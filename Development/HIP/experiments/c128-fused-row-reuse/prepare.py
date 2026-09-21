from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
out=Path('/tmp/c128-fused-row-reuse');out.mkdir(exist_ok=True)
shutil.copytree(root/'src',out/'src',dirs_exist_ok=True);(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
shutil.copyfile(root/'Development/HIP/benchmark_vit_reuse.cpp',out/'Development/HIP/benchmark.cpp')
s=(root/'hip/multihead_fast_padded.hip').read_text()
a=s.index('template<uint C,bool Tiled=false,bool Project=false,bool Mapped=false,bool Grouped=false,bool ByteIn=false,bool ByteFeature=false,bool BatchNorm=false,bool Frag=false>\nDEV void mh_ffn_qkv_body')
b=s.index('\nKERNEL ',a)
body=s[a:b]
# Separate specialization: row-major weights, sequential Q/K normalization only.
body=body.replace('mh_ffn_qkv_body','mh_ffn_qkv_m32_body',1)
body=body.replace(' uint first=__builtin_amdgcn_workgroup_id_x()*16;', ' const uint rowbase=(wave/8)*16, localtid=tid%256;\n uint first=__builtin_amdgcn_workgroup_id_x()*32;')
body=body.replace('static_assert(Project&&Grouped,','static_assert(C==128&&!Tiled&&!Frag&&!BatchNorm&&Project&&Grouped,')
body=body.replace('bytes[16*','bytes[32*').replace('raw[(BatchNorm?2:1)*16*','raw[(BatchNorm?2:1)*32*')
body=body.replace('__attribute__((shared)) unsigned char qfeature[16*(C+4)];','__attribute__((shared)) unsigned char qbuf[32*(C+4)];\n unsigned char*qfeature=qbuf+rowbase*(C+4);')
body=body.replace('__attribute__((shared)) float inverse[(BatchNorm?2:1)*16*(C/32)];','__attribute__((shared)) float ibuf[32*(C/32)];\n float*inverse=ibuf+rowbase*(C/32);float*raw=storage.raw+rowbase*(C/32)*33;')
body=body.replace('i<16*','i<32*').replace('i+=2*C','i+=4*C')
x=body.index(' f8 expand[4]{};');y=body.index('\n#if HIP_FFN_COOP_INPUT\n // ByteIn',x)
body=body[:x]+''' f8 expand[4]{};
 for(uint k=0;k<C;k+=16){i2 a[2]{};
  for(uint r=0;r<2;r++){
#if HIP_FFN_COOP_INPUT
   if constexpr(ByteIn)a[r]=ffn_input8_fragment<C,Mapped>(in8,first+r*16+rc,k+group*8,width,height,workw,sx,sy);
   else __builtin_memcpy(&a[r],hidden+(r*16+rc)*(C+4)+k+group*8,8);
#else
   for(uint e=0;e<8;e++)pack(a[r],e,load_in(first+r*16+rc,k+group*8+e));
#endif
  }
  for(uint t=0;t<2;t++){uint offset=((wave*32+t*16+rc)*C+k+group*8)/4;i2 b{int(pw[offset]),int(pw[offset+1])};
   for(uint r=0;r<2;r++)expand[r*2+t]=__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12(a[r],b,expand[r*2+t]);
  }
 }
'''+body[y:]
# Activation: four fragments now indexed by row tile, column tile.
x=body.index('#if HIP_FFN_ABLATE_ACT');y=body.index('\n f8 accum{};',x)
body=body[:x]+''' for(uint tile=0;tile<4;tile++)for(uint e=0;e<8;e++){float a=expand[tile][e],g=clampf(a,-4.f,4.f),q=absf(g)*(-.055908203125f)+.447265625f,poly=g*q+.89453125f;hidden[((tile/2)*16+group*8+e)*(4*C+4)+wave*32+(tile%2)*16+rc]=static_cast<unsigned char>(q8_fused_round(a*poly));}
 __builtin_amdgcn_s_barrier();
 // The remaining phases use 8 column waves per 16-row tile.
 wave%=8;
 first+=rowbase;
'''+body[y:]
x=body.index(' f8 accum{};');tail=body[x:]
tail=tail.replace('hidden+rc*','hidden+(rowbase+rc)*').replace('hidden[(group*8+e)*','hidden[(rowbase+group*8+e)*')
tail=tail.replace('storage.raw[','raw[').replace('if(tid<','if(localtid<').replace('head=tid/16,row=tid%16','head=localtid/16,row=localtid%16').replace('inverse[tid]','inverse[localtid]')
body=body[:x]+tail
exports=[];names=[]
for mapped in (False,True):
 for bytein,fb in ((False,False),(False,True),(True,True)):
  name='mh_ffn_fused_c128_project_'+('mapped_' if mapped else '')+'g128_qkv'+('_bytein_fb' if bytein else '_fb' if fb else '')
  names.append(name)
  exports.append(f'KERNEL __attribute__((amdgpu_flat_work_group_size(512,512))) void {name}_m32(const float*in,const float*w,const float*aw,unsigned char*out,unsigned char*norm,uint tokens,uint width,uint height,uint workw,uint sx,uint sy){{mh_ffn_qkv_m32_body<128,false,true,{str(mapped).lower()},true,{str(bytein).lower()},{str(fb).lower()}>(in,w,out,tokens,width,height,workw,sx,sy,aw,norm);}}')
(out/'multihead_fast_padded.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_PREPACKED_WEIGHTS 1\n#define HIP_FFN_HOIST_RES 2\n'+s+'\n'+body+'\n'+'\n'.join(exports)+'\n')
(here/'kernel.inc').write_text(body+'\n'+'\n'.join(exports)+'\n')
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text();needle='  if(module=="mh_fast"){';assert s.count(needle)==1
# Route only known compatible entries, preserve all alternative modes.
s=s.replace(needle,needle+'\n   static const std::set<std::string> m32={'+','.join('"'+n+'"' for n in names)+'};\n   if(m32.count(kernel)&&!std::getenv("DLSS5_C128_M32_DISABLE")){if(count%(128*32))throw std::runtime_error("C128 M32 shape");kernel+="_m32";}')
needle='threads=c*2;groups=count/(c*16);';assert s.count(needle)==1
s=s.replace(needle,needle+'if(kernel.size()>4&&kernel.compare(kernel.size()-4,4,"_m32")==0){threads=512;groups=count/(c*32);}')
p.write_text(s)
print(out)
