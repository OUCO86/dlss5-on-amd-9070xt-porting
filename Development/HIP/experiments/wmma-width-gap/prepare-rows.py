from pathlib import Path
import runpy
h=Path(__file__).resolve().parent;out=Path('/tmp/wmma-width-gap');runpy.run_path(str(h/'prepare-grid.py'))
(out/'rows.hip').write_text((out/'multi.hip').read_text()+'\n'+(h/'load-rows.inc').read_text())
s=(out/'bench-grid.cpp').read_text();a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a)
s=s[:a]+''' std::vector<Pair>pairs={
 {"row_control",{"pair128_loadonly_multi",4,0,0,640},{"pair128_loadonly_rows",4,1023,0,640}},
 {"row_fold",{"pair128_loadonly_rows",4,1023,0,640},{"pair128_loadonly_rows",4,255,0,640}},
 {"same_workset",{"pair128_loadonly_rows",4,255,0,400},{"pair128_loadonly_rows",4,255,0,640}},
 {"boundary_low",{"pair128_loadonly_rows",4,255,0,496},{"pair128_loadonly_rows",4,255,0,512}},
 {"boundary_high",{"pair128_loadonly_rows",4,255,0,512},{"pair128_loadonly_rows",4,255,0,528}}
 };
'''+s[b:];(out/'bench-rows.cpp').write_text(s)
