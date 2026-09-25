"""Compare ELF function bytes and summarize staging ISA without external packages."""
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys


def functions(path):
    data = Path(path).read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01', 'requires little-endian ELF64'
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, header[6]+i*header[11])
                for i in range(header[12])]
    out = {}
    for section in sections:
        if section[1] not in (2, 11):
            continue
        table = sections[section[6]]
        strings = data[table[4]:table[4]+table[5]]
        for offset in range(section[4], section[4]+section[5], section[9]):
            n, info, _, idx, value, size = struct.unpack_from('<IBBHQQ', data, offset)
            if info & 15 != 2 or not 0 < idx < len(sections):
                continue
            name = strings[n:].split(b'\0')[0].decode()
            target = sections[idx]
            pos = target[4]+value-target[3]
            out[name] = data[pos:pos+size]
    return out



baseline,candidate=functions(sys.argv[1]),functions(sys.argv[2]);assembly=Path(sys.argv[3]).read_text()
unchanged={n:candidate.get(n)==v for n,v in baseline.items()};assert unchanged and all(unchanged.values()),unchanged
report={'production_functions_identical':unchanged,'kernels':{}}
for name in candidate:
 if '_dz' not in name:continue
 original=name.rsplit('_dz',1)[0]
 if name.endswith('_dz1'):assert candidate[name]==baseline[original],name
 for n in (original,name):
  body=assembly[assembly.index('\n'+n+':')+1:];body=body[:body.index('\n.Lfunc_end')]
  match=re.search(r'\.set '+re.escape(n)+r'\.num_vgpr, (\d+)',assembly)
  report['kernels'][n]={'vgpr':int(match[1]),'code_bytes':len(candidate[n]),'static_wmma':len(re.findall(r'\bv_wmma_',body))}
print(json.dumps(report,indent=2))
