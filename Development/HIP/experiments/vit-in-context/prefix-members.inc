 unsigned schedule_mode=0,schedule_replaced=0,context_pack=0;
 struct ContextPrefix{Handle start{},mid{},end{};};std::vector<ContextPrefix> prefixes;size_t prefix_index=0;
 bool prefix_active=false,prefix_after=false,prefix_hit=false;ContextPrefix* current_prefix=nullptr;
