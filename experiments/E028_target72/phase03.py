"""Large FP32 DMA batch and balanced lane accumulation; separate simulator build."""
from pathlib import Path
import fcntl,json,statistics,shutil
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase03'

def simulate_baseline():
    folder=ROOT/'simulation';folder.mkdir(mode=0o700)
    build=HERE/'build_sim_COMBO'
    cmds=[['cmake','-S',str(trial.OLD/'cloud_bench'),'-B',str(build),'-DNPU_ARCH=dav-2201',
           '-DCMAKE_ASC_RUN_MODE=sim','-DCMAKE_ASC_ARCHITECTURES=dav-2201','-DCMAKE_ASC_FLAGS=-O2 -g',
           '-DKERNEL_SOURCE='+str(trial.BASE_SOURCE)],['cmake','--build',str(build),'--parallel','4']]
    records=[]
    for i,cmd in enumerate(cmds):
        r=core.run_logged(cmd,folder/(str(i)+'_stdout.log'),folder/(str(i)+'_stderr.log'),600)
        r['command']=cmd;records.append(r);core.save(folder/'build_records.json',records)
        if r['returncode']!=0 or r['timed_out']:
            core.save(folder/'completion.json',dict(status='build_failed',instruction_export_valid=False));return
    private=folder/'cloud_addrmsnormbias';shutil.copy2(build/'cloud_addrmsnormbias',private);private.chmod(0o700)
    core.copied_case('s2',folder/'case')
    cmd=['msprof','op','simulator','--soc-version=Ascend910B3','--core-id=0','--launch-count=1','--timeout=2',
         '--aic-metrics=PipeUtilization,ResourceConflictRatio','--output='+str(folder/'profile'),
         str(private),'--case-dir',str(folder/'case'),'--result',str(folder/'benchmark.json'),
         '--warmup','0','--repeats','1','--batch','1','--timing','host','--timeout-ms','30000']
    r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',240)
    r.update(command=cmd,runner_sha256=core.sha(private),source_sha256=core.sha(trial.BASE_SOURCE))
    files=[p for p in folder.rglob('*') if p.is_file()]
    r['instruction_export_valid']=any(p.name.endswith('_instr_exe.csv') or p.name=='trace.json' for p in files)
    r['files']=[str(p.relative_to(folder)) for p in files]
    core.save(folder/'completion.json',r);print(json.dumps({'separate_sim_build':True,'instruction_export_valid':r['instruction_export_valid']}),flush=True)

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase02b/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/'protocol_phase03.json').read_text());core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        for name in ('RR4','RR4TREE'):
            if core.sha(trial.source(name))!=proto['variants'][name]['sha256']:raise ValueError('Candidate source changed')
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s13',10300,3079,'float32'),('rr_low',5463,3072,'float32'),('rr_in',5465,3073,'float32'),
                     ('rr_upper',5141,3264,'float32'),('rr_out',5141,3265,'float32'),('rr_small',161,3083,'float32')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            b=None
            for name in ('COMBO','RR4','RR4TREE'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                if name=='COMBO':b=r.get('output_sha256')
                r['bitwise_equal_COMBO']=r.get('output_sha256')==b
                checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status']!='measured_strict_pass':raise RuntimeError('FP32 strict failed '+cid+'/'+name)
                if name=='RR4' and not r['bitwise_equal_COMBO']:raise RuntimeError('Layout changed arithmetic')
        pairs=[];summary=[]
        for c in ('RR4','RR4TREE'):
            for block in range(2):
                order=('COMBO',c,c,'COMBO') if block==0 else (c,'COMBO','COMBO',c)
                for pos,name in enumerate(order):
                    r=trial.capture('s13',name,ROOT/('pair_'+c+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(candidate_group=c,block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status']!='measured_strict_pass':raise RuntimeError('Invalid timing')
            b=[r['median_us'] for r in pairs if r['candidate_group']==c and r['variant']=='COMBO'];a=[r['median_us'] for r in pairs if r['candidate_group']==c and r['variant']==c]
            summary.append(dict(candidate=c,case_id='s13',base_us=b,candidate_us=a,gain_pct=100*(statistics.median(b)-statistics.median(a))/statistics.median(b)))
            core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        diagnostics=[]
        for name in ('COMBO','RR4','RR4TREE'):
            r=trial.capture('s13',name,ROOT/('op_'+name),'op');diagnostics.append(r);core.save(ROOT/'diagnostic.json',diagnostics)
        core.save(ROOT/'metrics.json',metric_summary(diagnostics))
        simulate_baseline()
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
