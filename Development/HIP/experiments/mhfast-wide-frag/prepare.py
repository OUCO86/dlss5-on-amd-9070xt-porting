# Wide fragment weights for mh_ffn_fused_c256_frag_*: inside each 512-byte (16 rows x 32 k) tile the two K16 halves of
# a lane's fragment are placed adjacently, so one 16-byte load feeds two WMMAs (weight loads per wave halved). Same
# bytes, same accumulation order (k ascending). Host packs the wide layout under separate keys and, in pair mode, passes
# those buffers to the c256 launches; module set pair1 carries the matching kernel (pair2/3 = replications).
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-wide-frag'); out.mkdir(exist_ok=True)
# ---- kernel
s=(root/'hip/multihead_fast_padded.hip').read_text()
def rep(old,new):
    global s
    assert s.count(old)==1,(old[:80],s.count(old)); s=s.replace(old,new,1)
rep('DEV i2 frag_b(const unsigned char*base,uint row,uint K,uint k,uint group){',
    'using i4w=int __attribute__((ext_vector_type(4)));\nDEV i4w frag_b2(const unsigned char*base,uint row,uint K,uint k,uint group){i4w b;__builtin_memcpy(&b,base+((row/16)*(K/32)+k/32)*512+((group*16+row%16)*2)*8,16);return b;}\nDEV i2 frag_b(const unsigned char*base,uint row,uint K,uint k,uint group){')
W='__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12'
# expand loop
rep(''' for(uint k=0;k<C;k+=16){i2 a{};
#if HIP_FFN_COOP_INPUT
  if constexpr(ByteIn)a=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+group*8,width,height,workw,sx,sy);else __builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);
#else
  for(uint e=0;e<8;e++)pack(a,e,load_in(first+rc,k+group*8+e));
#endif
  for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc,offset=(row*C+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w),row,C,k,group);''',
''' if constexpr(Frag){
  for(uint k=0;k<C;k+=32){i2 a0{},a1{};
#if HIP_FFN_COOP_INPUT
   if constexpr(ByteIn){a0=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+group*8,width,height,workw,sx,sy);a1=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+16+group*8,width,height,workw,sx,sy);}else{__builtin_memcpy(&a0,hidden+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,hidden+rc*(C+4)+k+16+group*8,8);}
#else
   for(uint e=0;e<8;e++){pack(a0,e,load_in(first+rc,k+group*8+e));pack(a1,e,load_in(first+rc,k+16+group*8+e));}
#endif
   for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc;i4w b2=frag_b2(reinterpret_cast<const unsigned char*>(w),row,C,k,group);i2 b0={b2[0],b2[1]},b1={b2[2],b2[3]};expand[tile]='''+W+'''(a0,b0,expand[tile]);expand[tile]='''+W+'''(a1,b1,expand[tile]);}
  }
 }else
 for(uint k=0;k<C;k+=16){i2 a{};
#if HIP_FFN_COOP_INPUT
  if constexpr(ByteIn)a=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+group*8,width,height,workw,sx,sy);else __builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);
#else
  for(uint e=0;e<8;e++)pack(a,e,load_in(first+rc,k+group*8+e));
#endif
  for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc,offset=(row*C+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w),row,C,k,group);''')
# contract loop
rep(''' for(uint k=first_k;k<last_k;k+=16){i2 a;__builtin_memcpy(&a,hidden+rc*(4*C+4)+k+group*8,8);uint offset=4*C*C+((wave*16+rc)*(4*C)+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+4*C*C),wave*16+rc,4*C,k,group);''',
''' if constexpr(Frag){for(uint k=first_k;k<last_k;k+=32){i2 a0,a1;__builtin_memcpy(&a0,hidden+rc*(4*C+4)+k+group*8,8);__builtin_memcpy(&a1,hidden+rc*(4*C+4)+k+16+group*8,8);i4w b2=frag_b2(reinterpret_cast<const unsigned char*>(w+4*C*C),wave*16+rc,4*C,k,group);i2 b0={b2[0],b2[1]},b1={b2[2],b2[3]};accum='''+W+'''(a0,b0,accum);accum='''+W+'''(a1,b1,accum);}}
 else for(uint k=first_k;k<last_k;k+=16){i2 a;__builtin_memcpy(&a,hidden+rc*(4*C+4)+k+group*8,8);uint offset=4*C*C+((wave*16+rc)*(4*C)+k+group*8)/4;i2 b{};if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+4*C*C),wave*16+rc,4*C,k,group);''')
# projection loop
rep('''  for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C+((wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);''',
'''  if constexpr(Frag){for(uint k=0;k<C;k+=32){i2 a0,a1;__builtin_memcpy(&a0,hidden+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,hidden+rc*(C+4)+k+16+group*8,8);i4w b2=frag_b2(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);i2 b0={b2[0],b2[1]},b1={b2[2],b2[3]};result='''+W+'''(a0,b0,result);result='''+W+'''(a1,b1,result);}}
  else for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,hidden+rc*(C+4)+k+group*8,8);uint off=8*C*C+((wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(w+8*C*C),wave*16+rc,C,k,group);''')
# QKV loops (BatchNorm and plain)
rep('''   for(uint part=0;part<3;part++)for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);''',
'''   if constexpr(Frag){for(uint part=0;part<3;part++)for(uint k=0;k<C;k+=32){i2 a0,a1;__builtin_memcpy(&a0,qfeature+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,qfeature+rc*(C+4)+k+16+group*8,8);i4w b2=frag_b2(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);i2 b0={b2[0],b2[1]},b1={b2[2],b2[3]};q[part]='''+W+'''(a0,b0,q[part]);q[part]='''+W+'''(a1,b1,q[part]);}}
   else for(uint part=0;part<3;part++)for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);''')
rep('''   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);''',
'''   if constexpr(Frag){for(uint k=0;k<C;k+=32){i2 a0,a1;__builtin_memcpy(&a0,qfeature+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,qfeature+rc*(C+4)+k+16+group*8,8);i4w b2=frag_b2(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);i2 b0={b2[0],b2[1]},b1={b2[2],b2[3]};q='''+W+'''(a0,b0,q);q='''+W+'''(a1,b1,q);}}
   else for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((part*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),part*C+wave*16+rc,C,k,group);''')
(out/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'); print('kernel ok')
# ---- host: fence-scope-all host + wide packers + weight substitution in pair mode
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'): shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/packed_weights.h'; h=p.read_text()
old='inline void TilePackedMatrix(std::vector<float>&v,size_t start,size_t rows,size_t columns){'
assert h.count(old)==1
h=h.replace(old,'''// Wide fragment tiles: same 512-byte tiles, bytes ordered [lane half gr][row%16][k/16 within tile][8 k] so one 16-byte load
// per lane covers both K16 steps of a 32-k tile. Pure permutation of the same bytes.
inline void FragmentPackedMatrixWide(std::vector<float>&v,size_t start,size_t rows,size_t columns){
 if(rows%16||columns%32||start>v.size()||rows*columns>(v.size()-start)*4)throw std::runtime_error("packed fragment shape");
 auto*dst=reinterpret_cast<uint8_t*>(v.data()+start);std::vector<uint8_t>src(dst,dst+rows*columns);
 for(size_t n=0;n<rows;n++)for(size_t k=0;k<columns;k++)dst[((n/16)*(columns/32)+k/32)*512+((((k%16)/8)*16+n%16)*2+(k%32)/16)*8+k%8]=src[n*columns+k];
}
'''+old,1); p.write_text(h)
p=out/'Development/HIP/hip_reference_network.h'; n=p.read_text()
n=n.replace('class Network {','class Network {\n unsigned pair_mode=0,pair_calls=0;\n static bool PairModule(const std::string&m){return m=="c32_fused_ffn"||m=="mh_fused"||m=="deep_fast"||m=="mh_fast";}\n std::string Route(const std::string&m){if(pair_mode&&PairModule(m)){++pair_calls;return m+"_pair"+std::to_string(pair_mode);}return m;}\n',1)
old='api.hipModuleLaunchKernel(Fn(module,kernel),'; assert n.count(old)==1; n=n.replace(old,'api.hipModuleLaunchKernel(Fn(Route(module),kernel),',1)
anchor='modules["mh_fast"]=m;}'; assert n.count(anchor)==1
n=n.replace(anchor,anchor+'''
for(unsigned pm=1;pm<=3;pm++){const char*pf[][2]={{"c32_fused_ffn","c32_fused_ffn_attention-packed.hsaco"},{"mh_fused","multihead_fused_attention.hsaco"},{"deep_fast","deep_fast-packed.hsaco"},{"mh_fast","multihead-fast-padded-wave-packed.hsaco"}};for(auto&v:pf){Handle m{};api.Check(api.LoadModule(&m,(opt.modules+"/pair"+std::to_string(pm)+"/"+v[1]).c_str()),v[1]);modules[std::string(v[0])+"_pair"+std::to_string(pm)]=m;}}''',1)
n=n.replace(' Handle Stream()const{return stream;}',' void SetPairMode(unsigned m){pair_mode=m;pair_calls=0;} unsigned PairCalls()const{return pair_calls;}\n Handle Stream()const{return stream;}',1)
# wide packers (copies of the frag packers with the wide permutation and new keys)
i=n.index(' void* PackedFusedMhWeightFrag('); j=n.index('\n',i)
ffn=n[i:j].replace('PackedFusedMhWeightFrag(','PackedFusedMhWeightFragWide(').replace('@ffn-frag','@ffn-frag-wide').replace('FragmentPackedMatrix(','FragmentPackedMatrixWide(')
i2=n.index(' void* PackedMhWeightQkvFragOnly('); j2=n.index('\n',i2)
qkv=n[i2:j2].replace('PackedMhWeightQkvFragOnly(','PackedMhWeightQkvFragOnlyWide(').replace('@qkv-frag-only','@qkv-frag-only-wide').replace('FragmentPackedMatrix(','FragmentPackedMatrixWide(')
assert ffn.count('Wide(')>=2 and qkv.count('Wide(')>=2
n=n[:j2+1]+ffn+'\n'+qkv+'\n'+n[j2+1:]
old='auto fw=ffn_frag?PackedFusedMhWeightFrag(Block(block,"ffn"),c):'; assert n.count(old)==1
n=n.replace(old,'auto fw=ffn_frag?(pair_mode?PackedFusedMhWeightFragWide(Block(block,"ffn"),c):PackedFusedMhWeightFrag(Block(block,"ffn"),c)):',1)
old='ffn_frag?PackedMhWeightQkvFragOnly(Block(block,"attention"),c):'; assert n.count(old)==1
n=n.replace(old,'ffn_frag?(pair_mode?PackedMhWeightQkvFragOnlyWide(Block(block,"attention"),c):PackedMhWeightQkvFragOnly(Block(block,"attention"),c)):',1)
p.write_text(n)
x=(root/'src/native_hip_network.h').read_text();a=x.index('hip_reference::Options o;');b=x.index('  const wchar_t*modules=',a)
opts=x[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=W;o.height=H;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
r=(root/'Development/HIP/experiments/vit-schedule-cause/runner.cpp.in').read_text()
a=r.index(' for(unsigned frame=0;');b=r.index('api.hipFree(x);',a)
r=r[:a]+(here/'timing.inc').read_text()+r[b:]
(out/'network.cpp').write_text(r.replace('/* OPTIONS */',opts).replace('PASS ViT schedule controls','PASS wide frag'))
print('host ok')
