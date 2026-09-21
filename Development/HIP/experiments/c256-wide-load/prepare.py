from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/c256-wide-load');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
shutil.copyfile(root/'Development/HIP/benchmark_vit_reuse.cpp',out/'Development/HIP/benchmark.cpp')
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text();needle='FragmentPackedMatrix(v,0,4*c,c);';assert s.count(needle)==1
s=s.replace(needle,needle+'''if(c==256){auto*bytes=reinterpret_cast<unsigned char*>(v.data());for(size_t block=0;block<4*cc/512;block++){unsigned char old[512];memcpy(old,bytes+block*512,512);for(unsigned lane=0;lane<32;lane++)for(unsigned half=0;half<2;half++)memcpy(bytes+block*512+lane*16+half*8,old+half*256+lane*8,8);}}''');p.write_text(s)
old=(root/'hip/multihead_fast_padded.hip').read_text();a=old.index(' for(uint k=0;k<C;k+=16){i2 a{};',old.index('DEV void mh_ffn_qkv_body'));b=old.index('\n#if HIP_FFN_COOP_INPUT\n // ByteIn',a)
wide=''' if constexpr(C==256&&Frag){
  typedef int i4 __attribute__((ext_vector_type(4)));
  for(uint k=0;k<C;k+=32){i2 a0{},a1{};
#if HIP_FFN_COOP_INPUT
   if constexpr(ByteIn){a0=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+group*8,width,height,workw,sx,sy);a1=ffn_input8_fragment<C,Mapped>(in8,first+rc,k+16+group*8,width,height,workw,sx,sy);}
   else{__builtin_memcpy(&a0,hidden+rc*(C+4)+k+group*8,8);__builtin_memcpy(&a1,hidden+rc*(C+4)+k+16+group*8,8);}
#else
   for(uint e=0;e<8;e++){pack(a0,e,load_in(first+rc,k+group*8+e));pack(a1,e,load_in(first+rc,k+16+group*8+e));}
#endif
   for(uint tile=0;tile<4;tile++){uint row=wave*64+tile*16+rc;size_t offset=((row/16)*(C/32)+k/32)*512+l*16;i4 b;__builtin_memcpy(&b,reinterpret_cast<const unsigned char*>(w)+offset,16);
    expand[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a0,i2{b[0],b[1]},expand[tile]);
    expand[tile]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a1,i2{b[2],b[3]},expand[tile]);
   }
  }
 }else{
'''
s=old[:a]+wide+old[a:b]+'\n }'+old[b:];(out/'multihead_fast_padded.hip').write_text(s)
(here/'candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/hip/multihead_fast_padded.hip',tofile='b/hip/multihead_fast_padded.hip')))
print(out)
