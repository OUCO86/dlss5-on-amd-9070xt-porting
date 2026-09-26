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
assembly = Path(sys.argv[3]).read_text()
unchanged = {name: candidate.get(name) == code for name, code in baseline.items()}
assert unchanged and all(unchanged.values()), unchanged
post = 'vit_expand_blocked_fp8_frag_bytein'
assert candidate[post] == candidate[post+'_order1']
contract = 'vit_contract_blocked_fp8_frag'
if contract+'_order1' in candidate:
    assert candidate[contract] == candidate[contract+'_order1']
report = {'production_functions_identical': unchanged, 'control_identical': True, 'kernels': {}}
for name in candidate:
    if not (name == post or name.startswith(post+'_order') or name == contract or name.startswith(contract+'_order')):
        continue
    body = assembly[assembly.index('\n'+name+':')+1:]
    body = body[:body.index('\n.Lfunc_end')]
    staging = body
    vgpr = re.search(r'\.set '+re.escape(name)+r'\.num_vgpr, (\d+)', assembly)
    report['kernels'][name] = {
        'code_bytes': len(candidate[name]),
        'vgpr': int(vgpr[1]) if vgpr else None,
        'static_global_loads': dict(Counter(re.findall(r'\bglobal_load_\w+', staging))),
    }
print(json.dumps(report, indent=2))
