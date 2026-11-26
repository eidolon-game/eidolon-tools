"""Independent regression checks for published graph catalog and authored geometry."""
import hashlib
import json
import pathlib
import sys
from first_descent import authored, verify


def check_graphs(data):
    floors=data['floors']
    expected={f'{d}.{n:03}' for d in ('abyss','eternity') for n in range(1,101)}
    assert len(floors)==200 and {f['id'] for f in floors}==expected
    for f in floors:
        nodes=set(f['nodes']); edges=f['edges']
        assert len(nodes)==len(f['nodes']) and all(a in nodes and b in nodes for a,b in edges)
        def reach(start,blocked=None):
            seen={start}
            for _ in nodes:
                for a,b in edges:
                    if a in seen and b!=blocked: seen.add(b)
            return seen
        assert reach(f['entry'])==nodes
        assert f['exit'] not in reach(f['entry'],f['objective'])
        assert f['exit'] in reach(f['checkpoint'])


def rejects(fn):
    try: fn()
    except AssertionError: return
    raise AssertionError('negative fixture accepted')


if __name__=='__main__':
    raw=pathlib.Path(sys.argv[1]).read_bytes(); data=json.loads(raw)
    check_graphs(data)
    data['floors'][0]['edges'].append(['entry','exit'])
    rejects(lambda:check_graphs(data))
    d=authored(); verify(d)
    d['cells'].append((10,1)); rejects(lambda:verify(d))
    d=authored(); d['cells'].append((99,99)); rejects(lambda:verify(d))
    print('PASS 200 graphs; authored geometry; 3 rejected negative fixtures')
    print('catalog git blob',hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
