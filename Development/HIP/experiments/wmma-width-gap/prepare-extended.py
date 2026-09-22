from pathlib import Path
h=Path(__file__).resolve().parent;root=h.parents[3];out=Path('/tmp/wmma-width-gap')
(out/'extended.hip').write_text((h/'kernel.hip').read_text()+'\n'+(h/'load-only.inc').read_text())
s=(h/'bench.cpp').read_text().replace('../../hip_api.h',str(root/'Development/HIP/hip_api.h'))
a=s.index(' std::vector<Pair>pairs=');b=s.index(' FILE*csv=fopen(',a)
s=s[:a]+''' std::vector<Pair>pairs={
 {"load_ceiling",{"pair128",4,0,0},{"pair128_loadonly",4,0,0}}
 };
'''+s[b:]
s=s.replace('double flops=double(groups)*rounds*16*8192,tf=flops/(us*1e6);','double flops=std::string(c.name)=="pair128_loadonly"?0.:double(groups)*rounds*16*8192,tf=flops/(us*1e6);')
(out/'bench-extended.cpp').write_text(s)
s=(h/'numeric.cpp').read_text().replace('../../hip_api.h',str(root/'Development/HIP/hip_api.h')).replace('"pair128_adjacent"}', '"pair128_adjacent","pair128_loadonly"}')
s=s.replace('unsigned bad=0;for(unsigned i=0;i<v.size();i++)bad+=v[i]!=ref[i]||!std::isfinite(v[i]);', '''auto expected=ref;if(std::string(name)=="pair128_loadonly"){
 auto word=[](const std::vector<unsigned char>&v,size_t p){return unsigned(v[p])|(unsigned(v[p+1])<<8)|(unsigned(v[p+2])<<16)|(unsigned(v[p+3])<<24);};
 for(unsigned block=0;block<groups;block++)for(unsigned lane=0;lane<32;lane++){unsigned total=0,r=lane%16,g=lane/16;
  for(unsigned k=0;k<1024;k+=32){for(unsigned e=0;e<4;e++)total^=word(a1,r*1024+k+g*16+e*4);
   for(unsigned n=0;n<4;n++){unsigned row=block*64+n*16+r;for(unsigned e=0;e<4;e++)total^=word(b1,row/16*16384+k/32*512+(g*16+row%16)*16+e*4);}
  }expected[block*32+lane]=float(total)+208.f;
 }}unsigned bad=0;for(unsigned i=0;i<v.size();i++)bad+=v[i]!=expected[i]||!std::isfinite(v[i]);''')
(out/'numeric-extended.cpp').write_text(s)
