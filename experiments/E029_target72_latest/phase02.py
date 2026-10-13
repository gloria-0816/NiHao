import fcntl,json,statistics
from pathlib import Path
from harness import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase02'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def main():
 if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
 if json.loads((HERE/'results/phase01b/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior unfinished')
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 with (PREV/'exclusive_npu.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  proto=json.loads((HERE/'protocol_phase02.json').read_text())
  if core.sha(trial.source('BASE'))!=trial.EXPECTED_BASE or core.sha(trial.source('HSG'))!=proto['variants']['HSG']['sha256']:raise RuntimeError('Source changed')
  core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__),harness_sha256=core.sha(HERE/'harness.py')))
  f=ROOT/'build_HSG';f.mkdir(mode=0o700)
  cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source('HSG')),'BUILD_DIR='+str(trial.runner('HSG').parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
  r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
  if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed')
  print('BUILD HSG completed',flush=True)
  trial.ITEMS=[('s4',767,193,'float16'),('sg255',1280,255,'float16'),('sg192',767,192,'float16'),('sg256',767,256,'float16'),('sg159',159,193,'float16'),('sg160',160,193,'float16')]
  trial.stage_inputs();checks=[]
  for cid,*_ in trial.ITEMS:
   parent=None
   for name in ('BASE','HSG'):
    r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
    if name=='BASE':parent=r.get('output_sha256')
    r['bitwise_equal_BASE']=r.get('output_sha256')==parent;checks.append(r);core.save(ROOT/'checks.json',checks)
    if r['status'] not in VALID or not r['bitwise_equal_BASE']:raise RuntimeError('Invalid protection '+cid+'/'+name)
  pairs=[]
  for pos,name in enumerate(('BASE','HSG','HSG','BASE')):
   r=trial.capture('s4',name,ROOT/('pair_'+str(pos)),'ordinary');pairs.append(r);core.save(ROOT/'pairs.json',pairs)
   if r['status'] not in VALID:raise RuntimeError('Invalid timing')
  b=[r['median_us'] for r in pairs if r['variant']=='BASE'];c=[r['median_us'] for r in pairs if r['variant']=='HSG']
  summary=dict(base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b),screening_only=True)
  core.save(ROOT/'summary.json',summary);print(json.dumps(summary),flush=True)
  records=[]
  for name in ('BASE','HSG'):
   r=trial.capture('s4',name,ROOT/('op_'+name),'op');records.append(r);core.save(ROOT/'diagnostic.json',records)
  core.save(ROOT/'metrics.json',metric_summary(records))
  core.save(ROOT/'completion.json',dict(status='completed',goal_achieved=False,baseline_official_score=65.34,target_score=72,screening_only=True))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
