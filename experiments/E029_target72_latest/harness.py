from pathlib import Path
import importlib.util,json,csv,statistics
HERE=Path(__file__).resolve().parent
PREV=Path('/home/developer/addrms_E027/experiments/E027_target70')
spec=importlib.util.spec_from_file_location('e027_trial',PREV/'resume_probe.py')
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
core=trial.core
trial.HERE=HERE
trial.BASE_SOURCE=HERE/'BASE/kernel.asc'
trial.BASE_RUNNER=Path('/mnt/workspace/addrms_cloudbench/huawei-CANN/experiments/E027_new_methods/build_FRESLONG/cloud_addrmsnormbias')
trial.EXPECTED_BASE='d676dd20267c736d2c35d245c043be933a13f84ba0e0fc67d887e30611e66bce'
trial.source=lambda name:trial.BASE_SOURCE if name=='BASE' else HERE/name/'kernel.asc'
trial.runner=lambda name:trial.BASE_RUNNER if name=='BASE' else HERE/('build_'+name)/'cloud_addrmsnormbias'
core.version=lambda name:(trial.runner(name),core.sha(trial.source(name)))
def metric_summary(records):
    out=[]
    for r in records:
        rows=[]
        for p in (Path(r['directory'])/'profile').rglob('*.csv'):
            if p.name.startswith('PipeUtilization'):
                with p.open(encoding='utf-8-sig') as f: rows.extend(csv.DictReader(f))
        fields=('aiv_time(us)','aiv_vec_time(us)','aiv_scalar_time(us)','aiv_mte2_time(us)','aiv_mte3_time(us)','aiv_vec_ratio','aiv_scalar_ratio','aiv_mte2_ratio','aiv_mte3_ratio')
        metrics={}
        for k in fields:
            values=[]
            for row in rows:
                try:values.append(float(row[k]))
                except (ValueError,KeyError,TypeError):pass
            metrics[k]=statistics.median(values) if values else None
        out.append(dict(variant=r['variant'],case_id=r['case_id'],n_core_records=len(rows),metrics=metrics))
    return out
