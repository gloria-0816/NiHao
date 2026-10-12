"""Block/whole reduction and FP16 cyclic DMA; repaired instruction simulation export."""
import json,fcntl,statistics,shutil
from pathlib import Path
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase02b'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def repaired_simulator(name):
    folder=ROOT/('simulator_'+name);folder.mkdir(mode=0o700)
    meta,_=core.copied_case('s2',folder/'case')
    private=folder/'cloud_addrmsnormbias';shutil.copy2(trial.runner(name),private);private.chmod(0o700)
    cmd=['msprof','op','simulator','--soc-version=Ascend910B3','--core-id=0','--launch-count=1','--timeout=2',
         '--aic-metrics=PipeUtilization,ResourceConflictRatio','--output='+str(folder/'profile'),
         str(private),'--case-dir',str(folder/'case'),'--result',str(folder/'benchmark.json'),
         '--warmup','0','--repeats','1','--batch','1','--timing','host','--timeout-ms','30000']
    r=dict(variant=name,command=cmd,source_sha256=core.sha(trial.source(name)),runner_sha256=core.sha(private),kind='simulation; never board timing')
    r.update(core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',240))
    files=[p for p in folder.rglob('*') if p.is_file()]
    r['export_files']=[str(p.relative_to(folder)) for p in files]
    r['instruction_export_valid']=any(p.name.endswith('_instr_exe.csv') or p.name=='trace.json' for p in files)
    core.save(folder/'record.json',r)
    print(json.dumps({'simulator':name,'returncode':r['returncode'],'instruction_export_valid':r['instruction_export_valid']}),flush=True)
    return r

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase01/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior experiment unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    (HERE/'results').chmod(0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/'protocol_phase02b.json').read_text())
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        old=json.loads((HERE/'results/phase01/diagnostic.json').read_text())
        core.save(ROOT/'phase01_metrics_reparsed.json',metric_summary(old))
        # Earlier simulator app failed aclrtSetDevice; do not mark it valid or repeat without sim build.
        for name in ('S256B','HRR2'):
            if name=='S256B':
                prior=json.loads((HERE/'results/phase02/build_S256B/record.json').read_text())
                if prior['returncode']!=0 or prior['timed_out']:raise RuntimeError('Reused build invalid')
                core.save(ROOT/'reused_build_S256B.json',dict(prior=prior,source_sha256=core.sha(trial.source(name)),runner_sha256=core.sha(trial.runner(name))))
                continue
            if core.sha(trial.source(name))!=proto['variants'][name]['sha256']:raise ValueError('Source changed')
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        groups={'S256B':[('s2',7,197,'float32'),('short193',3,193,'float32'),('short255',17,255,'float32'),('short256',40,256,'float32'),
                         ('short192',7,192,'float32'),('short257',7,257,'float32'),('short41',41,197,'float32')],
                'HRR2':[('s4',767,193,'float16'),('h64',161,64,'float16'),('h128',767,128,'float16'),('h256',1280,256,'float16'),
                       ('h160',160,193,'float16'),('h1280',1280,193,'float16'),('h1281',1281,193,'float16')]}
        checks=[]
        for name,items in groups.items():
            trial.ITEMS=items;trial.stage_inputs()
            for cid,*_ in items:
                b=trial.capture(cid,'COMBO',ROOT/('check_'+cid+'_COMBO'))
                c=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                c['bitwise_equal_COMBO']=c.get('output_sha256')==b.get('output_sha256')
                checks.extend((b,c));core.save(ROOT/'checks.json',checks)
                if b['status'] not in VALID or c['status'] not in VALID:raise RuntimeError('Invalid check '+cid)
                if name=='S256B' and c['status']!='measured_strict_pass':raise RuntimeError('FP32 strict failed')
                if name=='HRR2' and not c['bitwise_equal_COMBO']:raise RuntimeError('DMA reorder changed values')
        pairs=[];summary=[]
        for name,cid in [('S256B','s2'),('HRR2','s4')]:
            for block in range(2):
                order=('COMBO',name,name,'COMBO') if block==0 else (name,'COMBO','COMBO',name)
                for pos,v in enumerate(order):
                    r=trial.capture(cid,v,ROOT/('pair_'+name+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(candidate_group=name,block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in VALID:raise RuntimeError('Invalid timing')
            b=[r['median_us'] for r in pairs if r['candidate_group']==name and r['variant']=='COMBO']
            c=[r['median_us'] for r in pairs if r['candidate_group']==name and r['variant']==name]
            summary.append(dict(candidate=name,case_id=cid,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
            core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        diagnostic=[]
        for cid,name in [('s2','S256B'),('s4','HRR2')]:
            for v in ('COMBO',name):
                r=trial.capture(cid,v,ROOT/('op_'+cid+'_'+v),'op');diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
