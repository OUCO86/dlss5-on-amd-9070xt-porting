# 1b: wave-local QKV normalisation (NOT bit-exact: the 32-term sum of squares is re-associated). On top of the
# transposed tail. Parts 0/1: wave w owns head w%(C/32) of part w/(C/32) (two 16-column tiles x 16 k = 32 WMMAs);
# a token row's 32 columns then sit in two lanes (l, l^16) x two tiles: 16 in-lane squares + one ds_bpermute add,
# rsqrt and scale in registers, no LDS, no barriers. Part 2 keeps 16 columns per wave (16 WMMAs) -> 48 per wave as
# before. Tolerant module-set host records bitdiff. pair1 = pair2 = pair3 (three replications).
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-wave-norm')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
W='__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12'
start='  for(uint part=0;part<3;part++){f8 q{};\n'
assert s0.count(start)==1
i=s0.index(start)
# the loop ends at the line '  }\n' that precedes ' }else{\n' (non-Project branch)
j=s0.index('  }\n }else{\n',i)+len('  }\n')
old=s0[i:j]
assert old.count('__builtin_amdgcn_s_barrier();')==2 and old.count('#if HIP_FFN_TRANSPOSED_TAIL')==3
new='''#if HIP_FFN_WAVE_NORM
  {const uint heads=C/32;uint hp=wave/heads,head=wave%heads;f8 q[2]{};
   for(uint j=0;j<2;j++)for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint col=head*32+j*16+rc,off=((hp*C+col)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),hp*C+col,C,k,group);else b={int(aq[off]),int(aq[off+1])};q[j]='''+W+'''(b,a,q[j]);}
   float ss=0.f;for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)ss+=q[j][e]*q[j][e];
   ss+=__builtin_bit_cast(float,__builtin_amdgcn_ds_bpermute(int((l^16)*4),__builtin_bit_cast(int,ss)));
   float inv=__builtin_amdgcn_rsqf(maxf(ss,6.198883056640625e-5f))*(hp==0?aw[4*C*C+(C/32)*4096+head]:1.f);
   for(uint j=0;j<2;j++)for(uint e=0;e<8;e++)norm[((first+rc)*3+hp)*C+head*32+j*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[j][e]*inv));}
  {f8 q{};
   for(uint k=0;k<C;k+=16){i2 a,b;__builtin_memcpy(&a,qfeature+rc*(C+4)+k+group*8,8);uint off=((2*C+wave*16+rc)*C+k+group*8)/4;if constexpr(Frag)b=frag_b(reinterpret_cast<const unsigned char*>(aw),2*C+wave*16+rc,C,k,group);else b={int(aq[off]),int(aq[off+1])};q='''+W+'''(b,a,q);}
   for(uint e=0;e<8;e++)norm[((first+rc)*3+2)*C+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*1.f));}
#else
'''+old+'#endif\n'
s1=s0[:i]+new+s0[j:]
assert 'HIP_FFN_TRANSPOSED_TAIL 1' in s1
for m in (1,2,3):
    (out/f'pair{m}'/'multihead-fast-padded-wave-packed.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n#define HIP_FFN_WAVE_NORM 1\n'+s1+'\n')
print('written; removed loop lines',old.count('\n'))
