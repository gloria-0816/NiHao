"""Bounded screening: arithmetic-identical event scheduling / duplicate barriers."""
import fcntl,json,statistics
from harness import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase07'
VALID=('measured_strict_pass','measured_strict_fail_retained')
CASES={'COMBO3':[('v5_s1',1,64,'float16'),('v5_s2',7,197,'float32'),('v5_s3',128,256,'float32'),
 ('v5_s4',767,193,'float16'),('v5_s5',8,32768,'float16'),('v5_s6',1513,577,'float16'),
 ('v5_s7',3113,397,'float16'),('v5_s8',10240,512,'float16'),('v5_s9',4096,1536,'float32'),
 ('v5_s10',8192,1024,'float16'),('v5_s11',3749,3083,'float32'),('v5_s12',3408,4096,'bfloat16'),
 ('v5_s13',10300,3079,'float32'),('v5_s14_reduced',1024,128,'bfloat16'),('v5_s15_reduced',128,8192,'bfloat16'),
 ('v5_c512',161,512,'float16'),('v5_c513',161,513,'float16'),('v5_c640',1121,640,'float16'),('v5_c641',1121,641,'float16')]}
TARGETS={'COMBO3':['v5_s1','v5_s4','v5_s5','v5_s6','v5_s11']}
def main():
 if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 with (PREV/'exclusive_npu.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  proto=json.loads((HERE/'protocol_phase07.json').read_text())
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
   prior=json.loads((HERE/'results/phase05b/checks.json').read_text())
   for cid,*_ in trial.ITEMS:
    b=next(r for r in prior if r['case_id']==cid and r['variant']=='BASE')
    if b['kernel_sha256']!=proto['baseline_sha256'] or b['runner_sha256']!=core.sha(trial.runner('BASE')):raise RuntimeError('Baseline identity changed')
    if core.sha(__import__('pathlib').Path(b['directory'])/'case/output.bin')!=b['output_sha256']:raise RuntimeError('Prior output changed')
    if any(core.sha(core.origin(cid)/n)!=h for n,h in b['input_file_sha256'].items()):raise RuntimeError('Input changed')
    b=dict(b,reused_protection=True);checks.append(b)
    r=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name));r['bitwise_equal_BASE']=r.get('output_sha256')==b['output_sha256'];checks.append(r);core.save(ROOT/'checks.json',checks)
    if r['status'] not in VALID or (r['dtype']=='float32' and r['status']!='measured_strict_pass') or not r['bitwise_equal_BASE']:raise RuntimeError('Protection failed '+cid+'/'+name)
   for cid in TARGETS[name]:
    for pos,version in enumerate(('BASE',name,name,'BASE')):
     r=trial.capture(cid,version,ROOT/('pair_'+cid+'_'+str(pos)),'ordinary');pairs.append(r);core.save(ROOT/'pairs.json',pairs)
     if r['status'] not in VALID:raise RuntimeError('Invalid timing')
    b=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']=='BASE']
    c=[r['median_us'] for r in pairs if r['case_id']==cid and r['variant']==name]
    s=dict(case_id=cid,candidate=name,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b),screening_only=False)
    summary.append(s);core.save(ROOT/'summary.json',summary);print(json.dumps(s),flush=True)
    # Diagnose only material winners; avoid replaying already negative mechanisms.
    if False:
     for version in ('BASE',name):
      r=trial.capture(cid,version,ROOT/('op_'+cid+'_'+version),'op');diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
      if r['status'] not in VALID:raise RuntimeError('Invalid diagnostic')
     core.save(ROOT/'metrics.json',metric_summary(diagnostic))
  core.save(ROOT/'completion.json',dict(status='completed',goal_achieved=False,baseline_official_score=65.34,target_score=72,screening_only=False))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
