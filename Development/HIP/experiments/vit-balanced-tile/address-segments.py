"""Count aligned address segments touched by a wave's loads, not hardware traffic."""
import json
from pathlib import Path

def offset(row,k):return ((row//16)*32+k//32)*512+((k%32)//8)*128+(row%16)*8+k%8

def segments(addrs,size):return len({(a+b)//size for a in addrs for b in range(8)})
out={}
for size in [32,64,128]:
 ar=segments([(lane%16)*1024+(lane//16)*8 for lane in range(32)],size)
 at=segments([offset(lane%16,(lane//16)*8) for lane in range(32)],size)
 b=segments([offset(lane%16,(lane//16)*8) for lane in range(32)],size)
 out[size]={'A_row_per_fragment':ar,'A_tile_per_fragment':at,'B_per_fragment':b,'M16N64_row_sum':ar+4*b,'M32N32_row_sum':2*ar+2*b,'M16N64_tile_sum':at+4*b,'M32N32_tile_sum':2*at+2*b}
print(json.dumps(out,indent=2))
Path(__file__).resolve().parents[3].joinpath('results/vit-balanced-tile-20260922/address-segments.json').write_text(json.dumps(out,indent=2)+'\n')
