"""Small shapes: isolate one horizontal reduction with input aliasing and readiness waits."""
import fcntl,json,statistics
import resume_probe as trial
core=trial.core;HERE=trial.HERE;ROOT=HERE/'results'/'attempt09'
def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/attempt08/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior trial incomplete')
    ROOT.mkdir(parents=True,exist_ok=False)
    with (HERE/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/'SMOVE/protocol.json').read_text())
        if core.sha(trial.source('SMOVE'))!=proto['sha256']:raise ValueError('Candidate changed')
        folder=ROOT/'build';folder.mkdir()
        cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source('SMOVE')),
             'BUILD_DIR='+str(trial.runner('SMOVE').parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
        r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600);core.save(folder/'record.json',r)
        if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
        trial.ITEMS=[('s2',7,197,'float32'),('fold_65',3,65,'float32'),('fold_128',3,128,'float32'),
          ('fold_129',3,129,'float32'),('fold_256',3,256,'float32'),('fold_257',3,257,'float32'),
          ('fold_79',79,193,'float32')]
        trial.stage_inputs();checks=[];baseline_hash={}
        for cid,*_ in trial.ITEMS:
            for v in ('FACC','SMOVE'):
                r=trial.capture(cid,v,ROOT/('check_'+cid+'_'+v));checks.append(r);core.save(ROOT/'checks.json',checks)
                if r['status']!='measured_strict_pass':raise RuntimeError('Strict check failed '+cid+'/'+v)
                if v=='FACC':baseline_hash[cid]=r['output_sha256']
                elif r['output_sha256']!=baseline_hash[cid]:raise RuntimeError('Bitwise mismatch '+cid)
        pairs=[]
        for block in range(2):
            order=('FACC','SMOVE','SMOVE','FACC') if block==0 else ('SMOVE','FACC','FACC','SMOVE')
            for pos,v in enumerate(order):
                r=trial.capture('s2',v,ROOT/('pair_'+str(block)+'_'+str(pos)),'ordinary');pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                if r['status']!='measured_strict_pass':raise RuntimeError('Invalid measurement')
        b=[r['median_us'] for r in pairs if r['variant']=='FACC'];c=[r['median_us'] for r in pairs if r['variant']=='SMOVE']
        core.save(ROOT/'summary.json',dict(case_id='s2',base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
        diagnostics=[]
        for v in ('FACC','SMOVE'):
            r=trial.capture('s2',v,ROOT/('diagnostic_'+v),'op');diagnostics.append(r);core.save(ROOT/'diagnostic.json',diagnostics)
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False))
if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
