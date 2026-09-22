 void PrepareContext(unsigned frames){context_events.resize(frames);for(auto&e:context_events){api.Check(api.hipEventCreate(&e.begin),"context begin create");api.Check(api.hipEventCreate(&e.end),"context end create");}}
 void SetSchedule(unsigned mode){schedule_mode=mode;schedule_replaced=0;}
 unsigned ScheduleReplaced()const{return schedule_replaced;}
 void ContextFrame(int frame){context_frame=frame;context_pack=0;if(frame>=0){if(size_t(frame)>=context_events.size())throw std::runtime_error("context frame range");context_events[frame].began=context_events[frame].ended=false;}}
 std::vector<float> ReadContext(){Synchronize();std::vector<float>v;for(auto&e:context_events){if(!e.began||!e.ended)throw std::runtime_error("missing context event");api.Check(api.hipEventSynchronize(e.end),"context end completed");float ms=0;api.Check(api.hipEventElapsedTime(&ms,e.begin,e.end),"context elapsed");v.push_back(ms);}return v;}
 void ReleaseContext(){Synchronize();for(auto&e:context_events){api.hipEventDestroy(e.begin);api.hipEventDestroy(e.end);}context_events.clear();}

 float ReadContextFrame(unsigned frame){auto&e=context_events.at(frame);if(!e.began||!e.ended)throw std::runtime_error("missing immediate event");api.Check(api.hipEventSynchronize(e.begin),"begin completed");api.Check(api.hipEventSynchronize(e.end),"end completed");float ms=0;api.Check(api.hipEventElapsedTime(&ms,e.begin,e.end),"immediate elapsed");return ms;}
