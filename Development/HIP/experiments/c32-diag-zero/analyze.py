"""Summarize complete ABBA slots; report control noise beside each candidate."""
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1])
for path in sorted(root.glob('results-*/slots.csv')):
    groups = defaultdict(list)
    for row in csv.DictReader(path.open()):
        groups[int(row['repeat']), int(row['candidate'])].append(row)
    deltas = defaultdict(list)
    for (rep, candidate), rows in sorted(groups.items()):
        rows.sort(key=lambda r: int(r['slot']))
        assert [int(r['slot']) for r in rows] == [0, 1, 2, 3], (path, rep, candidate)
        assert [int(r['mode']) for r in rows] == [0, candidate, candidate, 0]
        assert all(int(r['diag_calls']) == int(r['frames'])*6 for r in rows)
        times = [float(r['ms']) for r in rows]
        delta = (times[1]+times[2]-times[0]-times[3])/2
        deltas[candidate].append(delta)
    for candidate, values in sorted(deltas.items()):
        print(f'{path.parent.name} candidate={candidate} B-A ms: '
              + ', '.join(f'{v:+.6f}' for v in values)
              + f'; mean={statistics.mean(values):+.6f}')
