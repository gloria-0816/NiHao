"""Compare independent output buffers and mask reuse; repeat parameter scheduling."""
import fcntl,json,statistics
from pathlib import Path
from harness import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase01b'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase01b.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise RuntimeError('Baseline changed')
        if core.sha(trial.BASE_RUNNER)!=proto['baseline']['runner_sha256']:raise RuntimeError('Cached baseline runner changed')
        installed_source=trial.OLD/'experiments/E027_new_methods/FRESLONG/code/kernel.asc'
        if core.sha(installed_source)!=trial.EXPECTED_BASE:raise RuntimeError('Cached baseline source changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__),harness_sha256=core.sha(HERE/'harness.py'),core_driver_sha256=core.sha(trial.OLD/'experiments/E006A_probe/cloud_driver.py'),baseline_runner_sha256=core.sha(trial.BASE_RUNNER)))
        for name,m in proto['variants'].items():
            if core.sha(trial.source(name))!=m['sha256']:raise RuntimeError('Source changed')
            prior=json.loads((HERE/'results/phase01'/('build_'+name)/'record.json').read_text())
            earlier=json.loads((HERE/'results/phase01/checks.json').read_text())
            candidates=[r for r in earlier if r['variant']==name and r['kernel_sha256']==m['sha256']]
            if prior['returncode']!=0 or prior['timed_out'] or not candidates:raise RuntimeError('Build reuse not proven '+name)
            if core.sha(trial.runner(name))!=candidates[0]['runner_sha256']:raise RuntimeError('Cached runner differs '+name)
            core.save(ROOT/('reused_build_'+name+'.json'),dict(original_build_directory=str(HERE/'results/phase01'/('build_'+name)),runner_sha256=core.sha(trial.runner(name)),source_sha256=m['sha256']))
        trial.ITEMS=[('s6',1513,577,'float16'),('s7',3113,397,'float16'),('s8',10240,512,'float16'),
                     ('dbd321',161,321,'float16'),('dbd384',1121,384,'float16'),
                     ('dbd640',1601,640,'float16'),('dbd641',1601,641,'float16'),
                     ('dbd1024',1601,1024,'float16')]
        trial.stage_inputs();checks=[]
        earlier=json.loads((HERE/'results/phase01/checks.json').read_text())
        for cid,*_ in trial.ITEMS:
            parent=None
            for name in ('BASE','P9LP','P9DB','P9MASK'):
                expected=trial.EXPECTED_BASE if name=='BASE' else proto['variants'][name]['sha256']
                matches=[r for r in earlier if r['case_id']==cid and r['variant']==name]
                if not matches:raise RuntimeError('Required completed protection missing '+cid+'/'+name)
                r=dict(matches[0]);case_dir=Path(r['directory'])/'case'
                if r['kernel_sha256']!=expected or r['runner_sha256']!=core.sha(trial.runner(name)):raise RuntimeError('Protection identity differs')
                if core.sha(case_dir/'output.bin')!=r['output_sha256']:raise RuntimeError('Captured output altered')
                if any(core.sha(core.origin(cid)/n)!=h for n,h in r['input_file_sha256'].items()):raise RuntimeError('Input identity altered')
                if name=='BASE':parent=r['output_sha256']
                if r['status'] not in VALID or r['output_sha256']!=parent:raise RuntimeError('Invalid structural protection')
                r['reused_protection']=True;checks.append(r);core.save(ROOT/'checks.json',checks)
        pairs=[];summary=[];versions=('BASE','P9LP','P9DB','P9MASK')
        for cid in ('s6','s7','s8'):
            for block in range(2):
                order=versions
                if block%2:order=tuple(reversed(order))
                for pos,name in enumerate(order):
                    r=trial.capture(cid,name,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in VALID:raise RuntimeError('Invalid timing')
            base=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='BASE']
            for name in versions[1:]:
                candidate=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']==name]
                summary.append(dict(case_id=cid,candidate=name,base_us=base,candidate_us=candidate,
                     gain_pct=100*(statistics.median(base)-statistics.median(candidate))/statistics.median(base)))
                core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        diagnostic=[]
        original=core.run_logged
        def conflicts(cmd,*args,**kwargs):
            for i,arg in enumerate(cmd):
                if arg.startswith('--aic-metrics='):cmd[i]=arg+',ResourceConflictRatio'
            return original(cmd,*args,**kwargs)
        core.run_logged=conflicts
        try:
            for cid in ('s6','s7','s8'):
                best=max([r for r in summary if r['case_id']==cid],key=lambda r:r['gain_pct'])['candidate']
                for name in ('BASE',best):
                    r=trial.capture(cid,name,ROOT/('op_'+cid+'_'+name),'op');diagnostic.append(r)
                    core.save(ROOT/'diagnostic.json',diagnostic)
                    if r['status'] not in VALID:raise RuntimeError('Invalid diagnostic capture')
        finally:core.run_logged=original
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',baseline_official_score=65.34,
                  historical_other_branch_score=65.36,target_score=72,goal_achieved=False,screening_only=True,protection_reused_not_repeated=True))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
