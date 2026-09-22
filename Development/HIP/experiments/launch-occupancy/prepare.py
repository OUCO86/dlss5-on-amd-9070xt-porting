# Launch-level occupancy profile: reuse the three in-kernel phase-trace experiments (C32 ten kernels, mh_fast
# ffn_fused_c256, mh_fused c256_attention) and add two 64-bit real-time stamps per wave (entry/exit,
# __builtin_readsteadycounter = s_sendmsg_rtn REALTIME, constant 100MHz) in the two unused record slots 14/15.
# From them every launch gets: span (first wave in -> last wave out), summed wave busy time, concurrency curve,
# ramp / steady / tail split, and "throughput time" = busy / slots for comparison with the measured span.
from pathlib import Path
import subprocess, sys, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/launch-occupancy'); out.mkdir(exist_ok=True)
SRC={'c32':'c32-phase-trace','mhfast':'mhfast-phase-trace','mh':'mh-phase-trace'}
for tag,exp in SRC.items():
    subprocess.check_call([sys.executable,str(here.parent/exp/'prepare.py')])
    src=Path('/tmp')/exp; dst=out/tag
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns('*.exe','*.s','ev*','*.txt'))
    k=dst/'kernel.hip'; s=k.read_text()
    a='DEV u64 cyc(){return __builtin_readcyclecounter();}'
    b='TraceState ts{};ts.t[0]=cyc();'
    c='o[12]=ts.wait;o[13]=ts.n;}'
    assert s.count(a)==1 and s.count(b)==1 and s.count(c)==1,(tag,s.count(a),s.count(b),s.count(c))
    s=s.replace(a,a+'\nDEV u64 rtc(){return __builtin_readsteadycounter();}',1)
    s=s.replace(b,'TraceState ts{};u64 rt0=rtc();ts.t[0]=cyc();',1)
    # slot 13 (barrier count, a known constant per kernel) is replaced by HW_ID1 so every wave records its SE/SA/WGP/SIMD.
    s=s.replace(c,'o[12]=ts.wait;o[13]=hwid();o[14]=rt0;o[15]=rtc();}',1)
    s=s.replace('DEV u64 rtc(){return __builtin_readsteadycounter();}','DEV u64 rtc(){return __builtin_readsteadycounter();}\nDEV u64 hwid(){unsigned v;__asm__ volatile("s_getreg_b32 %0, hwreg(23, 0, 32)":"=s"(v));return v;}',1)
    k.write_text(s)
    n=dst/'network.cpp'; t=n.read_text().replace('"trace"','"trace"',1)
    n.write_text(t)
    print(tag,'patched')
