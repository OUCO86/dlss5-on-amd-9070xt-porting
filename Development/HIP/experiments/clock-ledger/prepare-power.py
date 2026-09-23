# Power ablations of the production (prod6, transposed tail) FFN+QKV kernel: timing/clock only, NOT bit-exact.
#   pair4: the 3 x 8-byte norm stores never execute (impossible data-dependent branch keeps the QKV WMMAs and the inverse)
#   pair5: the FFN 'out' global stores never execute (qfeature LDS copy kept, so the QKV part is unchanged)
#   pair6: both
from pathlib import Path
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/clock-ledger/power'); out.mkdir(parents=True,exist_ok=True)
s0=(root/'hip/multihead_fast_padded.hip').read_text()
norm='   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;for(uint e=0;e<8;e++)norm[((first+rc)*3+part)*C+wave*16+group*8+e]=static_cast<unsigned char>(q8_fused_round(q[e]*inv));}\n'
norm_ab='   {float inv=part<2?inverse[(wave/2)*16+rc]:1.f;for(uint e=0;e<8;e++)if(q[e]*inv==12345.f)norm[((first+rc)*3+part)*C+wave*16+group*8+e]=1;}\n'
outs='if constexpr(ByteFeature)out[(first+rc)*C+c]=static_cast<unsigned char>(byte);else reinterpret_cast<float*>(out)[(first+rc)*C+c]=v;'
outs_ab='if(v==12345.f){if constexpr(ByteFeature)out[(first+rc)*C+c]=1;else reinterpret_cast<float*>(out)[(first+rc)*C+c]=v;}'
for o in (norm,outs): assert s0.count(o)==1,(o[:40],s0.count(o))
V={'p6':s0,'pair4':s0.replace(norm,norm_ab),'pair5':s0.replace(outs,outs_ab),'pair6':s0.replace(norm,norm_ab).replace(outs,outs_ab)}
for n,s in V.items(): (out/f'{n}.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n')
print('written',list(V))
