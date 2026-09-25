 /* family-ledger (2026-09-26): sparse prefix markers with a dynamic dispatch total + Stage topology capture. */
 bool prefix_active=false,topo_active=false;unsigned prefix_cut=0,prefix_cursor=0,prefix_total=0;Handle prefix_begin{},prefix_mid{},prefix_end{};
 struct PrefixEvents{Handle begin{},mid{},end{};};std::vector<PrefixEvents>prefix_events;size_t prefix_event_index=0;
 std::vector<std::pair<std::string,unsigned>>topo_stages;std::vector<std::string>topo_kernels;
