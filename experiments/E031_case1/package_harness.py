"""Complete the immutable first export with its separately read-back build.sh."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
target=HERE/'harness_snapshot_complete_20261015.zip'
assert not target.exists(),'Preserve existing package'
with zipfile.ZipFile(HERE/'harness_snapshot_20261015.zip') as old:
    files={name:old.read(name) for name in old.namelist() if name!='HARNESS_MANIFEST.json'}
files['cloud_bench/build.sh']=(HERE/'harness/cloud_bench/build.sh').read_bytes()
manifest=[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
          for name,data in sorted(files.items())]
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in files.items():z.writestr(name,data)
    z.writestr('HARNESS_MANIFEST.json',json.dumps(manifest,indent=2))
(HERE/'harness/HARNESS_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(files=len(manifest),archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
