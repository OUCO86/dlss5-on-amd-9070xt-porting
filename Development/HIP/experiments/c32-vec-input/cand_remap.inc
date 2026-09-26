{static const char*cvi[]={nullptr,"cvi-vec.hsaco","cvi-vecsplit.hsaco","cvi-split.hsaco"};
 if(cand>=1&&cand<=3&&module=="c32_wave1"){std::string key=std::string("cvi")+char('0'+cand);if(!modules.count(key)){Handle mm{};api.Check(api.LoadModule(&mm,(opt.modules+"/"+cvi[cand]).c_str()),cvi[cand]);modules[key]=mm;}module=key;++cand_hits;}
}
