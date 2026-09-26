 static constexpr unsigned PHASE_GROUPS=40000,PHASE_LAUNCHES=16,PHASE_FRAMES=8;
 static constexpr size_t PHASE_WORDS=((PHASE_GROUPS+31)/32)*4*4;
 unsigned phase_mode=0,phase_launch=0,phase_frame=0,phase_offset=0;
 unsigned*phase_buffer=nullptr;
 std::string phase_names[PHASE_LAUNCHES];unsigned phase_groups[PHASE_LAUNCHES]{};
public:
 void InitPhase(){if(phase_buffer)throw std::runtime_error("phase already initialized");api.Check(api.hipMalloc((void**)&phase_buffer,PHASE_WORDS*PHASE_LAUNCHES*PHASE_FRAMES*4),"phase allocation");}
 void PhaseMode(unsigned mode){if(mode>11||!phase_buffer)throw std::runtime_error("phase mode");Synchronize();phase_mode=mode;phase_frame=phase_offset=0;}
 void ClearPhase(){api.Check(api.hipMemsetAsync(phase_buffer,0,PHASE_WORDS*PHASE_LAUNCHES*PHASE_FRAMES*4,stream),"phase clear");}
 void PhaseFrame(unsigned frame){if(frame>=PHASE_FRAMES)throw std::runtime_error("phase frame");phase_frame=frame;phase_offset=(frame*5)&31u;}
 unsigned PhaseCalls()const{return phase_launch;}
 void DumpPhase(const std::string&prefix){
  Synchronize();std::ofstream meta(prefix+"-meta.csv");meta<<"launch,kernel,groups\n";
  for(unsigned i=0;i<phase_launch;i++){
   meta<<i<<","<<phase_names[i]<<","<<phase_groups[i]<<"\n";
   size_t words=((phase_groups[i]+31)/32)*4*4;std::vector<unsigned> data(words);
   for(unsigned frame=0;frame<PHASE_FRAMES;frame++){
    auto*ptr=phase_buffer+(size_t(frame)*PHASE_LAUNCHES+i)*PHASE_WORDS;
    api.Check(api.hipMemcpy(data.data(),ptr,words*4,2),"phase read");
    std::ofstream f(prefix+"-launch"+std::to_string(i)+"-frame"+std::to_string(frame)+".u32",std::ios::binary);
    f.write(reinterpret_cast<const char*>(data.data()),words*4);if(!f)throw std::runtime_error("trace write");
   }
  }
 }
 void ReleasePhase(){Synchronize();phase_mode=0;if(phase_buffer)api.Check(api.hipFree(phase_buffer),"phase free");phase_buffer=nullptr;}
