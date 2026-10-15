"""Independently compare actual candidate source outside the selected half branch."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
def block_end(text,open_at):
    level=0
    for i in range(open_at,len(text)):
        if text[i]=='{':level+=1
        elif text[i]=='}':
            level-=1
            if level==0:return i+1
    raise ValueError('Unbalanced function/branch')
def normalize(text,candidate):
    if candidate:
        hits=list(re.finditer(r'__global__ __vector__ void e031_case1_\w+\(',text))
        assert len(hits)==1
        begin=hits[0].start();end=block_end(text,text.index('{',begin))
        text=text[:begin]+text[end:]
    start=text.index('if (rows == 1 && d == 64)')
    end=block_end(text,text.index('{',start))
    part=text[start:end]
    half=part.index('else if (input.dtype == 1)')
    hb=part.index('{',half);he=block_end(part,hb)
    part=part[:hb]+'{ /* isolated FP16 D64 launch */ }'+part[he:]
    text=text[:start]+part+text[end:]
    # Removing one helper leaves a harmless extra blank line.
    return re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',text)
base=(HERE/'BASE/code/kernel.asc').read_bytes()
assert hashlib.sha256(base).hexdigest()=='e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
receipt=json.loads((HERE/'BASE/best_source_manifest.json').read_text())
for entry in receipt['files']:
    b=(HERE/'BASE'/entry['path']).read_bytes()
    assert len(b)==entry['bytes'] and hashlib.sha256(b).hexdigest()==entry['sha256']
expected=normalize(base.decode().replace('\r\n','\n'),False)
rows=[]
for path in sorted(HERE.glob('*/manifest.json')):
    m=json.loads(path.read_text());source=path.parent/'code/kernel.asc'
    b=source.read_bytes()
    assert m['baseline_sha256']==hashlib.sha256(base).hexdigest()
    assert hashlib.sha256(b).hexdigest()==m['source_sha256'],source
    other_files=0
    for entry in receipt['files']:
        if entry['path']=='code/kernel.asc':continue
        assert (path.parent/entry['path']).read_bytes()==(HERE/'BASE'/entry['path']).read_bytes()
        other_files+=1
    recovered=normalize(b.decode().replace('\r\n','\n'),True)
    assert recovered==expected,'Changes outside scope: '+m['variant']
    rows.append(dict(variant=m['variant'],source_sha256=m['source_sha256'],
                     all_other_source_equal=True,other_project_files_equal=other_files))
result=dict(baseline_sha256=hashlib.sha256(base).hexdigest(),
            outside_scope_sha256=hashlib.sha256(expected.encode()).hexdigest(),
            variants=rows,retained_root_kernel_sha256=hashlib.sha256((HERE.parents[1]/'kernel.asc').read_bytes()).hexdigest())
(HERE/'scope_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified scope for',len(rows),'candidates; every other source path is identical to H6SHARE.')
