"""Merge tiny GM DMA packets using verified actual pointer strides; no arithmetic changes."""
import fcntl,json,statistics,csv
from pathlib import Path
from phase01 import trial,core,HERE,PREV,metric_summary
ROOT=HERE/'results/phase05'
VALID=('measured_strict_pass','measured_strict_fail_retained')

def main():
    if (PREV/'PAUSED_BY_USER').exists():raise RuntimeError('Paused by user')
    if json.loads((HERE/'results/phase04/completion.json').read_text())['status']!='completed':raise RuntimeError('Prior phase incomplete')
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    with (PREV/'exclusive_npu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proto=json.loads((HERE/'protocol_phase05.json').read_text())
        if core.sha(trial.BASE_SOURCE)!=trial.EXPECTED_BASE:raise ValueError('Baseline changed')
        core.save(ROOT/'identity.json',dict(protocol=proto,driver_sha256=core.sha(__file__)))
        for name,m in proto['variants'].items():
            if core.sha(trial.source(name))!=m['sha256']:raise ValueError('Source changed')
            f=ROOT/('build_'+name);f.mkdir(mode=0o700)
            cmd=['env','ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0','KERNEL_SOURCE='+str(trial.source(name)),
                 'BUILD_DIR='+str(trial.runner(name).parent),'bash',str(trial.OLD/'cloud_bench/build.sh')]
            r=core.run_logged(cmd,f/'stdout.log',f/'stderr.log',600);core.save(f/'record.json',r)
            if r['returncode']!=0 or r['timed_out']:raise RuntimeError('Build failed '+name)
            print('Build completed '+name,flush=True)
        trial.ITEMS=[('s1',1,64,'float16'),('s2',7,197,'float32'),('short193',3,193,'float32'),('short255',17,255,'float32'),
                     ('short256',40,256,'float32'),('short192',7,192,'float32'),('short257',7,257,'float32'),('short41',41,197,'float32')]
        trial.stage_inputs()
        special=[]
        for seed in (7,17,73,1337):
            cid='pair64_seed'+str(seed);d=HERE/'inputs'/cid
            if not d.exists():core.case_data.generate(d,[1,64],'float16',seed=seed,case_id=cid)
            special.append(cid)
        for pattern in ('zeros','cancel','wide_range','specials'):
            cid='pair64_'+pattern;d=HERE/'inputs'/cid
            if not d.exists():core.case_data.generate(d,[1,64],'float16',seed=1729,pattern=pattern,case_id=cid)
            special.append(cid)
        checks=[]
        for name,parent,cases in [('S64PAIR','COMBO',['s1']+special),('S256PAIR','S256B',[i[0] for i in trial.ITEMS[1:]])]:
            for cid in cases:
                b=trial.capture(cid,parent,ROOT/('check_'+cid+'_'+parent));c=trial.capture(cid,name,ROOT/('check_'+cid+'_'+name))
                c['bitwise_equal_parent']=c.get('output_sha256')==b.get('output_sha256');checks.extend((b,c));core.save(ROOT/'checks.json',checks)
                if b['status'] not in VALID or c['status'] not in VALID or not c['bitwise_equal_parent']:raise RuntimeError('DMA output changed '+cid)
                if name=='S256PAIR' and c['status']!='measured_strict_pass':raise RuntimeError('FP32 strict failed')
        pairs=[];summary=[]
        for name,parent,cid in [('S64PAIR','COMBO','s1'),('S256PAIR','S256B','s2'),('S256PAIR','COMBO','s2')]:
            for block in range(2):
                order=(parent,name,name,parent) if block==0 else (name,parent,parent,name)
                for pos,v in enumerate(order):
                    r=trial.capture(cid,v,ROOT/('pair_'+name+'_'+parent+'_'+str(block)+'_'+str(pos)),'ordinary')
                    r.update(candidate_group=name,comparison_parent=parent,block=block,position=pos);pairs.append(r);core.save(ROOT/'pairs.json',pairs)
                    if r['status'] not in VALID:raise RuntimeError('Invalid timing')
            rs=[r for r in pairs if r['candidate_group']==name and r['comparison_parent']==parent]
            b=[r['median_us'] for r in rs if r['variant']==parent];c=[r['median_us'] for r in rs if r['variant']==name]
            summary.append(dict(candidate=name,parent=parent,case_id=cid,base_us=b,candidate_us=c,gain_pct=100*(statistics.median(b)-statistics.median(c))/statistics.median(b)))
            core.save(ROOT/'summary.json',summary);print(json.dumps(summary[-1]),flush=True)
        diagnostic=[]
        for cid,variants in [('s1',('COMBO','S64PAIR')),('s2',('S256B','S256PAIR'))]:
            for name in variants:
                r=trial.capture(cid,name,ROOT/('op_'+cid+'_'+name),'op')
                op_names=[];mte2=[]
                for p in (Path(r['directory'])/'profile').rglob('*.csv'):
                    if p.name.startswith('OpBasicInfo'):
                        with p.open(encoding='utf-8-sig') as h:op_names.extend(x.get('Op Name','') for x in csv.DictReader(h))
                    if p.name.startswith('Memory_'):
                        with p.open(encoding='utf-8-sig') as h:
                            for x in csv.DictReader(h):
                                try:mte2.append(float(x['aiv_mte2_instructions']))
                                except (KeyError,ValueError):pass
                r['observed_op_names']=op_names;r['paired_entry_observed']=any('paired_' in n for n in op_names)
                r['median_mte2_instruction_count']=statistics.median(mte2) if mte2 else None
                diagnostic.append(r);core.save(ROOT/'diagnostic.json',diagnostic)
        core.save(ROOT/'metrics.json',metric_summary(diagnostic))
        core.save(ROOT/'completion.json',dict(status='completed',official_score_unchanged=65.36,target_score=72,goal_achieved=False))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        ROOT.mkdir(parents=True,exist_ok=True);core.save(ROOT/'completion.json',dict(status='failed',error=str(exc),goal_achieved=False));raise
