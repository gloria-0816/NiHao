"""Summarize execution intervals without summing inclusive instruction/code queue times."""
from pathlib import Path
import json,collections,statistics,sys

def interval_union(intervals):
    total=0.;end=None
    for a,b in sorted(intervals):
        if end is None or a>end:total+=b-a;end=b
        elif b>end:total+=b-end;end=b
    return total

def analyze(profile):
    # Prefer the aggregate trace; per-core copies contain the same events.
    files=list(Path(profile).rglob('trace.json'))
    f=min(files,key=lambda p:len(p.parts))
    data=json.loads(f.read_text());events=[e for e in data['traceEvents'] if e.get('ph')=='X']
    groups=collections.defaultdict(list)
    for e in events:groups[(e['pid'],e['tid'],e['name'])].append(e)
    rows=[]
    for (core,pipe,instr),items in groups.items():
        durations=[float(e['dur']) for e in items]
        rows.append(dict(core=core,pipe=pipe,instruction=instr,count=len(items),min_execution_us=min(durations),median_execution_us=statistics.median(durations),max_execution_us=max(durations),execution_interval_union_us=interval_union([(float(e['ts']),float(e['ts'])+float(e['dur'])) for e in items]),source_stack_examples=list(dict.fromkeys(e.get('args',{}).get('code','') for e in items))[:2]))
    rows.sort(key=lambda r:r['max_execution_us'],reverse=True)
    pipes={p:dict(count=sum(1 for e in events if e['tid']==p),execution_interval_union_us=interval_union([(float(e['ts']),float(e['ts'])+float(e['dur'])) for e in events if e['tid']==p])) for p in sorted(set(e['tid'] for e in events))}
    return dict(kind='Simulator trace execution intervals; no board timing; engine intervals overlap; not additive',trace_file=str(f),event_count=len(events),pipes=pipes,rows=rows,notes=['CSV instr/code cycles can include queuing and nested stack attribution; they are not summed as pure execution latency.','Core-id=0 only; simulation models selected Ascend910B3, may differ from board cache/timing.'])

if __name__=='__main__':
    out=analyze(sys.argv[1]);Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(pipes=out['pipes'],top=[{k:r[k] for k in ('pipe','instruction','count','max_execution_us')} for r in out['rows'][:12]]),indent=2))
