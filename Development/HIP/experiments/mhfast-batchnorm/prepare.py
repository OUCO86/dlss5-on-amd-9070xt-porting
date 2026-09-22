# mh_ffn_fused_c256_frag_project_mapped_g128_qkv_bytein_fb with BatchNorm=true: parts 0 and 1 of the QKV normalisation
# share one barrier pair instead of one pair each (8 -> 6 barriers per wave). Same values, same summation order.
# Costs LDS (storage.raw holds two parts). pair1 only; pair2/3 replications. Base = prod5.
from pathlib import Path
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mhfast-batchnorm'); out.mkdir(exist_ok=True)
s=(root/'hip/multihead_fast_padded.hip').read_text()
old='mh_ffn_qkv_body<256,false,true,true,true,true,true,false,true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);}'
assert s.count(old)==1
s=s.replace(old,'mh_ffn_qkv_body<256,false,true,true,true,true,true,true,true>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);}',1)
text='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'
(out/'multihead-fast-padded-wave-packed.generated.hip').write_text(text); print('ok')
