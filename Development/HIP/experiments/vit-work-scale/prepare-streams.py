from pathlib import Path
import shutil
here=Path(__file__).resolve().parent;out=Path('/tmp/vit-work-scale');s=(out/'kernel.hip').read_text()
for bm in (1,2):
 a=s.index(f'template<uint T,bool Interleave> DEV void scale_dispatch_m{bm}');b=s.index('\n',a);t=s[a:b]
 t=t.replace(f'scale_dispatch_m{bm}(',f'scale_streams_m{bm}(').replace('uint copies){','uint copies,uint input_stride){').replace('(in,w,dest,T,1024,4096,logical)','(reinterpret_cast<const float*>(reinterpret_cast<const unsigned char*>(in)+copy*input_stride),w,dest,T,1024,4096,logical)')
 s+='\n'+t+'\n'
 for order in ('major','interleave'):
  flag='true' if order=='interleave' else 'false'
  s+=f'WAVE void probe_m{bm}_{order}_streams(const float*in,const float*w,float*out,uint tokens,uint copies,uint stride,const uint*gate){{if(gate&&gate[0])return;if(tokens==400)scale_streams_m{bm}<400,{flag}>(in,w,out,copies,stride);else if(tokens==640)scale_streams_m{bm}<640,{flag}>(in,w,out,copies,stride);}}\n'
(out/'streams.hip').write_text(s)
host=out/'streams';shutil.copytree(out/'Development',host/'Development',dirs_exist_ok=True)
p=host/'Development/HIP/hip_reference_network.h';text=p.read_text();old=(here/'timing.inc').read_text();assert old in text
new=old.replace('  FILE*csv=', '''  size_t input_bytes=size_t(tokens)*1024;std::vector<unsigned char>input_copy(input_bytes*8);api.Check(api.hipMemcpy(input_copy.data(),parg(0),input_bytes,2),"capture input");for(unsigned c=1;c<8;c++)std::memcpy(input_copy.data()+c*input_bytes,input_copy.data(),input_bytes);void*multi_input{};api.Check(api.hipMalloc(&multi_input,input_bytes*8),"multi input");api.Check(api.hipMemcpy(multi_input,input_copy.data(),input_bytes*8,1),"copy inputs");
  FILE*csv=''').replace('fopen("scale.csv"','fopen("streams.csv"').replace('for(U copies:{1u,2u,4u,8u})','for(U copies:{8u})').replace('+"_"+order);','+"_"+order+"_streams");')
new=new.replace('U active_copies=base?1:copies;unsigned g=base?groups:((tokens+16*bm-1)/(16*bm))*64*copies;auto fn=base?original:probe;','U active_copies=copies,input_stride=base?0:U(input_bytes);unsigned g=((tokens+16*bm-1)/(16*bm))*64*copies;auto fn=probe;')
new=new.replace('args[2]=&scratch;if(!base)args[4]=&copies;','args[0]=&multi_input;args[2]=&scratch;args[4]=&copies;args[5]=&input_stride;')
new=new.replace('api.hipFree(scratch);launch(original,','api.hipFree(multi_input);api.hipFree(scratch);launch(original,')
new=new.replace('slot,original,tokens','slot,shared_input,tokens')
p.write_text(text.replace(old,new));shutil.copyfile(out/'pure.cpp',host/'streams.cpp')
