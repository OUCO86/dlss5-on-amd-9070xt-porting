# Byte chain for the C32 raw chain: mapped/chain producers (HalfOutput, raw_output=1) write the FP8 byte the consumer
# would have produced -- fp8(F(float((_Float16)v))) -- instead of the f16 value; RawMapped consumers (chain, chain_finish)
# load one byte per element and skip F(). Bit-identical by construction: the producer evaluates exactly the consumer's
# expression. Same buffer (bytes occupy the first half of the f16 allocation). Three identical _pairN sets = 3 replications.
from pathlib import Path
import re
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/c32-byte-chain'); out.mkdir(exist_ok=True)
s=(root/'hip/c32_fused_ffn_attention.hip').read_text()
a=s.index('template<bool HalfOutput,bool Mapped=false'); b=s.index('\nKERNEL ',a); body=s[a:b]
prod_old='   else if constexpr(HalfOutput)reinterpret_cast<_Float16*>(out)[i]=(_Float16)(raw_output?v:F(v));else out[i]=raw_output?v:F(v);}\n'
prod_new='   else if constexpr(HalfOutput){if(raw_output)reinterpret_cast<unsigned char*>(out)[i]=static_cast<unsigned char>(fp8(F(float((_Float16)v))));else reinterpret_cast<_Float16*>(out)[i]=(_Float16)F(v);}else out[i]=raw_output?v:F(v);}\n'
cons_old='    else if constexpr(RawMapped)lv[j]=float(reinterpret_cast<const _Float16*>(raw_input)[idx+l]);\n'
cons_new='    else if constexpr(RawMapped){hb[j]=reinterpret_cast<const unsigned char*>(raw_input)[idx+l];lv[j]=0.f;}\n'
pack_old='   else{float c;if constexpr(Merge){float high=__builtin_amdgcn_cvt_f32_fp8(int(hb[j]),0);c=Hrtz(Hrtz(lv[j]*scales[l])+high*scales[32+l]);}else if constexpr(RawMapped)c=F(lv[j]);else c=lv[j];v=srcs[j]>=0?c:0.f;}\n   packed[row*36+l]=static_cast<unsigned char>(fp8(v));\n'
pack_new='   else{float c;if constexpr(Merge){float high=__builtin_amdgcn_cvt_f32_fp8(int(hb[j]),0);c=Hrtz(Hrtz(lv[j]*scales[l])+high*scales[32+l]);}else if constexpr(RawMapped)c=0.f;else c=lv[j];v=srcs[j]>=0?c:0.f;}\n   if constexpr(RawMapped)packed[row*36+l]=srcs[j]>=0?static_cast<unsigned char>(hb[j]):static_cast<unsigned char>(0);else packed[row*36+l]=static_cast<unsigned char>(fp8(v));\n'
for o in (prod_old,cons_old,pack_old): assert body.count(o)==1,o[:60]
v1=body.replace(prod_old,prod_new,1).replace(cons_old,cons_new,1).replace(pack_old,pack_new,1)
# vectorised staging: wrap the prefetch passes in `if constexpr(RawMapped){...}else{...}`
pf_start='#if HIP_C32_STAGE_PREFETCH\n  // Pass 1:'
pf_end_marker='   if constexpr(NeedIn16)in16[row*34+l]=(_Float16)v;\n  }}\n#else\n'
assert v1.count(pf_start)==1 and v1.count(pf_end_marker)==1
i0=v1.index(pf_start)+len('#if HIP_C32_STAGE_PREFETCH\n'); i1=v1.index(pf_end_marker)+len('   if constexpr(NeedIn16)in16[row*34+l]=(_Float16)v;\n  }')
vec='''  if constexpr(RawMapped){
   // Byte rows: lane l stages half of token l>>1 (16 bytes) with one 128-bit load; source row broadcast via ds_bpermute.
   int src=__builtin_amdgcn_ds_bpermute(int((l>>1)*4),mine);uint idx=src>=0?uint(src)+(l&1)*16:0u;
   i4 q;__builtin_memcpy(&q,reinterpret_cast<const unsigned char*>(raw_input)+idx,16);
   if(src<0)q=i4{0,0,0,0};
   __builtin_memcpy(packed+(first+(l>>1))*36+(l&1)*16,&q,16);
  }else{
'''
v2=v1[:i0]+vec+v1[i0:i1]+'  }'+v1[i1:]
assert 'using i4=' in s or True
variants={1:v1.replace('c32_fused_body(','c32_bc1_body(',1),2:v2.replace('c32_fused_body(','c32_bc2_body(',1),3:v2.replace('c32_fused_body(','c32_bc3_body(',1)}
code='#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n'+s+'\nusing i4=int __attribute__((ext_vector_type(4)));\n'+'\n'.join(variants[m] for m in (1,2,3))+'\n'
names=re.findall(r'^void (c32_\w+)\(',s[b:],re.M)
for mode in (1,2,3):
    for name in names:
        line=next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code+='KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'+line.replace('void '+name+'(',f'void {name}_pair{mode}(',1).replace('c32_fused_body<',f'c32_bc{mode}_body<')+'\n'
(out/'kernel.hip').write_text(code); print('kernels',len(names))
