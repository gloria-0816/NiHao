"""E031: independent case1 candidates on the exact H6SHARE source."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESS = (ROOT if (ROOT/'experiments/E027_new_methods/run_round.py').exists()
           else HERE/'harness')
OUT = Path('/home/developer/addrms_experiments/E031_case1')
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('e027', HARNESS/'experiments/E027_new_methods/run_round.py')
previous = importlib.util.module_from_spec(spec)
saved = sys.argv[:]
sys.argv = ['run_round.py', 'library_only']
try:
    spec.loader.exec_module(previous)
finally:
    sys.argv = saved
previous.OUT = OUT
previous.source = lambda v: HERE/v/'code/kernel.asc'
previous.runner = lambda v: HERE/('build_'+v)/'cloud_addrmsnormbias'
previous.core.version = lambda v: (previous.runner(v), previous.core.sha(previous.source(v)))
previous.core.origin = lambda cid: OUT/'inputs'/cid
core = previous.core


def case(cid, rows=1, d=64, dtype='float16', seed=42, pattern='uniform'):
    target = core.origin(cid)
    if not target.exists():
        target.parent.mkdir(exist_ok=True)
        core.case_data.generate(target, [1, rows, d], dtype, seed=seed,
                                pattern=pattern, case_id=cid, max_tensor_mib=8)
    return cid


def check(variant):
    specs = [('uniform42', 42, 'uniform'), ('uniform7', 7, 'uniform'),
             ('uniform2026', 2026, 'uniform'), ('zeros', 42, 'zeros'),
             ('cancel', 42, 'cancel'), ('checkerboard', 42, 'checkerboard'),
             ('wide_range', 42, 'wide_range'), ('specials', 42, 'specials')]
    rows = []
    for name, seed, pattern in specs:
        cid = case('e031_h64_'+name, seed=seed, pattern=pattern)
        pair = []
        for version in ['BASE', variant]:
            folder = OUT/'checks'/cid/version
            record = (json.loads((folder/'record.json').read_text())
                      if (folder/'record.json').exists() else previous.run(cid, version, folder))
            pair.append(record)
        row = dict(case_id=cid, variant=variant,
                   base_strict_pass=pair[0].get('strict', {}).get('pass'),
                   candidate_strict_pass=pair[1].get('strict', {}).get('pass'),
                   base_failed=pair[0].get('strict', {}).get('failed_elements'),
                   candidate_failed=pair[1].get('strict', {}).get('failed_elements'),
                   bitwise_equal=pair[0].get('output_sha256')==pair[1].get('output_sha256'),
                   new_strict_failure=pair[0].get('strict', {}).get('pass') and
                                      not pair[1].get('strict', {}).get('pass'))
        rows.append(row)
        core.save(OUT/('check_'+variant+'.json'), rows)
    print(json.dumps({'variant': variant, 'checks': rows}), flush=True)


def profile(variant, label, mode='ordinary'):
    cid = case('e031_h64_uniform42')
    folder = OUT/'performance'/label
    if folder.exists():
        raise RuntimeError('Preserve existing measurement: '+str(folder))
    if mode == 'ordinary':
        record = previous.run(cid, variant, folder, True)
    else:
        record = core.run_case(folder, cid, variant,
                              dict(warmup=10, repeats=1, batch=5, timing='host'), 'op')
    print(json.dumps(dict(variant=variant, label=label, status=record['status'],
                          median_us=record.get('median_us'))), flush=True)


def infinity_check(variant):
    cd = core.case_data
    old_patterns, old_chunk = cd.PATTERNS, cd._input_chunk
    def chunk(pattern, which, start, nrows, d, rng, directory, dtype):
        data = old_chunk('uniform', which, start, nrows, d, rng, directory, dtype)
        if which == 'x':
            data[0, 0] = float('inf') if pattern == 'inf_positive' else -float('inf')
        elif which == 'residual':
            data[0, 0] = 0
        return data
    cd.PATTERNS = old_patterns + ('inf_positive', 'inf_negative')
    cd._input_chunk = chunk
    try:
        for pattern in ['inf_positive', 'inf_negative']:
            cid = 'e031_h64_'+pattern
            target = core.origin(cid)
            if not target.exists():
                cd.generate(target, [1, 1, 64], 'float16', seed=42,
                            pattern=pattern, case_id=cid, max_tensor_mib=8)
    finally:
        cd.PATTERNS, cd._input_chunk = old_patterns, old_chunk
    records=[]
    for pattern in ['inf_positive', 'inf_negative']:
        cid='e031_h64_'+pattern
        pair=[]
        for version in ['BASE', variant]:
            folder=OUT/'infinity_checks'/cid/version
            r=(json.loads((folder/'record.json').read_text())
               if (folder/'record.json').exists() else previous.run(cid,version,folder))
            pair.append(r)
        records.append(dict(case_id=cid,variant=variant,
            base_strict_pass=pair[0]['strict']['pass'],
            candidate_strict_pass=pair[1]['strict']['pass'],
            bitwise_equal=pair[0]['output_sha256']==pair[1]['output_sha256'],
            candidate_failed=pair[1]['strict']['failed_elements']))
        core.save(OUT/('infinity_'+variant+'.json'),records)
    print(json.dumps(records),flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'build':
        previous.build(sys.argv[2:])
    elif action == 'check':
        for variant in sys.argv[2:]:
            check(variant)
    elif action == 'profile':
        profile(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv)>4 else 'ordinary')
    elif action == 'infinity_check':
        infinity_check(sys.argv[2])
    elif action == 'screen':
        for variant in sys.argv[3:]:
            checks = json.loads((OUT/('check_'+variant+'.json')).read_text())
            if any(row['new_strict_failure'] for row in checks):
                print(json.dumps(dict(variant=variant, skipped='new strict failure')), flush=True)
                continue
            profile(variant, sys.argv[2]+'_'+variant)
        profile('BASE', sys.argv[2]+'_BASE_end')
    else:
        raise ValueError(action)
