"""Check bijection, including the 25-row final partial group in the 900 preset."""
checks = 0
for rows in (1, 2, 3, 7, 8, 9, 16, 25, 40):
    for cols in (1, 16, 64):
        for gm in (2, 4, 8):
            seen = set()
            for idx in range(rows*cols):
                group, within = divmod(idx, gm*cols)
                base = group*gm
                size = min(gm, rows-base)
                m, n = base+within%size, within//size
                assert 0 <= m < rows and 0 <= n < cols
                assert (m, n) not in seen
                seen.add((m, n));checks += 1
            assert len(seen) == rows*cols
print(f'PASS {checks} mapped tiles, no duplicates or omissions')
