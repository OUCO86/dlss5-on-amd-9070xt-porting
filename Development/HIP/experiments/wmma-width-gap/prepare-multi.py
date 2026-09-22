from pathlib import Path
import runpy
h=Path(__file__).resolve().parent;out=Path('/tmp/wmma-width-gap')
runpy.run_path(str(h/'prepare-extended.py'))
(out/'multi.hip').write_text((out/'extended.hip').read_text()+'\n'+(h/'load-multi.inc').read_text())
s=(out/'bench-extended.cpp').read_text().replace('"load_ceiling",','"load_ceiling_multi",').replace('pair128_loadonly','pair128_loadonly_multi')
(out/'bench-multi.cpp').write_text(s)
s=(out/'numeric-extended.cpp').read_text().replace('pair128_loadonly','pair128_loadonly_multi')
(out/'numeric-multi.cpp').write_text(s)
