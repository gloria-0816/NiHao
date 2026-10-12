"""E027 short-row parameter overlap and a contemporaneous FP32 selection."""
import fcntl,json,statistics
import resume_probe as trial
core=trial.core;HERE=trial.HERE;ROOT=HERE/'results'/'attempt04'

def main():
    if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    prev=json.loads((HERE/'results/attempt03/completion.json').read_text())
    if prev['status']!='completed':raise RuntimeError('Prior trial incomplete')
    ROOT.mkdir(parents=True,exist_ok=False)
    with (HERE/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        proto=json.loads((HERE/'HSP/protocol.json').read_text())
        if core.sha(trial.source('HSP'))!=proto['sha256']:raise ValueError('Candidate changed')
        folder=ROOT/'build';folder.mkdir()
        cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source('HSP')),
             'BUILD_DIR='+str(trial.runner('HSP').parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
        r=core.run_logged(cmd,folder/'stdout.log',folder/'stderr.log',600);core.save(folder/'record.json',r)
        if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
        trial.ITEMS=[('s4',767,193,'float16'),('hs_low',160,64,'float16'),('hs_max',1280,256,'float16'),
                     ('hs_out',1281,256,'float16'),('hs_dout',767,257,'float16'),('s11',3749,3083,'float32')]
        trial.stage_inputs()
        checks=[]
        valid=('measured_strict_pass','measured_strict_fail_retained')
        for cid,*_ in trial.ITEMS:
            if cid=='s11':continue
            b=trial.capture(cid,'FACC',ROOT/('check_'+cid+'_FACC'));c=trial.capture(cid,'HSP',ROOT/('check_'+cid+'_HSP'))
            c['bitwise_equal_FACC']=c.get('output_sha256')==b.get('output_sha256')
            checks.extend((b,c));core.save(ROOT/'checks.json',checks)
            if b['status'] not in valid or c['status'] not in valid or not c['bitwise_equal_FACC']:raise RuntimeError('Output changed '+cid)
        records=[]
        for cid,variants in [('s4',('HSP',)),('s11',('FPB4','FPB4RPL'))]:
            for name in variants:
                for block in range(2):
                    order=('FACC',name,name,'FACC') if block==0 else (name,'FACC','FACC',name)
                    for pos,v in enumerate(order):
                        r=trial.capture(cid,v,ROOT/('pair_'+cid+'_'+name+'_'+str(block)+'_'+str(pos)),'ordinary')
                        r['candidate_group']=name;records.append(r);core.save(ROOT/'pairs.json',records)
                        if r['status'] not in valid:raise RuntimeError('Invalid measurement')
        summary=[]
        for cid,name in [('s4','HSP'),('s11','FPB4'),('s11','FPB4RPL')]:
            rs=[r for r in records if r['case_id']==cid and r['candidate_group']==name]
            b=[r['median_us'] for r in rs if r['variant']=='FACC'];c=[r['median_us'] for r in rs if r['variant']==name]
            summary.append(dict(case_id=cid,candidate=name,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
        core.save(ROOT/'summary.json',summary)
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=64.98,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
