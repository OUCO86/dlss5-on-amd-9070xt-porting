 struct ProbeRecord{Handle begin{},end{};std::string module,kernel,stage,args;unsigned groups{},threads{},count{},frame{};};
 struct ProbeFrame{Handle begin{},end{};size_t first{},last{};};
 std::vector<ProbeRecord>probe_records;std::vector<ProbeFrame>probe_frames;
 bool probe_active=false;size_t probe_cursor=0,probe_mark=0;unsigned probe_frame=0;
