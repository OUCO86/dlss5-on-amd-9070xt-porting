from pathlib import Path
here=Path(__file__).resolve().parent
s=(here/'prepare.py').read_text().replace("Path('/tmp/vit-repeat-context')","Path('/tmp/vit-clone-context')")
s=s.replace("(here/'members.inc').read_text()", "(here/'members.inc').read_text()+'\\n bool amp_distinct=false;std::map<void*,std::vector<void*>> amp_weight_clones;' ")
s=s.replace("(here/'public.inc').read_text()", "(here/'public.inc').read_text().replace('unsigned repeats){','unsigned repeats,bool distinct=false){amp_distinct=distinct;')+'\\n void ReleaseClones(){Synchronize();for(auto&kv:amp_weight_clones)for(void*p:kv.second)api.Check(api.hipFree(p),\"clone free\");amp_weight_clones.clear();}\\n'")
s=s.replace("(here/'dispatch.inc').read_text()", "(here/'clone-dispatch.inc').read_text()")
s=s.replace("(here/'timing.inc').read_text()", "(here/'clone-timing.inc').read_text()")
# Execute the same common generator with this file's scope/path.
exec(compile(s,str(here/'prepare.py'),'exec'))
