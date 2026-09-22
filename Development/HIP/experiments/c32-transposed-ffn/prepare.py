# C32 FFN expand->contract without the LDS round trip.
# WMMA A and B operand registers share one layout (lane%16 = M or N index, lane/16 selects the k half),
# so swapping the two operands of the expand product yields D^T: each lane then holds one row of the
# hidden block with 8 consecutive hidden columns = exactly the A fragment the contract step wants.
# The activated hidden values are packed to FP8 bytes in registers; scratch.hidden is never written.
# Round 1 (hfrag[8] array, expand fully unrolled by the compiler): bit-exact but +0.05..0.2ms, code +780 instructions.
# Round 2:
#   _pair1: transposed FFN with the contract interleaved into the rolled expand loop (one live fragment, no array)
#   _pair2: control: original LDS path, expand loop forced fully unrolled (code-size effect alone)
#   _pair3: pair1 with the sync after expand removed (hidden never touches LDS)
from pathlib import Path
import shutil, re
here = Path(__file__).resolve().parent; root = here.parents[3]; out = Path('/tmp/c32-transposed-ffn'); out.mkdir(exist_ok=True)
s = (root/'hip/c32_fused_ffn_attention.hip').read_text()
a = s.index('template<bool HalfOutput,bool Mapped=false'); b = s.index('\nKERNEL ', a); body = s[a:b]
expand_old = ''' C32_LOOP for(uint col=0;col<128;col+=16){f8 sum{};
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=matrix8(fw+512,(col+rc())*32+k);sum=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,sum);}
  for(uint e=0;e<8;e++){float v=sum[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;scratch.hidden[(first+gr()*8+e)*132+col+rc()]=static_cast<unsigned char>(fp8(v*p));}
 }
'''
expand_new = ''' C32_LOOP for(uint t=0;t<8;t++){f8 sum{};uint col=t*16;
  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=kt*16+gr()*8;a=load8(packed+(first+rc())*36+k);b=matrix8(fw+512,(col+rc())*32+k);sum=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(b,a,sum);}
  i2 h{};for(uint e=0;e<8;e++){float v=sum[e],g=clampf(v,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,p=g*q+.89453125f;put_bits(h,e,fp8(v*p));}
  {uint k=col+gr()*8;for(uint ci=0;ci<2;ci++){i2 b=matrix8(fw+4608,(ci*16+rc())*128+k);acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(h,b,acc[ci]);}}
 }
'''
expand_unrolled = expand_old.replace(' C32_LOOP for(uint col=0;col<128;col+=16)', ' _Pragma("unroll") for(uint col=0;col<128;col+=16)')
contract_old = '''  for(uint kt=0;kt<2;kt++){i2 a{},b{};uint k=chunk*32+kt*16+gr()*8;a=load8(scratch.hidden+(first+rc())*132+k);b=matrix8(fw+4608,(ci*16+rc())*128+k);acc[ci]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a,b,acc[ci]);}'''
contract_loop = ''' C32_LOOP for(uint chunk=0;chunk<4;chunk++)for(uint ci=0;ci<2;ci++){
''' + contract_old + '''
 }
'''
acc_decl = ' f8 acc[2];acc[0]=f8{};acc[1]=f8{};\n'
sync_block = '''#if HIP_C32_LOCAL_FFN_SYNC
 sync_owned_rows();
#else
 sync_window();
#endif
'''
assert body.count(expand_old) == 1 and body.count(contract_old) == 1
pre_i = body.index(sync_block); post_i = body.index(sync_block, body.index(expand_old))
assert body.count(sync_block) == 2 and pre_i < body.index(expand_old) < post_i
assert body.count(contract_loop) == 1 and body.count(acc_decl) == 1
def variant(mode):
    if mode == 2:
        return body.replace(expand_old, expand_unrolled, 1).replace('c32_fused_body(', 'c32_tffn2_body(', 1)
    # residual initialisation of acc (assignment or diagonal WMMAs) must precede the folded contract, as in the original order
    residual_seg = body[body.index(acc_decl):body.index(contract_loop)]
    v = body.replace(expand_old, residual_seg + expand_new, 1)
    v = v.replace(residual_seg + contract_loop, ' /* residual init moved before the expand loop; contract folded into it */\n', 1)
    assert v.count(residual_seg) == 1 and 'c32_tffn' not in v
    if mode == 3:
        i = v.index(sync_block, v.index(expand_new)); v = v[:i] + '/* hidden lives in registers: no sync needed */\n' + v[i+len(sync_block):]
    return v.replace('c32_fused_body(', f'c32_tffn{mode}_body(', 1)
code = '#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_C32_DIAG_WEIGHTS 1\n' + s
names = re.findall(r'^void (c32_\w+)\(', s[b:], re.M)
for mode in (1, 2, 3):
    code += '\n' + variant(mode) + '\n'
    for name in names:
        line = next(x for x in s[b:].splitlines() if x.startswith('void '+name+'('))
        code += 'KERNEL __attribute__((amdgpu_flat_work_group_size(128,128))) C32_OCC\n'
        code += line.replace('void '+name+'(', f'void {name}_pair{mode}(', 1).replace('c32_fused_body<', f'c32_tffn{mode}_body<') + '\n'
(out/'kernel.hip').write_text(code); print('kernels', len(names))
