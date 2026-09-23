# Transposed projection/output for the fused attention kernels (c64/c128/c256, bit-exact): swap the operands of the
# residual-diag WMMAs and of the AV x W projection WMMAs so a lane holds one token row and 8 consecutive output
# columns; the output loop then stores 8 consecutive bytes per (lane, j) instead of 8 rows x 1 column, and the crop test
# runs once per lane. Same operands, same accumulation order -> identical bits. Module-set host.
#   pair1: c256 body only      pair2: c64 + c128 + c256      pair3 = pair1
from pathlib import Path
import re, shutil
here=Path(__file__).resolve().parent; root=here.parents[3]; out=Path('/tmp/mh-transposed-project')
for sub in ('pair1','pair2','pair3'): shutil.rmtree(out/sub, ignore_errors=True); (out/sub).mkdir(parents=True)
s0=(root/'hip/multihead_fused_attention.hip').read_text()
W='__builtin_amdgcn_wmma_f32_16x16x16_fp8_fp8_w32_gfx12'
def body(s,C,colbase,avstride,pm):
    n=0
    def rep(o,new,count=1):
        nonlocal s,n; assert s.count(o)==count,(o[:70],s.count(o)); s=s.replace(o,new); n+=1
    # 1. diag residual WMMA
    m=re.search(r'(__builtin_memcpy\(&b,diag\+\(part\*'+str(pm)+r'\+ct\)\*512\+\(gr\(\)\*16\+rc\(\)\)\*8,8\);result\[j\]=)'+re.escape(W)+r'\(a,b,result\[j\]\);',s)
    assert m and s.count(m.group(0))==1; s=s.replace(m.group(0),m.group(1)+W+'(b,a,result[j]);'); n+=1
    # 2. scalar residual (non-Diag) path: per element column
    m=re.search(r' else for\(uint j=0;j<2;j\+\+\)\{uint col='+re.escape(colbase)+r'\+j\*16\+rc\(\);float remain=w\[(.+?)\+col\];for\(uint part=0;part<3;part\+\+\)\{(float component;.*?remain-=component;)for\(uint e=0;e<8;e\+\+\)\{uint p=raster\(win,first\+gr\(\)\*8\+e,width\);float x=(ByteFeature\?.*?feature8\[p\*'+str(C)+r'\+col\]\),0\):.*?feature\[p\*'+str(C)+r'\+col\]\)\),0\));for\(uint half=0;half<2;half\+\+\)result\[j\]\[e\]=__builtin_fmaf\(x,half==\(col%32\)/16\?component:0\.f,result\[j\]\[e\]\);\}\}\}\n',s,re.S)
    assert m,('scalar residual',C)
    off,comp,xexpr=m.group(1),m.group(2),m.group(3)
    new=f' else for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){{uint col={colbase}+j*16+gr()*8+e;float remain=w[{off}+col];uint p=raster(win,first+rc(),width);float x={xexpr};for(uint part=0;part<3;part++){{{comp}for(uint half=0;half<2;half++)result[j][e]=__builtin_fmaf(x,half==(col%32)/16?component:0.f,result[j][e]);}}}}\n'
    s=s.replace(m.group(0),new); n+=1
    # 3. projection WMMA
    o=f'__builtin_memcpy(&a,avbytes+(first+rc())*{avstride}+k+gr()*8,8);'
    i=s.index(o); j=s.index('\n',i); line=s[i:j]
    assert line.count(W+'(a,b,result[j])')==1; s=s[:i]+line.replace(W+'(a,b,result[j])',W+'(b,a,result[j])')+s[j:]; n+=1
    # 4. output loop
    o=f' for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){{uint p=raster(win,first+gr()*8+e,width),col={colbase}+j*16+rc(),dest=p*{C}+col;if(cropw){{uint x=p%width,y=p/width;if(x<sx||y<sy||x>=sx+cropw||y>=sy+croph)continue;dest=((y-sy)*cropw+x-sx)*{C}+col;}}float v=result[j][e],o=post==3?Hrtz(v):post==0?F(Hrtz(v)):F(v);if constexpr(ByteOut)out8[dest]=static_cast<unsigned char>(fp8(o));else out[dest]=o;}}\n'
    new=f' {{uint p=raster(win,first+rc(),width),rowbase=p*{C};bool keep=true;if(cropw){{uint x=p%width,y=p/width;if(x<sx||y<sy||x>=sx+cropw||y>=sy+croph)keep=false;else rowbase=((y-sy)*cropw+x-sx)*{C};}}\n  if(keep)for(uint j=0;j<2;j++)for(uint e=0;e<8;e++){{uint col={colbase}+j*16+gr()*8+e,dest=rowbase+col;float v=result[j][e],o=post==3?Hrtz(v):post==0?F(Hrtz(v)):F(v);if constexpr(ByteOut)out8[dest]=static_cast<unsigned char>(fp8(o));else out[dest]=o;}}}}\n'
    rep(o,new)
    return s,n
s1,n1=body(s0,256,'localhead*64+pair*32',260,16)
s2,n2=body(s1,64,'head*32',68,4); s2,n3=body(s2,128,'head*32',132,8)
print('sites c256',n1,'c64',n2,'c128',n3)
for m,s in {1:s1,2:s2,3:s1}.items():
    (out/f'pair{m}'/'multihead_fused_attention.generated.hip').write_text('#define HIP_ISA_HALF 1\n#define HIP_MH_RTZ_ISA 1\n'+s+'\n')
print('written')
