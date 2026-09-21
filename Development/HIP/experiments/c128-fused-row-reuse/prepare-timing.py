from pathlib import Path
root=Path(__file__).resolve().parents[4];out=Path('/tmp/c128-fused-row-reuse')
# Reuse the validated pure-HIP input/expected-output harness, at post_shift=3.
helper=root/'Development/HIP/experiments/kernel-bottleneck/prepare-pure.py'
s=helper.read_text().replace("out=Path('/tmp/kernel-bottleneck')", "out=Path('/tmp/c128-fused-row-reuse')")
exec(compile(s,str(helper),'exec'),{'__file__':str(helper)})
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text()
s=s.replace('class Network {','class Network {\n bool row_reuse_timed=false;',1)
s=s.replace('if(m32.count(kernel)){','if(m32.count(kernel)&&!std::getenv("DLSS5_C128_M32_DISABLE")){',1)
needle='for(unsigned repeat=0;repeat<repeats_here;repeat++)api.Check('
assert s.count(needle)==1
injection='''if(!row_reuse_timed&&(kernel=="mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb"||kernel=="mh_ffn_fused_c128_project_mapped_g128_qkv_bytein_fb_m32")){
 row_reuse_timed=true;auto fn=Fn(module,kernel);auto launch=[&](){api.Check(api.hipModuleLaunchKernel(fn,groups,1,1,threads,1,1,0,stream,argv,nullptr),"row reuse timing");};
 api.Check(api.hipStreamSynchronize(stream),"timing drain");
 for(unsigned i=0;i<2000;i++)launch();api.Check(api.hipStreamSynchronize(stream),"timing warmup");
 auto begin=std::chrono::steady_clock::now();for(unsigned i=0;i<10000;i++)launch();api.Check(api.hipStreamSynchronize(stream),"timing complete");
 double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-begin).count()/10000;
 printf("ROW_REUSE kernel=%s groups=%u threads=%u mean_us=%.6f\\n",kernel.c_str(),groups,threads,us);fflush(stdout);
 }
 '''
s=s.replace(needle,injection+needle,1);p.write_text(s)
