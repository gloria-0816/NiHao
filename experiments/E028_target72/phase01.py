"""Compare constant short-row geometry and a reduction fold against official COMBO."""
from pathlib import Path
import importlib.util,fcntl,json,statistics,csv,time

HERE=Path(__file__).resolve().parent
PREV=Path('/home/developer/addrms_E027/experiments/E027_target70')
spec=importlib.util.spec_from_file_location('previous_trial',PREV/'resume_probe.py')
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
core=trial.core
trial.HERE=HERE
trial.BASE_SOURCE=PREV/'COMBO/kernel.asc'
trial.BASE_RUNNER=PREV/'build_COMBO/cloud_addrmsnormbias'
trial.EXPECTED_BASE='aef9a81a4c3bc78693db38ea0eea66c4b6cbbc232f7f342aba1408e8b4233c3c'
trial.source=lambda name: trial.BASE_SOURCE if name=='COMBO' else HERE/name/'kernel.asc'
trial.runner=lambda name: trial.BASE_RUNNER if name=='COMBO' else HERE/('build_'+name)/'cloud_addrmsnormbias'
core.version=lambda name:(trial.runner(name),core.sha(trial.source(name)))
ROOT=HERE/'results/phase01'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def metric_summary(records):
    out=[]
    for r in records:
        rows=[]
        for p in (Path(r['directory'])/'profile').rglob('*.csv'):
            if p.name.startswith('PipeUtilization'):
                with p.open(encoding='utf-8-sig') as f: rows.extend(csv.DictReader(f))
        fields=('aiv_time(us)','aiv_vec_time(us)','aiv_scalar_time(us)','aiv_mte2_time(us)','aiv_mte3_time(us)','aiv_vec_ratio','aiv_scalar_ratio','aiv_mte2_ratio','aiv_mte3_ratio')
        metrics={}
        for k in fields:
            values=[]
            for row in rows:
                try:values.append(float(row[k]))
                except (ValueError,KeyError,TypeError):pass
            metrics[k]=statistics.median(values) if values else None
        out.append(dict(variant=r['variant'],case_id=r['case_id'],n_core_records=len(rows),metrics=metrics))
    return out

def simulator(name):
    folder=ROOT/('simulator_'+name);folder.mkdir(mode=0o700)
    meta,_=core.copied_case('s2',folder/'case')
    cmd=['msprof','op','simulator','--soc-version=Ascend910B3','--core-id=0','--launch-count=1','--timeout=2',
         '--aic-metrics=PipeUtilization,ResourceConflictRatio','--output='+str(folder/'profile'),
         str(trial.runner(name)),'--case-dir',str(folder/'case'),'--result',str(folder/'benchmark.json'),
         '--warmup','0','--repeats','1','--batch','1','--timing','host','--timeout-ms','30000']
    r=dict(variant=name,command=cmd,source_sha256=core.sha(trial.source(name)),kind='simulation only; not on-board timing')
    r.update(core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',240))
    r['export_files']=[str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()]
    r['instruction_export_valid']=any(p.name.endswith('_instr_exe.csv') or p.name=='trace.json' for p in folder.rglob('*'))
    core.save(folder/'record.json',r);print(json.dumps({'simulator':name,'returncode':r['returncode'],'timed_out':r['timed_out'],'n_files':len(r['export_files'])}),flush=True)
    return r

def main():
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Official baseline changed')
        proto=json.loads((HERE/'protocol.json').read_text())
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__),baseline_runner_sha256=core.sha(trial.BASE_RUNNER)))
        for name in ('S256','S256F'):
            if core.sha(trial.source(name))!=proto['variants'][name]['sha256']:raise ValueError('Candidate changed')
            folder=ROOT/('build_'+name);folder.mkdir()
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600)
            core.save(folder/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s2',7,197,'float32'),('short193',3,193,'float32'),('short255',17,255,'float32'),
                     ('short256',40,256,'float32'),('short192',7,192,'float32'),('short257',7,257,'float32'),
                     ('short41',41,197,'float32'),('short1',1,197,'float32'),('short2',2,197,'float32')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            base=None
            for name in ('COMBO','S256','S256F'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                if name=='COMBO':base=r.get('output_sha256')
                r['bitwise_equal_COMBO']=r.get('output_sha256')==base
                checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status']!='measured_strict_pass':raise RuntimeError('Strict failure '+cid+'/'+name)
                if name=='S256' and not r['bitwise_equal_COMBO']:raise RuntimeError('Arithmetic preserving candidate changed output')
        pairs=[]
        for candidate in ('S256','S256F'):
            for block in range(2):
                order=('COMBO',candidate,candidate,'COMBO') if block==0 else (candidate,'COMBO','COMBO',candidate)
                for pos,name in enumerate(order):
                    r=trial.capture('s2',name,ROOT/('pair_'+candidate+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(candidate_group=candidate,block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status']!='measured_strict_pass':raise RuntimeError('Invalid performance')
        summary=[]
        for c in ('S256','S256F'):
            b=[r['median_us'] for r in pairs if r['candidate_group']==c and r['variant']=='COMBO']
            a=[r['median_us'] for r in pairs if r['candidate_group']==c and r['variant']==c]
            summary.append(dict(candidate=c,case_id='s2',base_us=b,candidate_us=a,gain_pct=100*(statistics.median(b)-statistics.median(a))/statistics.median(b)))
        core.save(ROOT/'summary.json',summary);print(json.dumps(summary),flush=True)
        diagnostics=[]
        for name in ('COMBO','S256','S256F'):
            r=trial.capture('s2',name,ROOT/('op_'+name),'op');diagnostics.append(r);core.save(ROOT/'diagnostic.json',diagnostics)
        core.save(ROOT/'metrics.json',metric_summary(diagnostics))
        sims=[simulator('COMBO'),simulator('S256F')];core.save(ROOT/'simulator.json',sims)
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
