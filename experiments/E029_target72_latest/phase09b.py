"""One diagnostic pair after negative packed-input screening; no ordinary retest."""
import fcntl,json
from harness import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase09b'
VALID=('measured_strict_pass','measured_strict_fail_retained')
def main():
 if (HERE/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
 if json.loads((HERE/'results/phase09/completion.json').read_text())['status']!='completed':raise RuntimeError('Previous phase not complete')
 ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 with (PREV/'exclusive_npu.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  proto=json.loads((HERE/'protocol_phase09b.json').read_text())
  for name,expected in proto['variants'].items():
   if core.sha(trial.source(name))!=expected or core.sha(trial.runner(name))!=proto['runner_sha256'][name]:raise RuntimeError('Cached identity changed')
  core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__),harness_sha256=core.sha(HERE/'harness.py')))
  records=[];parent=None
  for name in ('P9LP','P9PACK'):
   r=trial.capture('p9_s6',name,ROOT/('op_'+name),'op')
   if name=='P9LP':parent=r.get('output_sha256')
   r['bitwise_equal_parent']=r.get('output_sha256')==parent;records.append(r);core.save(ROOT/'diagnostic.json',records)
   if r['status'] not in VALID or not r['bitwise_equal_parent']:raise RuntimeError('Diagnostic capture invalid')
  core.save(ROOT/'metrics.json',metric_summary(records))
  core.save(ROOT/'completion.json',dict(status='completed',goal_achieved=False,diagnostic_only=True,no_ordinary_retest=True))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc)));raise
