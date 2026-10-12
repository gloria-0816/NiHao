"""E027 FP32 cyclic rows: full output coverage, guards, then serial ABBA measurements."""
import fcntl,json,statistics,time
from pathlib import Path
import resume_probe as trial
core=trial.core
HERE=trial.HERE
ROOT=HERE/'results'/'attempt03'
NAME='FPRR'

def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    ROOT.mkdir(parents=True,exist_ok=False)
    with (HERE/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/NAME/'protocol.json').read_text())
        if core.sha(trial.source(NAME))!=proto['sha256']:raise ValueError('Candidate changed')
        folder=ROOT/'build';folder.mkdir()
        cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0',
             'KERNEL_SOURCE='+str(trial.source(NAME)),'BUILD_DIR='+str(trial.runner(NAME).parent),
             'bash',str(trial.OLD/'cloud_bench/build.sh')]
        rec=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600)
        rec.update(source_sha256=proto['sha256'])
        core.save(folder/'record.json',rec)
        if rec['returncode']!=0 or rec['timed_out']:raise RuntimeError('Build failed')
        cut=(64*1024*1024+3079*4-1)//(3079*4)
        trial.ITEMS=[('s11',3749,3083,'float32'),('s13',10300,3079,'float32'),
          ('rr_below',cut-1,3079,'float32'),('rr_above',cut,3079,'float32'),
          ('rr_aligned',8193,2048,'float32'),('rr_dmin',11000,1537,'float32'),
          ('rr_dmax',4097,4096,'float32'),('rr_dout',4097,4097,'float32')]
        trial.stage_inputs()
        checks=[]
        for cid,*_ in trial.ITEMS:
            b=trial.capture(cid,'FACC',ROOT/('check_'+cid+'_FACC'))
            c=trial.capture(cid,NAME,ROOT/('check_'+cid+'_'+NAME))
            c['bitwise_equal_FACC']=c.get('output_sha256')==b.get('output_sha256')
            checks.extend((b,c));core.save(ROOT/'checks.json',checks)
            if b['status']!='measured_strict_pass' or c['status']!='measured_strict_pass' or not c['bitwise_equal_FACC']:
                raise RuntimeError('Coverage check failed '+cid)
        pairs=[]
        for block in range(2):
            for cid in ('s11','s13'):
                order=('FACC',NAME,NAME,'FACC') if block==0 else (NAME,'FACC','FACC',NAME)
                for pos,v in enumerate(order):
                    r=trial.capture(cid,v,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)),'ordinary')
                    pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status']!='measured_strict_pass':raise RuntimeError('Invalid pair')
        summary=[]
        for cid in ('s11','s13'):
            b=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='FACC']
            c=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']==NAME]
            summary.append(dict(case_id=cid,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
        core.save(ROOT/'summary.json',summary)
        diagnostics=[]
        for v in ('FACC',NAME):
            r=trial.capture('s13',v,ROOT/('diagnostic_s13_'+v),'op')
            diagnostics.append(r);core.save(ROOT/'diagnostic.json',diagnostics)
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True)
        core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False))
        raise
