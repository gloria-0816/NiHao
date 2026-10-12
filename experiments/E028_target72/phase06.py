"""Full combination protection and paired timing before official evaluation."""
import fcntl,json,statistics,shutil
from pathlib import Path
from phase01 import trial,core,HERE,PREV
ROOT=HERE/'results/phase06'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def simulate_single64():
    f=ROOT/'simulation_s1';f.mkdir(mode=0o700)
    private=f/'cloud_addrmsnormbias';shutil.copy2(HERE/'build_sim_COMBO/cloud_addrmsnormbias',private);private.chmod(0o700)
    core.copied_case('s1',f/'case')
    cmd=['msprof','op','simulator','--soc-version=Ascend910B3','--core-id=0','--launch-count=1','--timeout=2',
         '--aic-metrics=PipeUtilization,ResourceConflictRatio','--output='+str(f/'profile'),str(private),
         '--case-dir',str(f/'case'),'--result',str(f/'benchmark.json'),'--warmup','0','--repeats','1','--batch','1','--timing','host','--timeout-ms','30000']
    r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',240)
    r.update(command=cmd,source_sha256=trial.EXPECTED_BASE,runner_sha256=core.sha(private),instruction_export_valid=any(p.name=='trace.json' for p in f.rglob('*')))
    core.save(f/'completion.json',r)
    if r['instruction_export_valid']:
        import analyze_instruction_trace
        core.save(ROOT/'instruction_s1.json',analyze_instruction_trace.analyze(f/'profile'))

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase05/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase06.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE or core.sha(trial.source('COMBO1'))!=proto['variants']['COMBO1']['sha256']:raise RuntimeError('Source changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        f=ROOT/'build';f.mkdir(mode=0o700)
        cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source('COMBO1')),
             'BUILD_DIR='+str(trial.runner('COMBO1').parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
        r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
        if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
        trial.ITEMS=[('s1',1,64,'float16'),('s2',7,197,'float32'),('s3',128,256,'float32'),('s4',767,193,'float16'),
                     ('s5',8,32768,'float16'),('s6',1513,577,'float16'),('s7',3113,397,'float16'),('s8',10240,512,'float16'),
                     ('s9',4096,1536,'float32'),('s10',8192,1024,'float16'),('s11',3749,3083,'float32'),
                     ('s12',3408,4096,'bfloat16'),('s13',10300,3079,'float32'),('s14_reduced',3841,128,'bfloat16'),('s15_reduced',161,8192,'bfloat16')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            b=trial.capture(cid,'COMBO',ROOT/('check_'+cid+'_COMBO'));c=trial.capture(cid,'COMBO1',ROOT/('check_'+cid+'_COMBO1'))
            c['bitwise_equal_COMBO']=c.get('output_sha256')==b.get('output_sha256');checks.extend((b,c));core.save(ROOT/'checks.json',checks)
            if b['status'] not in VALID or c['status'] not in VALID:raise RuntimeError('Invalid protection '+cid)
            if cid=='s2':
                if c['status']!='measured_strict_pass':raise RuntimeError('Changed FP32 strict failed')
            elif not c['bitwise_equal_COMBO']:raise RuntimeError('Unchanged arithmetic output changed '+cid)
        pairs=[];summary=[]
        for cid in ('s1','s2','s4','s11','s13'):
            for block in range(2):
                order=('COMBO','COMBO1','COMBO1','COMBO') if block==0 else ('COMBO1','COMBO','COMBO','COMBO1')
                for pos,name in enumerate(order):
                    r=trial.capture(cid,name,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in VALID:raise RuntimeError('Invalid timing')
            b=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='COMBO'];c=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='COMBO1']
            summary.append(dict(case_id=cid,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
            core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        simulate_single64()
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False,protection='15 representative paths; final two BF16 shapes reduced; changed FP32 strict passed, other arithmetic bitwise preserved'))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
