{auto vacload=[&](const char*key,const char*file){if(!modules.count(key)){Handle mm{};api.Check(api.LoadModule(&mm,(opt.modules+"/"+file).c_str()),file);modules[key]=mm;}};
 static const std::set<std::string> attn={"vit_attention_fused_256_bytein","vit_attention_fused_400_bytein","vit_attention_fused_640_bytein"};
 if(cand==2&&module=="deep_fast"&&kernel=="vit_qkv_project_normalize_fused_f16compact_fp8_frag"){vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_vt";++cand_hits;}
 if(cand==2&&module=="deep_fast"&&attn.count(kernel)&&!groups){vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_vt";++cand_hits;}
 if(cand==3&&module=="deep_fast"&&attn.count(kernel)&&!groups){vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_swap";++cand_hits;}
 if(cand==4&&module=="deep_fast"&&kernel=="vit_qkv_project_normalize_fused_f16compact_fp8_frag"){vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_vt";++cand_hits;}
 if(cand==4&&module=="deep_fast"&&attn.count(kernel)&&!groups){vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_swapvt";++cand_hits;}
 if(cand==5&&module=="c32_wave1"&&kernel=="c32_wave1_prefix"){vacload("vac_c32","vac-c32.hsaco");module="vac_c32";++cand_hits;}
 if(cand==1&&module=="deep_fast"&&attn.count(kernel)&&!groups&&count%512==0){U t=count/512;vacload("vac_deep","vac-deep.hsaco");module="vac_deep";kernel+="_m32";groups=((t+31)/32)*32;++cand_hits;}
}
