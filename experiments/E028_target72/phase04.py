"""Trace-directed short-row DMA readiness and UB layout; repeat the positive reduction candidate."""
from pathlib import Path
import fcntl,json,statistics
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase04'

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase03/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase incomplete')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase04.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        for name,m in proto['variants'].items():
            if core.sha(trial.source(name))!=m['sha256']:raise ValueError('Candidate changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        for name in ('S256BP','S256BUB'):
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s2',7,197,'float32'),('short193',3,193,'float32'),('short255',17,255,'float32'),('short256',40,256,'float32'),
                     ('short192',7,192,'float32'),('short257',7,257,'float32'),('short41',41,197,'float32')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            baseline=None;parent=None
            for name in ('COMBO','S256B','S256BP','S256BUB'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                if name=='COMBO':baseline=r.get('output_sha256')
                if name=='S256B':parent=r.get('output_sha256')
                r['bitwise_equal_COMBO']=r.get('output_sha256')==baseline
                r['bitwise_equal_S256B']=None if parent is None else r.get('output_sha256')==parent
                checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status']!='measured_strict_pass':raise RuntimeError('Strict failed '+cid+'/'+name)
                if name in ('S256BP','S256BUB') and not r['bitwise_equal_S256B']:raise RuntimeError('Structural edit changed values')
        pairs=[];versions=('COMBO','S256B','S256BP','S256BUB')
        for block in range(5):
            k=block%4;order=versions[k:]+versions[:k]
            if block%2:order=tuple(reversed(order))
            for pos,name in enumerate(order):
                r=trial.capture('s2',name,ROOT/('pair_'+str(block)+'_'+str(pos)),'ordinary')
                r.update(block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                if r['status']!='measured_strict_pass':raise RuntimeError('Invalid timing')
        summary=[]
        b=[r['median_us'] for r in pairs if r['variant']=='COMBO']
        parent=[r['median_us'] for r in pairs if r['variant']=='S256B']
        for name in versions[1:]:
            c=[r['median_us'] for r in pairs if r['variant']==name]
            summary.append(dict(candidate=name,case_id='s2',base_us=b,candidate_us=c,parent_S256B_us=parent,gain_vs_COMBO_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b),gain_vs_S256B_pct=100*(statistics.median(parent)-statistics.median(c))/statistics.median(parent)))
        core.save(ROOT/'summary.json',summary);print(json.dumps(summary),flush=True)
        diagnostic=[]
        original=core.run_logged
        def conflicts(cmd,*args,**kwargs):
            for i,arg in enumerate(cmd):
                if arg.startswith('--aic-metrics='):cmd[i]=arg+',ResourceConflictRatio'
            return original(cmd,*args,**kwargs)
        core.run_logged=conflicts
        try:
            for name in ('COMBO','S256B','S256BP','S256BUB'):
                r=trial.capture('s2',name,ROOT/('op_'+name),'op');diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
        finally:core.run_logged=original
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
