from pathlib import Path
root=Path(__file__).resolve().parents[4];out=Path('/tmp/kernel-bottleneck')
s=(root/'Development/HIP/benchmark_live_capture.cpp').read_text();needle=';void*local_in=nullptr,*local_out=nullptr;';assert needle in s
s=s.replace(needle,';std::ofstream("D:/DLSSNR-Lab/hip-backend/counter-input.f32",std::ios::binary).write(reinterpret_cast<char*>(encoded.data()),encoded.size()*4);std::ofstream("D:/DLSSNR-Lab/hip-backend/counter-expected.f32",std::ios::binary).write(reinterpret_cast<char*>(expected.data()),expected.size()*4);void*local_in=nullptr,*local_out=nullptr;',1)
(out/'dump.cpp').write_text(s.replace('#include "../../src/','#include "'+str(root/'src')+'/'))
s=(root/'src/native_hip_network.h').read_text();a=s.index('hip_reference::Options o;');b=s.index('  const wchar_t*modules=',a);opts=s[a:b].replace('o.width=g.processing_width;o.height=g.processing_height;o.post_shift=post_shift','o.width=1600;o.height=960;o.post_shift=3').replace('o.assets=Utf8(directory)','o.assets=argv[1]')
code='''#include <windows.h>
#include <fstream>
#include <vector>
#include <string>
#include "Development/HIP/hip_reference_network.h"
std::vector<float> read(const char*p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error(p);size_t bytes=size_t(f.tellg());if(bytes%4)throw std::runtime_error("unaligned file");std::vector<float>x(bytes/4);f.seekg(0);f.read(reinterpret_cast<char*>(x.data()),bytes);return x;}
int main(int argc,char**argv){try{if(argc!=7)throw std::runtime_error("assets modules flags input expected frames");std::ifstream ff(argv[3]);std::string line;while(std::getline(ff,line)){if(!line.empty()&&line.back()=='\\r')line.pop_back();auto p=line.find('=');if(line.rfind("DLSS5_",0)==0&&p!=std::string::npos)_putenv_s(line.substr(0,p).c_str(),line.substr(p+1).c_str());}
'''+opts+'''
o.modules=argv[2];hip_reference::Network net(o);auto&api=net.Runtime();auto in=read(argv[4]),expected=read(argv[5]);if(in.size()!=size_t(1600)*960*4||expected.size()!=size_t(1600)*960*3)throw std::runtime_error("shape");void*x{},*y{};api.Check(api.hipMalloc(&x,in.size()*4),"input");api.Check(api.hipMalloc(&y,expected.size()*4),"output");api.Check(api.hipMemcpy(x,in.data(),in.size()*4,1),"upload");std::vector<float>actual(expected.size());size_t errors=0;unsigned frames=unsigned(std::stoul(argv[6]));
for(unsigned i=0;i<frames;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();if(i==0||i+1==frames){api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"read");size_t diff=0;for(size_t j=0;j<actual.size();j++)diff+=memcmp(&actual[j],&expected[j],4)!=0;printf("PURE frame=%u bitdiff=%zu\\n",i,diff);fflush(stdout);errors+=diff;}}
api.hipFree(x);api.hipFree(y);return errors?1:0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\\n",e.what());return 1;}}
''';(out/'pure.cpp').write_text(code)
