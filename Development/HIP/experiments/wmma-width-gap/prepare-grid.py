from pathlib import Path
import runpy
h=Path(__file__).resolve().parent;out=Path('/tmp/wmma-width-gap');runpy.run_path(str(h/'prepare-multi.py'))
s=(out/'bench-multi.cpp').read_text().replace('unsigned chains,as,bs;', 'unsigned chains,as,bs,tokens=640;')
a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a)
s=s[:a]+''' std::vector<Pair>pairs={
 {"wmma_grid",{"pair128",4,0,0,400},{"pair128",4,0,0,640}},
 {"load_grid",{"pair128_loadonly_multi",4,0,0,400},{"pair128_loadonly_multi",4,0,0,640}},
 {"original_grid",{"model4",4,1023,1023,400},{"model4",4,1023,1023,640}},
 {"single_grid",{"pair128_loadonly",4,0,0,400},{"pair128_loadonly",4,0,0,640}}
 };
'''+s[b:]
s=s.replace('pair.b:pair.a;Handle fn{};', 'pair.b:pair.a;groups=c.tokens/16*64;Handle fn{};')
s=s.replace('c.as,c.bs,tokens,rounds,n,us,tf','c.as,c.bs,c.tokens,rounds,n,us,tf')
s=s.replace('std::string(c.name)=="pair128_loadonly_multi"','std::string(c.name).find("loadonly")!=std::string::npos')
s=s.replace('if(tokens!=400&&tokens!=640)', 'if(tokens!=640)')
s=s.replace(' printf("conditioned=%u\\n",unsigned(conditioned));', ' printf("conditioned=%u fixed_A_bytes=%llu fixed_B_bytes=%llu A=%p B=%p\\n",unsigned(conditioned),(unsigned long long)A.size(),(unsigned long long)B.size(),a,b);')
(out/'bench-grid.cpp').write_text(s)
