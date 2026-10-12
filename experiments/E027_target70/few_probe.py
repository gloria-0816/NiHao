"""Few short FP32 rows: compare batching on one and two cores."""
import fcntl,json,statistics
import resume_probe as trial
core=trial.core;HERE=trial.HERE;ROOT=HERE/'results'/'attempt05'
def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/attempt04/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior trial incomplete')
    ROOT.mkdir(parents=True,exist_ok=False)
    with (HERE/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        for name in ('FG1','FG2'):
            proto=json.loads((HERE/name/'protocol.json').read_text())
            if core.sha(trial.source(name))!=proto['sha256']:raise ValueError('Source changed')
            folder=ROOT/('build_'+name);folder.mkdir()
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600);core.save(folder/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
        trial.ITEMS=[('s2',7,197,'float32'),('fg_min',2,64,'float32'),('fg_max',8,256,'float32'),
                     ('fg_rout',9,256,'float32'),('fg_dout',7,257,'float32')]
        trial.stage_inputs();checks=[]
        for cid,*_ in trial.ITEMS:
            for name in ('FACC','FG1','FG2'):
                r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name));checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status']!='measured_strict_pass':raise RuntimeError('Strict output failed '+cid+'/'+name)
        pairs=[]
        for name in ('FG1','FG2'):
            for block in range(2):
                order=('FACC',name,name,'FACC') if block==0 else (name,'FACC','FACC',name)
                for pos,v in enumerate(order):
                    r=trial.capture('s2',v,ROOT/('pair_'+name+'_'+str(block)+'_'+str(pos)),'ordinary');r['candidate_group']=name
                    pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status']!='measured_strict_pass':raise RuntimeError('Invalid measurement')
        summary=[]
        for name in ('FG1','FG2'):
            rs=[r for r in pairs if r['candidate_group']==name];b=[r['median_us'] for r in rs if r['variant']=='FACC'];c=[r['median_us'] for r in rs if r['variant']==name]
            summary.append(dict(candidate=name,case_id='s2',base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
        core.save(ROOT/'summary.json',summary);core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False))
if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
