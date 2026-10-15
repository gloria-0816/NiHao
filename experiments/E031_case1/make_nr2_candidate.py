"""A vector-only Newton path, including an Inf-safe correction operand."""
from pathlib import Path
import hashlib,json,shutil,difflib
HERE=Path(__file__).resolve().parent
raw=(HERE/'BASE/code/kernel.asc').read_bytes();base=raw.decode().replace('\r\n','\n')
assert hashlib.sha256(raw).hexdigest()=='e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
start=base.index('template <typename T>\n__global__ __vector__ void single_row_64_custom(')
end=base.index('\ntemplate <typename T>\n__global__ __vector__ void single_row_custom(',start)
entry=base[start:end];body=entry[entry.index('{')+1:entry.rfind('}')]
old='''    Sqrt(sum, sum, 1);
    PipeBarrier<PIPE_V>();
    Brcb(work, sum, 1, {1, 8});
    PipeBarrier<PIPE_V>();
    Div(y, y, work, static_cast<uint64_t>(64), static_cast<uint8_t>(1),
        {1, 1, 0, 8, 8, 0});
    PipeBarrier<PIPE_V>();'''
new='''    // All operations stay on the vector pipeline. For z=+Inf, native
    // Rsqrt(z)=0; clamp only the correction operand so 0*Inf cannot
    // turn that valid zero inverse into NaN. Finite z is unchanged.
    Rsqrt(work[8],sum,1);
    Mins(work[16],sum,3.402823466e38f,1);
    Duplicate(work[24],1.5f,1);
    PipeBarrier<PIPE_V>();
    Mul(work[32],work[8],work[8],1);
    Muls(work[16],work[16],-0.5f,1);
    PipeBarrier<PIPE_V>();
    FusedMulAdd(work[32],work[16],work[24],1);PipeBarrier<PIPE_V>();
    Mul(sum,work[8],work[32],1);PipeBarrier<PIPE_V>();
    Brcb(work,sum,1,{1,8});PipeBarrier<PIPE_V>();
    Mul(y,y,work,static_cast<uint64_t>(64),static_cast<uint8_t>(1),
        {1,1,0,8,8,0});PipeBarrier<PIPE_V>();'''
assert body.count(old)==1
body=body.replace(old,new)
helper='''__global__ __vector__ void e031_case1_nr2_custom(
    GM_ADDR x,GM_ADDR residual,GM_ADDR gamma,GM_ADDR bias,GM_ADDR output,float epsilon)
{\n    using T=half;'''+body+'}\n\n'
launch='single_row_64_custom<half><<<1, nullptr, stream>>>'
code=(base[:start]+helper+base[start:]).replace(launch,'e031_case1_nr2_custom<<<1, nullptr, stream>>>')
assert code.replace(helper,'',1).replace('e031_case1_nr2_custom<<<1, nullptr, stream>>>',launch)==base
dest=HERE/'NR2';assert not dest.exists();shutil.copytree(HERE/'BASE/code',dest/'code');(dest/'code/kernel.asc').write_bytes(code.encode())
m=dict(variant='NR2',parent='H6SHARE',baseline_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(code.encode()).hexdigest(),
       description='Vector-only FP32 Rsqrt and fused Newton correction with finite-clamped correction operand; no vector-to-scalar transfer or data-dependent branch',
       numerical_change=True,other_paths_recovered_byte_equal=True,guard='FP16 rows=1 D=64')
(dest/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(dest/'change.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),code.splitlines(True),fromfile='H6SHARE',tofile='NR2')))
print(json.dumps(m))
