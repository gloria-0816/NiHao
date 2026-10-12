"""Compare independent output buffers and mask reuse; repeat parameter scheduling."""
import fcntl,json,statistics
from pathlib import Path
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase09'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase08/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase09.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise RuntimeError('Baseline changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        for name,m in proto['variants'].items():
            if core.sha(trial.source(name))!=m['sha256']:raise RuntimeError('Source changed')
            if name=='P9LP':
                prior=json.loads((HERE/'results/phase08/identity.json').read_text())
                if prior['protocol']['variants'][name]['sha256']!=m['sha256']:raise RuntimeError('Parent identity differs')
                r=json.loads((HERE/'results/phase08/pairs.json').read_text())
                candidates=[x for x in r if x['variant']==name]
                if not candidates or core.sha(trial.runner(name))!=candidates[0]['runner_sha256']:raise RuntimeError('Reused runner identity differs')
                core.save(ROOT/'reused_build_P9LP.json',dict(source_sha256=m['sha256'],runner_sha256=core.sha(trial.runner(name)),original_phase='phase08'))
                continue
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s6',1513,577,'float16'),('s7',3113,397,'float16'),('s8',10240,512,'float16'),
                     ('dbd320',161,320,'float16'),('dbd321',161,321,'float16'),
                     ('dbd384',1121,384,'float16'),('dbd448',1761,448,'float16'),
                     ('dbd512',761,512,'float16'),('dbd640',1601,640,'float16'),
                     ('dbd641',1601,641,'float16'),('dbd1024',1601,1024,'float16'),
                     ('dbd1025',161,1025,'float16'),('dbr159',159,577,'float16'),
                     ('dbr160',160,577,'float16'),('dbr560',560,577,'float16'),
                     ('dbr561',561,577,'float16'),('dbr1120',1120,577,'float16'),
                     ('dbr1121',1121,577,'float16'),('dbr1680',1680,577,'float16'),
                     ('dbr1681',1681,577,'float16')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            parent=None
            for name in ('COMBO','P9LP','P9DB','P9MASK'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                if name=='COMBO':parent=r.get('output_sha256')
                r['bitwise_equal_COMBO']=r.get('output_sha256')==parent
                checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status'] not in VALID:raise RuntimeError('Invalid capture '+cid+'/'+name)
                if not r['bitwise_equal_COMBO']:raise RuntimeError('Structural edit changed output '+cid+'/'+name)
        pairs=[];summary=[];versions=('COMBO','P9LP','P9DB','P9MASK')
        for cid in ('s6','s7','s8'):
            for block in range(6):
                k=block%4;order=versions[k:]+versions[:k]
                if block%2:order=tuple(reversed(order))
                for pos,name in enumerate(order):
                    r=trial.capture(cid,name,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in VALID:raise RuntimeError('Invalid timing')
            base=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='COMBO']
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
                for name in versions:
                    r=trial.capture(cid,name,ROOT/('op_'+cid+'_'+name),'op');diagnostic.append(r)
                    core.save(ROOT/'diagnostic.json',diagnostic)
                    if r['status'] not in VALID:raise RuntimeError('Invalid diagnostic capture')
        finally:core.run_logged=original
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',best_historical_official_score=65.36,
                  newest_official_score=64.52,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
