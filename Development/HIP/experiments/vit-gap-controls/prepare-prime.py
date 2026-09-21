from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent;out=Path('/tmp/vit-gap-controls/prime');out.mkdir(parents=True,exist_ok=True)
shutil.copytree(Path('/tmp/vit-gap-controls/Development'),out/'Development',dirs_exist_ok=True)
p=out/'Development/HIP/hip_reference_network.h';s=p.read_text();old=(here/'timing.inc').read_text();assert old in s
new=old.replace('"u1","u2","u4","u8","u16","group4","group8","nmajor","token_fixed","m2"','"memory_prime"').replace('auto probe=Fn(module,std::string("probe_")+variant);','auto probe=original;')
new=new.replace('  FILE*csv=', '''  void*prime_a{},*prime_b{};size_t prime_bytes=128ull*1024*1024;api.Check(api.hipMalloc(&prime_a,prime_bytes),"prime alloc");api.Check(api.hipMalloc(&prime_b,prime_bytes),"prime alloc");api.Check(api.hipMemsetAsync(prime_a,0,prime_bytes,stream),"prime init");api.Check(api.hipStreamSynchronize(stream),"prime init ready");
  FILE*csv=''')
needle='    for(unsigned i=0;i<32;i++)launch(fn);'
new=new.replace(needle,'''    auto prime_start=std::chrono::steady_clock::now();do{
     if(base){for(unsigned i=0;i<64;i++)launch(original);}else{for(unsigned i=0;i<32;i++)api.Check(api.hipMemcpyAsync(prime_b,prime_a,prime_bytes,3,stream),"memory prime");}
     api.Check(api.hipStreamSynchronize(stream),"prime ready");
    }while(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-prime_start).count()<200.);
'''+needle)
new=new.replace('  fclose(csv);launch(original);','  fclose(csv);api.hipFree(prime_a);api.hipFree(prime_b);launch(original);');s=s.replace(old,new);p.write_text(s)
shutil.copyfile('/tmp/vit-gap-controls/pure.cpp',out/'prime.cpp')
