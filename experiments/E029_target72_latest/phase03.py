"""Bounded screening: arithmetic-identical event scheduling / duplicate barriers."""
import fcntl,json,statistics
from harness import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase03'
VALID=('measured_strict_pass','measured_strict_fail_retained')
CASES={'HLP':[('s4',767,193,'float16'),('hl256',1280,256,'float16'),('hl160',160,193,'float16')],
 'S64BAR':[('s1',1,64,'float16'),('s64f',1,64,'float32'),('s64b',1,64,'bfloat16')],
 'P9BAR':[('s6',1513,577,'float16'),('s7',3113,397,'float16'),('pb1024',1601,1024,'float16')]}
TARGETS={'HLP':['s4'],'S64BAR':['s1'],'P9BAR':['s6','s7']}
def main():
 if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 with (PREV/'exclusive_npu.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  proto=json.loads((HERE/'protocol_phase03.json').read_text())
  if core.sha(trial.source('BASE'))!=proto['baseline_sha256']:raise RuntimeError('Baseline source changed')
  core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__),harness_sha256=core.sha(HERE/'harness.py'),baseline_runner_sha256=core.sha(trial.runner('BASE')),core_driver_sha256=core.sha(trial.OLD/'experiments/E006A_probe/cloud_driver.py')))
  checks=[];pairs=[];summary=[];diagnostic=[]
  for name,expected in proto['variants'].items():
   if core.sha(trial.source(name))!=expected:raise RuntimeError('Source changed')
   f=ROOT/('build_'+name);f.mkdir(mode=0o700)
   cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
   r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
   if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
   print('BUILD',name,'completed',flush=True)
   trial.ITEMS=CASES[name];trial.stage_inputs()
   for cid,*_ in trial.ITEMS:
    parent=None
    for version in ('BASE',name):
     r=trial.capture(cid,version,ROOT/('check_'+cid+'_'+version))
     if version=='BASE':parent=r.get('output_sha256')
     r['bitwise_equal_BASE']=r.get('output_sha256')==parent;checks.append(r);core.save(ROOT/'checks.json',checks)
     if r['status'] not in VALID or not r['bitwise_equal_BASE']:raise RuntimeError('Protection failed '+cid+'/'+version)
   for cid in TARGETS[name]:
    for pos,version in enumerate(('BASE',name,name,'BASE')):
     r=trial.capture(cid,version,ROOT/('pair_'+cid+'_'+str(pos)),'ordinary');pairs.append(r);core.save(ROOT/'pairs.json',pairs)
     if r['status'] not in VALID:raise RuntimeError('Invalid timing')
    b=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='BASE']
    c=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']==name]
    s=dict(case_id=cid,candidate=name,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b),screening_only=True)
    summary.append(s);core.save(ROOT/'summary.json',summary);print(json.dumps(s),flush=True)
    # Diagnose only material winners; avoid replaying already negative mechanisms.
    if s['gain_pct']>=2:
     for version in ('BASE',name):
      r=trial.capture(cid,version,ROOT/('op_'+cid+'_'+version),'op');diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
      if r['status'] not in VALID:raise RuntimeError('Invalid diagnostic')
     core.save(ROOT/'metrics.json',metric_summary(diagnostic))
  core.save(ROOT/'completion.json',dict(status='completed',goal_achieved=False,baseline_official_score=65.34,target_score=72,screening_only=True))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
