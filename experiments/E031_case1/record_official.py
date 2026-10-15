"""Parse visible-page snapshots; never call competition back-end endpoints."""
from pathlib import Path
import hashlib,json,re,zipfile
HERE=Path(__file__).resolve().parent
out=HERE/'official'
def us(text):
    m=re.fullmatch(r'([0-9.]+)(ms|[μµ]s)',text)
    if not m:raise ValueError(text)
    return float(m[1])*(1000 if m[2]=='ms' else 1)
records=[]
for p in sorted(out.glob('*_result_dom.txt')):
    name=p.name.removesuffix('_result_dom.txt')
    text=p.read_text(encoding='utf-8')
    identity=re.search(r'提交 ID：(\d+)',text)
    if not identity:continue
    points=[]
    for m in re.finditer(r'- row "(\d+) (.*?) ([0-9.]+%) ([0-9.]+(?:ms|[μµ]s)) ([0-9.]+(?:ms|[μµ]s))":',text):
        points.append(dict(case=int(m[1]),status=m[2],error=m[3],time_us=us(m[4]),tbest_us=us(m[5])))
    if not points:continue
    assert len(points)==15 and [r['case'] for r in points]==list(range(1,16))
    source=HERE/('BASE' if name.startswith('BASE') else name)/'code/kernel.asc'
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    verify=out/(name+'_editor_verified.json')
    if name=='BASE':verify=out/'baseline_editor_verified.json'
    v=json.loads(verify.read_text())
    assert v['sha256']==source_sha and v.get('matches',v.get('matchesBaseline')) is True
    urlfile=out/(name+'_url.txt')
    url=(urlfile.read_text().strip() if urlfile.exists() else
         'https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad073ddaad397b6d9b97a07' if name=='BASE' else None)
    row=dict(variant=name,id=int(identity[1]),url=url,source_sha256=source_sha,
             editor_source_verified=True,passed=sum(r['status']=='Pass' for r in points),
             points=points,case1_us=points[0]['time_us'],tbest_case1_us=points[0]['tbest_us'])
    stamp=re.search(r'提交时间：([^\n]+)',text)
    if stamp:row['submitted_at']=stamp[1]
    records.append(row)
(HERE/'official_results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
project=out/'BASE_restore_project.zip'
with zipfile.ZipFile(project) as z:
    assert z.testzip() is None
    files=[n for n in z.namelist() if not n.endswith('/')]
    expected={p.relative_to(HERE/'BASE').as_posix():p for p in (HERE/'BASE/code').rglob('*') if p.is_file()}
    assert set(files)==set(expected) and len(files)==8
    verified=[]
    for name in files:
        b=z.read(name)
        assert b==expected[name].read_bytes(),name
        verified.append(dict(path=name.removeprefix('code/'),bytes=len(b),
            sha256=hashlib.sha256(b).hexdigest(),matches_cloud_best=True))
    (out/'BASE_restore_project_verification.json').write_text(json.dumps(verified,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['variant','id','passed','case1_us','url']} for r in records],ensure_ascii=False))
