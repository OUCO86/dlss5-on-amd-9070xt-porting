from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-balanced-layout');out.mkdir(exist_ok=True)
s=Path('/tmp/vit-balanced-tile/kernel.hip').read_text()
a=s.index('template<uint BM>\nDEV void balanced_m32n32_u4');b=s.index('template<uint BM>\nDEV void balanced_m32n32_u1',a);part=s[a:b]
part=part.replace('balanced_m32n32_u4','balanced_tiled').replace('probe_m32n32_u4','probe_tiled_balanced')
part=part.replace('const uint*p=reinterpret_cast<const uint*>(in);uint off=((first+m*16+rc())*1024+k+gr()*8)/4;\n   a[m]={int(p[off]),int(p[off+1])};','__builtin_memcpy(&a[m],reinterpret_cast<const unsigned char*>(in)+vit_tile_offset(first+m*16+rc(),k+gr()*8,1024),8);')
s+=part+'\nWAVE void probe_tiled_m16(const float*in,const float*w,float*out,uint tokens,uint inputs,uint outputs,const uint*gate){if(gate&&gate[0])return;vit_expand_blocked_body<true,true,true,true>(in,w,out,tokens,1024,4096);}\n'
(out/'kernel.hip').write_text(s)
(out/'Development/HIP').mkdir(parents=True,exist_ok=True)
for p in (root/'Development/HIP').glob('*.h'):shutil.copyfile(p,out/'Development/HIP'/p.name)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text().replace('class Network {','class Network {\n bool c32_probe_done=false;void*layout_float_input=nullptr;U layout_count=0;',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check(';assert s.count(needle)==1
s=s.replace(needle,(here/'layout-timing.inc').read_text()+needle,1).replace(' Handle Stream()const{return stream;}',' bool C32ProbeDone()const{return c32_probe_done;}\n Handle Stream()const{return stream;}',1);p.write_text(s)
s=Path('/tmp/vit-balanced-tile/pure.cpp').read_text().replace('PASS ViT balanced tile','PASS ViT balanced layout');(out/'pure.cpp').write_text(s)
