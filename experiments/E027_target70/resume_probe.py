"""Independent E027 trials against the archived FACC; run serially on the NPU."""
import csv
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
OLD = Path('/mnt/workspace/addrms_cloudbench/huawei-CANN')
OUT = HERE / 'results' / 'attempt01'
spec = importlib.util.spec_from_file_location('e006_core', OLD / 'experiments/E006A_probe/cloud_driver.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.PROTOCOL = dict(timeout_ms=30000, process_timeout_s=240)
BASE_SOURCE = OLD / 'experiments/E026_target70/FACC/code/kernel.asc'
BASE_RUNNER = OLD / 'experiments/E026_target70/build_FACC/cloud_addrmsnormbias'
EXPECTED_BASE = 'bc62917a0b4e5a6155b188e5f829f32590832ba1e06345deb50564beacef356b'
ITEMS = [('s11', 3749, 3083, 'float32'), ('s13', 10300, 3079, 'float32')]


def source(name):
    return BASE_SOURCE if name == 'FACC' else HERE / name / 'kernel.asc'


def runner(name):
    return BASE_RUNNER if name == 'FACC' else HERE / ('build_' + name) / 'cloud_addrmsnormbias'


core.version = lambda name: (runner(name), core.sha(source(name)))
core.origin = lambda cid: HERE / 'inputs' / cid


def stage_inputs():
    for cid, rows, d, dtype in ITEMS:
        dest = core.origin(cid)
        if dest.exists():
            continue
        src = next((p / cid for p in [Path('/mnt/workspace/addrms_results/E021/inputs'),
                                     Path('/mnt/workspace/addrms_results/E023/inputs')]
                    if (p / cid / 'meta.json').exists()), None)
        dest.mkdir(parents=True)
        if src:
            for name in core.FILES:
                shutil.copy2(src / name, dest / name)
            meta = json.loads((dest / 'meta.json').read_text())
            for name, expected in meta['file_sha256'].items():
                if (dest / name).exists() and core.sha(dest / name) != expected:
                    raise ValueError('Staged input hash mismatch: ' + name)
        else:
            shape = [rows, d] if rows <= 8192 else [1, rows, d]
            dest.rmdir()
            core.case_data.generate(dest, shape, dtype, seed=42, case_id=cid)
        meta = json.loads((dest / 'meta.json').read_text())
        if meta['case_id'] != cid or meta['dtype'] != dtype or meta['shape'][-1] != d:
            raise ValueError('Staged input geometry mismatch')
        if __import__('math').prod(meta['shape'][:-1]) != rows:
            raise ValueError('Staged row count mismatch')


def capture(cid, name, folder, mode=None):
    if folder.exists():
        raise FileExistsError('Never reuse a prior run as new evidence: ' + str(folder))
    settings = dict(warmup=10 if mode else 0, repeats=1,
                    batch=5 if mode == 'op' else 20 if mode else 1, timing='host')
    rec = core.run_case(folder, cid, name, settings, mode)
    if rec['status'] not in ('measured_strict_pass', 'measured_strict_fail_retained'):
        return rec
    if mode == 'ordinary':
        tasks = []
        for p in (folder / 'profile').rglob('op_summary*.csv'):
            with p.open(encoding='utf-8-sig') as handle:
                tasks.extend(csv.DictReader(handle))
        tasks.sort(key=lambda r: float(r['Task Start Time(us)']))
        if len(tasks) != 31:
            raise ValueError('Expected 31 ordinary tasks, got ' + str(len(tasks)))
        rec['task_times_us'] = [float(r['Task Duration(us)']) for r in tasks[-20:]]
        rec['median_us'] = statistics.median(rec['task_times_us'])
        core.save(folder / 'record.json', rec)
    return rec


def main(mode):
    OUT.mkdir(parents=True, exist_ok=True)
    # Cooperating E027 commands hold this lock for the entire measurement block.
    # Actual device occupancy must be checked separately before starting.
    with (HERE / 'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if core.sha(BASE_SOURCE) != EXPECTED_BASE:
            raise ValueError('FACC source identity changed')
        protocol = json.loads((HERE / 'protocol.json').read_text())
        for name, meta in protocol['variants'].items():
            if core.sha(source(name)) != meta['sha256']:
                raise ValueError('Candidate source identity changed: ' + name)
        stage_inputs()
        if mode == 'baseline':
            records = []
            for cid, *_ in ITEMS:
                for capture_mode in ('ordinary', 'op'):
                    rec = capture(cid, 'FACC', OUT / ('baseline_' + cid + '_' + capture_mode), capture_mode)
                    records.append(rec)
                    core.save(OUT / 'baseline.json', records)
            return
        if mode == 'build':
            records = []
            for name in ('FPB4', 'FPRP'):
                dest = OUT / ('build_' + name)
                dest.mkdir(exist_ok=False)
                cmd = ['env', 'ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0',
                       'KERNEL_SOURCE=' + str(source(name)), 'BUILD_DIR=' + str(runner(name).parent),
                       'bash', str(OLD / 'cloud_bench/build.sh')]
                rec = core.run_logged(cmd, dest / 'stdout.log', dest / 'stderr.log', 600)
                rec.update(variant=name, source_sha256=core.sha(source(name)))
                if rec['returncode'] == 0 and runner(name).exists():
                    rec['runner_sha256'] = core.sha(runner(name))
                records.append(rec)
                core.save(dest / 'record.json', rec)
                core.save(OUT / 'builds.json', records)
                print(json.dumps(rec), flush=True)
            return
        if mode == 'check':
            records = []
            for cid, *_ in ITEMS:
                base = capture(cid, 'FACC', OUT / ('check_' + cid + '_FACC'))
                if base['status'] != 'measured_strict_pass':
                    raise ValueError('Baseline FP32 strict failure: ' + cid)
                records.append(base)
                for name in ('FPB4', 'FPRP'):
                    rec = capture(cid, name, OUT / ('check_' + cid + '_' + name))
                    rec['bitwise_equal_FACC'] = rec.get('output_sha256') == base['output_sha256']
                    records.append(rec)
                    core.save(OUT / 'checks.json', records)
                    if rec['status'] != 'measured_strict_pass' or not rec['bitwise_equal_FACC']:
                        raise ValueError('Structural candidate output changed: ' + cid + '/' + name)
            return
        if mode == 'pairs':
            checks = json.loads((OUT / 'checks.json').read_text())
            if not all(r['status'] == 'measured_strict_pass' and r.get('bitwise_equal_FACC', True) for r in checks):
                raise ValueError('Correctness preflight is incomplete')
            records = []
            for name in ('FPB4', 'FPRP'):
                for block in range(2):
                    for cid, *_ in ITEMS:
                        order = ('FACC', name, name, 'FACC') if block % 2 == 0 else (name, 'FACC', 'FACC', name)
                        for pos, version in enumerate(order):
                            rec = capture(cid, version, OUT / ('pair_' + name + '_' + cid + '_' + str(block) + '_' + str(pos)), 'ordinary')
                            rec.update(candidate_group=name, block=block, position=pos)
                            records.append(rec)
                            core.save(OUT / 'pairs.json', records)
                            if rec['status'] != 'measured_strict_pass':
                                raise ValueError('Invalid measured run')
            summary = []
            for name in ('FPB4', 'FPRP'):
                for cid, *_ in ITEMS:
                    selected = [r for r in records if r['case_id'] == cid and r['candidate_group'] == name]
                    b = [r['median_us'] for r in selected if r['variant'] == 'FACC']
                    c = [r['median_us'] for r in selected if r['variant'] == name]
                    summary.append(dict(candidate=name, case_id=cid, base_us=b, candidate_us=c,
                                        gain_pct=100 * (statistics.median(b)-statistics.median(c))/statistics.median(b)))
            core.save(OUT / 'summary.json', summary)
            print(json.dumps(summary), flush=True)
            return
        raise ValueError('Unknown mode: ' + mode)


if __name__ == '__main__':
    mode = sys.argv[1]
    started = time.time()
    try:
        main(mode)
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        core.save(OUT / (mode + '_completion.json'), dict(status='failed', error=str(exc), elapsed_s=time.time()-started))
        raise
    core.save(OUT / (mode + '_completion.json'), dict(status='completed', elapsed_s=time.time()-started))
