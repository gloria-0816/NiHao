"""Baseline engine and instruction evidence for FP16 transfer/pipeline work."""
import fcntl,json,shutil
from pathlib import Path
from phase01 import trial,core,HERE,PREV,metric_summary
import analyze_instruction_trace
ROOT=HERE/'results/phase07'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def simulate(cid):
    f=ROOT/('simulation_'+cid);f.mkdir(mode=0o700)
    private=f/'cloud_addrmsnormbias'
    shutil.copy2(HERE/'build_sim_COMBO/cloud_addrmsnormbias',private);private.chmod(0o700)
    core.copied_case(cid,f/'case')
    cmd=['msprof','op','simulator','--soc-version=Ascend910B3','--core-id=0','--launch-count=1','--timeout=2',
         '--aic-metrics=PipeUtilization,ResourceConflictRatio','--output='+str(f/'profile'),str(private),
         '--case-dir',str(f/'case'),'--result',str(f/'benchmark.json'),'--warmup','0','--repeats','1',
         '--batch','1','--timing','host','--timeout-ms','30000']
    r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',240)
    r.update(command=cmd,source_sha256=trial.EXPECTED_BASE,runner_sha256=core.sha(private),
             instruction_export_valid=any(p.name=='trace.json' for p in f.rglob('*')))
    core.save(f/'completion.json',r)
    if r['instruction_export_valid']:
        core.save(ROOT/('instruction_'+cid+'.json'),analyze_instruction_trace.analyze(f/'profile'))
    print(json.dumps(dict(case_id=cid,simulation_valid=r['instruction_export_valid'],returncode=r['returncode'])),flush=True)

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase06/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise RuntimeError('Baseline changed')
        core.save(ROOT/'identity.json',dict(protocol=json.loads((HERE/'protocol_phase07.json').read_text()),
                   driver_sha256=core.sha(__file__),board_runner_sha256=core.sha(trial.BASE_RUNNER)))
        trial.ITEMS=[('s4',767,193,'float16'),('s6',1513,577,'float16'),('s7',3113,397,'float16')]
        trial.stage_inputs();diagnostic=[]
        for cid,*_ in trial.ITEMS:
            r=trial.capture(cid,'COMBO',ROOT/('op_'+cid),'op');diagnostic.append(r)
            core.save(ROOT/'diagnostic.json',diagnostic)
            if r['status'] not in VALID:raise RuntimeError('Invalid baseline capture '+cid)
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        for cid,*_ in trial.ITEMS:simulate(cid)
        core.save(ROOT/'completion.json',dict(status='completed',best_historical_score=65.36,
                  newest_official_score=64.52,target_score=72,goal_achieved=False,no_candidate_tested=True))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
