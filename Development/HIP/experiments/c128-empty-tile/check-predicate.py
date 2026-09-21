"""Check the uniform empty-tile test against all16 mapped rows, including row wrap."""
from random import Random
rng=Random(20260921);shapes=[(w,h,sx,sy) for w,h in [(160,96),(200,120),(240,144)] for sx in (0,4) for sy in (0,4)]
shapes += [(rng.randrange(1,65),rng.randrange(1,33),rng.randrange(5),rng.randrange(5)) for _ in range(1000)]
checked=0;skipped=0;vertical_skipped=0
for width,height,sx,sy in shapes:
 workw=(width+sx+7)&~7;workh=(height+sy+7)&~7
 for first in range(0,workw*workh,16):
  y,x=divmod(first,workw);n0=min(16,workw-x);n1=16-n0
  valid0=y>=sy and y-sy<height and x<sx+width and x+n0>sx
  valid1=n1 and y+1>=sy and y+1-sy<height and n1>sx
  fast_empty=workw>=16 and not(valid0 or valid1)
  actual_empty=not any(0<=p%workw-sx<width and 0<=p//workw-sy<height for p in range(first,first+16))
  vertical_empty=first+15<sy*workw or first>=(sy+height)*workw
  assert not vertical_empty or actual_empty,(width,height,sx,sy,first)
  vertical_skipped+=bool(vertical_empty)
  assert not fast_empty or actual_empty,(width,height,sx,sy,first)
  if workw>=16:assert fast_empty==actual_empty,(width,height,sx,sy,first)
  checked+=1;skipped+=bool(fast_empty)
print(f'shapes={len(shapes)} tiles={checked} fast_empty={skipped} vertical_empty={vertical_skipped} false_skips=0')
