 struct PrefixEvents{Handle begin{},mid{},end{};};std::vector<PrefixEvents>prefix_events;size_t prefix_event_index=0;
 bool prefix_active=false;unsigned prefix_cut=0,prefix_cursor=0;Handle prefix_begin{},prefix_mid{},prefix_end{};
