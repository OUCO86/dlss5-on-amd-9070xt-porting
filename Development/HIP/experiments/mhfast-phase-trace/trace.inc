 // 30 untraced warm-up frames, then TRACE_FRAMES traced frames; every C32 launch writes per-wave SHADER_CYCLES stamps.
 for(unsigned i=0;i<30;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();}
 net.SetPairMode(1);net.BeginTrace();
 const unsigned frames=8;
 for(unsigned i=0;i<frames;i++){net.Enqueue(x,nullptr,y,0);net.Synchronize();net.EndFrame();}
 std::vector<float>actual(expected.size());api.Check(api.hipMemcpy(actual.data(),y,actual.size()*4,2),"raw check");size_t diff=0;for(size_t i=0;i<actual.size();i++)diff+=memcmp(&actual[i],&expected[i],4)!=0;
 if(diff)throw std::runtime_error("traced output differs");
 net.DumpTrace("trace");
 printf("TRACE frames=%u bitdiff=%llu launches_per_frame=%u\n",frames,(unsigned long long)diff,net.LaunchesPerFrame());fflush(stdout);
