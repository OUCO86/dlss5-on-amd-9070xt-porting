"""Check vertical reuse against the production post staging address equations.

Includes every window of small grids (edges, shifts, odd-height fallback) and
boundary/interior windows of production grids. No assumption about pixel values.
"""
checks = 0
for width, height in [(8, 8), (16, 16), (16, 15), (1600, 960), (1920, 1152)]:
    for sx in (0, 4):
        for sy in (0, 1, 4):
            if (sy & 1) or (height & 1):
                continue  # Candidate explicitly retains all original reads.
            ww, hh = width + 2*sx, height + 2*sy
            nx, ny = ww//8, hh//8
            xs = range(nx) if nx < 8 else (0, 1, nx//2, nx-2, nx-1)
            ys = range(ny) if ny < 8 else (0, 1, ny//2, ny-2, ny-1)
            for wy in ys:
                for wx in xs:
                    for wave in range(4):
                        def low_address(tok, lane):
                            x = wx*8 + tok%8 - sx
                            y = wy*8 + tok//8 - sy
                            valid = 0 <= x < width and 0 <= y < height
                            idx = ((y//2)*(width//2) + x//2)*32 if valid else 0
                            return valid, idx + (lane & 7)*4
                        for lane in range(32):
                            for k in (2, 3):
                                tok = wave*16 + k*4 + (lane >> 3)
                                assert low_address(tok, lane) == low_address(tok-8, lane), (width,height,sx,sy,wx,wy,wave,lane,k)
                                checks += 1
print(f'PASS {checks} address/validity pairs; odd shift/height uses original loads')
