"""Validate the selected complete kernel against all fifteen local representative paths."""
import fcntl,json,statistics
import resume_probe as trial
core=trial.core;HERE=trial.HERE;ROOT=HERE/'results'/'attempt06'
def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/attempt05/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior trial incomplete')
    ROOT.mkdir(parents=True,exist_ok=False)
    with (HERE/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/'COMBO/protocol.json').read_text())
        if core.sha(trial.source('COMBO'))!=proto['sha256']:raise ValueError('Candidate changed')
        folder=ROOT/'build';folder.mkdir()
        cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source('COMBO')),
             'BUILD_DIR='+str(trial.runner('COMBO').parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
        r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600);r['source_sha256']=proto['sha256'];core.save(folder/'record.json',r)
        if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
        trial.ITEMS=[('s1',1,64,'float16'),('s2',7,197,'float32'),('s3',128,256,'float32'),
          ('s4',767,193,'float16'),('s5',8,32768,'float16'),('s6',1513,577,'float16'),
          ('s7',3113,397,'float16'),('s8',10240,512,'float16'),('s9',4096,1536,'float32'),
          ('s10',8192,1024,'float16'),('s11',3749,3083,'float32'),('s12',3408,4096,'bfloat16'),
          ('s13',10300,3079,'float32'),('s14_reduced',3841,128,'bfloat16'),('s15_reduced',161,8192,'bfloat16')]
        trial.stage_inputs();checks=[];valid=('measured_strict_pass','measured_strict_fail_retained')
        for cid,*_ in trial.ITEMS:
            b=trial.capture(cid,'FACC',ROOT/('check_'+cid+'_FACC'));c=trial.capture(cid,'COMBO',ROOT/('check_'+cid+'_COMBO'))
            c['bitwise_equal_FACC']=c.get('output_sha256')==b.get('output_sha256');checks.extend((b,c));core.save(ROOT/'checks.json',checks)
            if b['status'] not in valid or c['status'] not in valid or not c['bitwise_equal_FACC']:raise RuntimeError('Protection output changed '+cid)
        pairs=[]
        for block in range(2):
            for cid in ('s4','s11','s13'):
                order=('FACC','COMBO','COMBO','FACC') if block==0 else ('COMBO','FACC','FACC','COMBO')
                for pos,v in enumerate(order):
                    r=trial.capture(cid,v,ROOT/('pair_'+cid+'_'+str(block)+'_'+str(pos)),'ordinary');pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in valid:raise RuntimeError('Invalid measurement')
        summary=[]
        for cid in ('s4','s11','s13'):
            b=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='FACC'];c=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='COMBO']
            summary.append(dict(case_id=cid,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
        core.save(ROOT/'summary.json',summary);core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False,protection='15 local representative paths; BF16 final two reduced shapes'))
if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
