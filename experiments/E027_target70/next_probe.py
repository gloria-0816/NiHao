"""Second E027 trial: bounded composite correctness plus short-path diagnosis."""
from pathlib import Path
import json
import fcntl
import resume_probe as trial

core = trial.core
HERE = trial.HERE
ROOT = HERE / 'results' / 'attempt02'


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    with (HERE / 'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE) != trial.EXPECTED_BASE:
            raise ValueError('Baseline identity changed')
        name = 'FPB4RPL'
        proto = json.loads((HERE / 'protocol.json').read_text())
        if core.sha(trial.source(name)) != proto['variants'][name]['sha256']:
            raise ValueError('Combined source identity mismatch')
        folder = ROOT / 'build'
        folder.mkdir()
        cmd = ['env', 'ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0',
               'KERNEL_SOURCE='+str(trial.source(name)), 'BUILD_DIR='+str(trial.runner(name).parent),
               'bash', str(trial.OLD / 'cloud_bench/build.sh')]
        build = core.run_logged(cmd, folder/'stdout.log', folder/'stderr.log', 600)
        core.save(folder/'record.json', build)
        if build['returncode'] != 0 or build['timed_out']:
            raise RuntimeError('Combined candidate build failed')
        trial.ITEMS = [('s11',3749,3083,'float32'), ('s13',10300,3079,'float32'),
                       ('bound_low',161,3072,'float32'), ('bound_in',161,3073,'float32'),
                       ('bound_upper',161,3264,'float32'), ('bound_out',161,3265,'float32'),
                       ('rows_128',5120,3083,'float32'), ('rows_129',5160,3083,'float32')]
        trial.stage_inputs()
        records = []
        for cid, *_ in trial.ITEMS:
            b = trial.capture(cid,'FACC',ROOT/('check_'+cid+'_FACC'))
            c = trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
            c['bitwise_equal_FACC'] = c.get('output_sha256') == b.get('output_sha256')
            records.extend((b,c))
            core.save(ROOT/'checks.json',records)
            if b['status'] != 'measured_strict_pass' or c['status'] != 'measured_strict_pass' or not c['bitwise_equal_FACC']:
                raise RuntimeError('Combined boundary check failed: '+cid)
        pairs = []
        for block in range(2):
            for cid in ('s11','s13'):
                order = ('FACC',name,name,'FACC') if block==0 else (name,'FACC','FACC',name)
                for pos,v in enumerate(order):
                    r=trial.capture(cid,v,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)), 'ordinary')
                    pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] != 'measured_strict_pass':raise RuntimeError('Invalid comparison')
        trial.ITEMS = [('s1',1,64,'float16'), ('s2',7,197,'float32'),
                       ('s4',767,193,'float16'), ('s6',1513,577,'float16'), ('s7',3113,397,'float16')]
        trial.stage_inputs()
        diagnostic=[]
        for cid,*_ in trial.ITEMS:
            for mode in ('ordinary','op'):
                r=trial.capture(cid,'FACC',ROOT/('diagnose_'+cid+'_'+mode),mode)
                diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True)
        core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False))
        raise
