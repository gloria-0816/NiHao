"""Read-only export of experiment logs and the unchanged historical harness."""
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=Path('/home/developer/addrms_experiments/E031_case1')
target=OUT/'evidence_metadata_20261015.zip'
assert not target.exists(),'Preserve the existing evidence export'
manifest=[]
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.json','.csv','.log','.txt'):
            b=p.read_bytes();rel=p.relative_to(OUT).as_posix()
            manifest.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
            z.writestr(rel,b)
    z.writestr('EXPORT_MANIFEST.json',json.dumps(dict(
        exported_at=datetime.datetime.now().astimezone().isoformat(),files=manifest,
        excludes='Raw tensor binaries, runner executables and native profiler dump binaries remain on the cloud; their input/output/runner hashes are in the records.'),indent=2))
harness=OUT/'harness_snapshot_20261015.zip'
assert not harness.exists(),'Preserve the existing harness snapshot'
selected=[]
for p in (ROOT/'cloud_bench').rglob('*'):
    rel=p.relative_to(ROOT)
    if p.is_file() and not any(x.startswith('build') or x=='__pycache__' for x in rel.parts[:-1]) and (
        p.suffix in ('.py','.asc','.sh','.json','.md','.h') or p.name=='CMakeLists.txt'):
        selected.append(p)
for rel in ['experiments/E027_new_methods/run_round.py','experiments/E006A_probe/cloud_driver.py',
            'experiments/E006A_probe/protocol.json','experiments/E006A_probe/source_manifest.json']:
    selected.append(ROOT/rel)
with zipfile.ZipFile(harness,'w',zipfile.ZIP_DEFLATED) as z:
    entries=[]
    for p in sorted(set(selected)):
        b=p.read_bytes();rel=p.relative_to(ROOT).as_posix()
        entries.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
        z.writestr(rel,b)
    z.writestr('HARNESS_MANIFEST.json',json.dumps(entries,indent=2))
print(json.dumps(dict(evidence=str(target),evidence_bytes=target.stat().st_size,
    evidence_files=len(manifest),evidence_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    harness=str(harness),harness_files=len(selected),harness_sha256=hashlib.sha256(harness.read_bytes()).hexdigest())))
