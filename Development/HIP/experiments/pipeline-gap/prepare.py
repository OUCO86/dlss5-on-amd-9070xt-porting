from pathlib import Path
root=Path(__file__).resolve().parents[4];s=(root/'Development/HIP/benchmark_live_capture.cpp').read_text()
s=s.replace('auto run=[&]{network.Enqueue(local_in,nullptr,local_out,0);api.Check(api.hipStreamSynchronize(network.Stream()),"local completion");};', '''double enqueue_ms=0,wait_ms=0;
 auto run=[&]{auto a=std::chrono::steady_clock::now();network.Enqueue(local_in,nullptr,local_out,0);auto b=std::chrono::steady_clock::now();api.Check(api.hipStreamSynchronize(network.Stream()),"local completion");auto c=std::chrono::steady_clock::now();enqueue_ms=std::chrono::duration<double,std::milli>(b-a).count();wait_ms=std::chrono::duration<double,std::milli>(c-b).count();};''')
s=s.replace('std::vector<double>times;','std::vector<double>times;FILE*detail=_wfopen((prefix+L"-hip.csv").c_str(),L"wb");fprintf(detail,"frame,enqueue_ms,wait_ms,total_ms\\n");',1)
needle='times.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());'
assert s.count(needle)==1;s=s.replace(needle,needle+'fprintf(detail,"%u,%.9f,%.9f,%.9f\\n",i,enqueue_ms,wait_ms,times.back());')
s=s.replace(' std::vector<float>actual(expected.size());',' fclose(detail);\n std::vector<float>actual(expected.size());',1)
# Burst submission retains same stream order/input; intermediate results intentionally overwritten.
needle='api.hipFree(local_in);api.hipFree(local_out);if(diff||invalid)throw'
s=s.replace(needle,'''if(diff||invalid)throw std::runtime_error("before burst mismatch");
 for(unsigned depth:{4u,16u}){auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<N;i++){for(unsigned j=0;j<depth;j++)network.Enqueue(local_in,nullptr,local_out,0);api.Check(api.hipStreamSynchronize(network.Stream()),"burst completion");}double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/double(N*depth);api.Check(api.hipMemcpy(actual.data(),local_out,actual.size()*4,2),"burst read");if(memcmp(actual.data(),expected.data(),actual.size()*4))throw std::runtime_error("burst mismatch");printf("BURST depth=%u mean_per_frame_ms=%.9f output_exact=1\\n",depth,ms);}
 api.hipFree(local_in);api.hipFree(local_out);if(diff||invalid)throw''')
out=Path('/tmp/pipeline-gap');out.mkdir(exist_ok=True);(out/'benchmark.cpp').write_text(s.replace('#include "../../src/','#include "'+str(root/'src')+'/'))
