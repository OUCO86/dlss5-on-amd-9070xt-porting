from pathlib import Path
root=Path(__file__).resolve().parents[4];s=(root/'Development/HIP/benchmark_live_capture.cpp').read_text()
s=s.replace('fprintf(csv,"frame,reset,wall_ms', 'FILE*tickcsv=_wfopen((prefix+L"-ticks.csv").c_str(),L"wb");if(!tickcsv)throw std::runtime_error("tick CSV");fprintf(tickcsv,"frame,end_tick_ms,wall_ms\\n");fprintf(csv,"frame,reset,wall_ms',1)
s=s.replace('walltotal+=elapsed;','walltotal+=elapsed;fprintf(tickcsv,"%u,%llu,%.9f\\n",i,GetTickCount64(),elapsed);',1)
s=s.replace('fclose(csv);','fclose(tickcsv);fclose(csv);',1)
out=Path('/tmp/clock-observe');out.mkdir(exist_ok=True);(out/'bench.cpp').write_text(s.replace('#include "../../src/','#include "'+str(root/'src')+'/'))
s=(root/'Development/HIP/read-adl-telemetry.cpp').read_text().replace('{1,2,8,19,20,23,27}','{1,2,3,8,19,20,23,27,30,35,44,55,73}');(out/'telemetry.cpp').write_text(s)
