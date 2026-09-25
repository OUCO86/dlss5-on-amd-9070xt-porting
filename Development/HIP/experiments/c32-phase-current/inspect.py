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



baseline, candidate = functions(sys.argv[1]), functions(sys.argv[2])
assembly=Path(sys.argv[3]).read_text()
unchanged={name:candidate.get(name)==code for name,code in baseline.items()}
assert unchanged and all(unchanged.values()),unchanged
report={'production_functions_identical':unchanged,'kernels':{}}
for name in candidate:
    if name not in baseline and '_phase' not in name:continue
    body=assembly[assembly.index('\n'+name+':')+1:]
    body=body[:body.index('\n.Lfunc_end')]
    def resource(key):
        m=re.search(r'\.set '+re.escape(name)+r'\.'+key+r', (\d+)',assembly)
        return int(m[1]) if m else None
    counter=[x.strip() for x in body.splitlines() if 's_getreg_b32' in x]
    if '_phase' in name:
        assert counter and all('29' in x or 'SHADER_CYCLES' in x for x in counter),counter
        assert 's_sendmsg_rtn' not in body and 'REALTIME' not in body,name
    report['kernels'][name]={'code_bytes':len(candidate[name]),'vgpr':resource('num_vgpr'),'sgpr':resource('numbered_sgpr'),'private_bytes':resource('private_seg_size'),'counter_reads':len(counter)}
print(json.dumps(report,indent=2))
