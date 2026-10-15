"""Small-input cache policies and one readiness event, isolated to FP16 D64."""
from pathlib import Path
import hashlib,json,shutil,difflib
HERE=Path(__file__).resolve().parent
raw=(HERE/'BASE/code/kernel.asc').read_bytes();base=raw.decode().replace('\r\n','\n')
assert hashlib.sha256(raw).hexdigest()=='e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
start=base.index('template <typename T>\n__global__ __vector__ void single_row_64_custom(')
end=base.index('\ntemplate <typename T>\n__global__ __vector__ void single_row_custom(',start)
entry=base[start:end];body=entry[entry.index('{')+1:entry.rfind('}')]
launch='single_row_64_custom<half><<<1, nullptr, stream>>>'
signature='''__global__ __vector__ void e031_case1_cache_custom(
    GM_ADDR x,GM_ADDR residual,GM_ADDR gamma,GM_ADDR bias,GM_ADDR output,float epsilon)
{\n    using T=half;'''
variants={
 'OUTNC':(body.replace('    outgm.SetGlobalBuffer((__gm__ T*)output);',
     '    outgm.SetGlobalBuffer((__gm__ T*)output);\n    outgm.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);'),
     'Bypass output L2 allocation for this 128-byte output only; no arithmetic or other shape changes'),
 'INNC':(body.replace('    outgm.SetGlobalBuffer((__gm__ T*)output);',
     '''    outgm.SetGlobalBuffer((__gm__ T*)output);
    xgm.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
    rgm.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
    ggm.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
    bgm.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);'''),
     'Bypass L2 allocation for all four 128-byte input vectors on this path only; recompute every input every call'),
 'READY':(body.replace('    SetFlag<HardEvent::MTE2_V>(0);\n','')
               .replace('    WaitFlag<HardEvent::MTE2_V>(0);','    WaitFlag<HardEvent::MTE2_V>(1);')
               .replace('    PipeBarrier<PIPE_V>();\n    WaitFlag<HardEvent::MTE2_V>(1);\n', '    PipeBarrier<PIPE_V>();\n'),
     'Four independent input DMAs share one readiness event; full arithmetic and original output synchronization retained')
}
for name,(changed,description) in variants.items():
 dest=HERE/name;assert not dest.exists()
 helper=signature+changed+'}\n\n'
 code=base[:start]+helper+base[start:];code=code.replace(launch,'e031_case1_cache_custom<<<1, nullptr, stream>>>')
 assert code.replace(helper,'',1).replace('e031_case1_cache_custom<<<1, nullptr, stream>>>',launch)==base
 shutil.copytree(HERE/'BASE/code',dest/'code');(dest/'code/kernel.asc').write_bytes(code.encode())
 m=dict(variant=name,parent='H6SHARE',baseline_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(code.encode()).hexdigest(),
        description=description,numerical_change=False,guard='FP16 rows=1 D=64',other_paths_recovered_byte_equal=True)
 (dest/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 (dest/'change.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),code.splitlines(True),fromfile='H6SHARE',tofile=name)))
 print(json.dumps(m))
