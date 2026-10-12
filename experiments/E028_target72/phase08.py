"""Isolate FP16 parameter startup and two output slot ownership."""
import fcntl,json,statistics
from pathlib import Path
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase08'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase07/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase unfinished')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase08.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise RuntimeError('Baseline changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        for name,m in proto['variants'].items():
            if core.sha(trial.source(name))!=m['sha256']:raise RuntimeError('Source changed')
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s6',1513,577,'float16'),('s7',3113,397,'float16'),
                     ('p9d320',161,320,'float16'),('p9d321',161,321,'float16'),
                     ('p9d512',761,512,'float16'),('p9d513',1241,513,'float16'),
                     ('p9d1024',1601,1024,'float16'),('p9d1025',161,1025,'float16'),
                     ('p9r159',159,577,'float16'),('p9r160',160,577,'float16'),
                     ('p9r599',599,577,'float16'),('p9r600',600,577,'float16')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            parent=None
            for name in ('COMBO','P9LP','P9OUT'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                if name=='COMBO':parent=r.get('output_sha256')
                r['bitwise_equal_COMBO']=r.get('output_sha256')==parent
                checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status'] not in VALID:raise RuntimeError('Invalid capture '+cid+'/'+name)
                if not r['bitwise_equal_COMBO']:raise RuntimeError('Structural edit changed output '+cid+'/'+name)
        pairs=[];summary=[]
        for cid in ('s6','s7'):
            for candidate in ('P9LP','P9OUT'):
                for block in range(2):
                    order=('COMBO',candidate,candidate,'COMBO') if block==0 else (candidate,'COMBO','COMBO',candidate)
                    for pos,name in enumerate(order):
                        r=trial.capture(cid,name,ROOT/('pair_'+cid+'_'+candidate+'_'+str(block)+'_'+str(pos)),'ordinary')
                        r.update(block=block,position=pos,pair=candidate);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                        if r['status'] not in VALID:raise RuntimeError('Invalid timing')
                b=[r['median_us'] for r in pairs if r['case_id']==cid and r['pair']==candidate and r['variant']=='COMBO']
                c=[r['median_us'] for r in pairs if r['case_id']==cid and r['pair']==candidate and r['variant']==candidate]
                summary.append(dict(case_id=cid,candidate=candidate,base_us=b,candidate_us=c,
                     gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
                core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        diagnostic=[]
        for cid in ('s6','s7'):
            for name in ('COMBO','P9LP','P9OUT'):
                r=trial.capture(cid,name,ROOT/('op_'+cid+'_'+name),'op');diagnostic.append(r)
                core.save(ROOT/'diagnostic.json',diagnostic)
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',best_historical_official_score=65.36,
                  newest_official_score=64.52,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
