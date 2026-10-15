"""Summarize preserved records, including both modes of the bimodal timings."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,statistics,zipfile
HERE=Path(__file__).resolve().parent
archive=zipfile.ZipFile(HERE/'evidence_metadata_20261015.zip')
paths=sorted(archive.namelist())
def read(path):return archive.read(path)
def read_json(path):return json.loads(read(path))
manifest=read_json('EXPORT_MANIFEST.json')
for x in manifest['files']:
    b=read(x['path'])
    assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'],x['path']
for filename in ['evidence_metadata_20261015.zip','harness_snapshot_20261015.zip','harness_snapshot_complete_20261015.zip']:
    with zipfile.ZipFile(HERE/filename) as z:assert z.testzip() is None,filename
with zipfile.ZipFile(HERE/'harness_snapshot_complete_20261015.zip') as z:
    harness_manifest=json.loads(z.read('HARNESS_MANIFEST.json'))
    for x in harness_manifest:
        b=z.read(x['path'])
        assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
builds=[]
for p in [Path(p) for p in paths if p.startswith('build_') and p.count('/')==1 and p.endswith('/record.json')]:
    r=read_json(p.as_posix());variant=p.parent.name.removeprefix('build_')
    source=HERE/variant/'code/kernel.asc'
    assert r['returncode']==0 and r['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    builds.append(dict(variant=variant,source_sha256=r['source_sha256'],runner_sha256=r['runner_sha256']))
records=[];unfinished=[]
for p in [Path(p) for p in paths if p.endswith('/record.json')]:
    r=read_json(p.as_posix())
    if 'case_id' not in r:continue
    if not r.get('benchmark'):
        unfinished.append(dict(path=p.as_posix(),status=r.get('status'),valid_timing=False,
            explanation='Preparation failed before NPU launch: msprof was outside PATH; stale status, not a running job.'))
        continue
    b=next(x for x in builds if x['variant']==r['variant'])
    assert r['runner_sha256']==b['runner_sha256'] and r['kernel_sha256']==b['source_sha256']
    records.append(r)
checks=[]
for p in [p for p in paths if '/' not in p and p.startswith('check_') and p.endswith('.json')]:
    rows=read_json(p);assert len(rows)==8 and not any(r['new_strict_failure'] for r in rows)
    checks.append(dict(variant=rows[0]['variant'],count=len(rows),strict_pass=sum(r['candidate_strict_pass'] for r in rows),
                       bitwise_equal=sum(r['bitwise_equal'] for r in rows)))
perf=[]
for p in [Path(p) for p in paths if p.startswith('performance/') and p.count('/')==2 and p.endswith('/record.json')]:
    r=read_json(p.as_posix());t=r.get('task_times_us')
    if not t:continue
    assert len(t)==20
    s=sorted(t)
    perf.append(dict(label=p.parent.name,variant=r['variant'],median_us=r['median_us'],
                     lower_half_median_us=statistics.median(s[:10]),upper_half_median_us=statistics.median(s[10:]),
                     min_us=min(t),max_us=max(t),task_times_us=t))
op_metrics=[]
for p in paths:
    if p.startswith('performance/baseline_op_01/') and '/PipeUtilization_' in p and p.endswith('.csv'):
        for r in csv.DictReader(io.StringIO(read(p).decode('utf-8-sig'))):
            op_metrics.append({k:float(r[k]) for k in ['aiv_time(us)','aiv_vec_time(us)',
                'aiv_mte2_time(us)','aiv_scalar_time(us)','aiv_icache_miss_rate','aiv_scalar_wait_ib_time(us)']})
assert len(op_metrics)==5
result=dict(builds=builds,checks=checks,performance=perf,baseline_op_metrics=op_metrics,
            successful_npu_processes=len(records),status_counts=dict(Counter(r['status'] for r in records)),
            unfinished_records=unfinished,export_files_verified=len(manifest['files']),
            harness_files_verified=len(harness_manifest),
            infinity_checks=read_json('infinity_NR2.json'))
(HERE/'cloud_summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(builds=len(builds),candidates=len(checks),successful_npu_processes=len(records),
    statuses=result['status_counts'],valid_device_profiles=len(perf),export_files_verified=len(manifest['files']))))
for r in perf:print(r['label'],r['median_us'],r['lower_half_median_us'],r['upper_half_median_us'])
