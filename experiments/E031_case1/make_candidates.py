"""Create complete isolated candidates; never edit the retained H6SHARE files."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
raw = (HERE/'BASE/code/kernel.asc').read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
base = raw.decode().replace('\r\n', '\n')
begin = base.index('template <typename T>\n__global__ __vector__ void single_row_64_custom(')
end = base.index('\ntemplate <typename T>\n__global__ __vector__ void single_row_custom(', begin)
entry = base[begin:end]
body = entry[entry.index('{')+1:entry.rfind('}')]
signature = '''__global__ __vector__ void e031_case1_custom(
    GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
    float epsilon)
{\n    using T = half;'''
call = 'single_row_64_custom<half><<<1, nullptr, stream>>>'
assert base.count(call) == 1


def write(name, changed, description, numerical=False):
    target = HERE/name
    assert not target.exists(), 'Preserve existing candidate '+name
    helper = signature+changed+'}\n\n'
    code = base[:begin]+helper+base[begin:]
    code = code.replace(call, 'e031_case1_custom<<<1, nullptr, stream>>>')
    recovered = code.replace(helper, '', 1).replace(
        'e031_case1_custom<<<1, nullptr, stream>>>', call)
    assert recovered == base, 'Changes escaped the selected helper/launch'
    shutil.copytree(HERE/'BASE/code', target/'code')
    (target/'code/kernel.asc').write_bytes(code.encode())
    manifest = dict(variant=name, parent='H6SHARE', baseline_sha256=hashlib.sha256(raw).hexdigest(),
                    source_sha256=hashlib.sha256(code.encode()).hexdigest(),
                    guard='dtype=float16 AND rows=1 AND D=64; existing Host branch',
                    description=description, numerical_change=numerical,
                    other_paths_recovered_byte_equal=True, kernels_per_valid_call=1,
                    host_tensor_reads=False, cached_answers=False, status='prepared')
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (target/'change.diff').write_text(''.join(difflib.unified_diff(
        base.splitlines(True), code.splitlines(True), fromfile='H6SHARE', tofile=name)))
    print(json.dumps(manifest))


fence = body.replace('''    if(!CompactParameterType<T>::value) Add(y,y,tmp,64);
    PipeBarrier<PIPE_V>();''', '''    if(!CompactParameterType<T>::value) {
        Add(y,y,tmp,64);PipeBarrier<PIPE_V>();
    }''')
fence = fence.replace('''    SetFlag<HardEvent::MTE3_V>(2);
    WaitFlag<HardEvent::MTE3_V>(2);''', '    PipeBarrier<PIPE_ALL>();')
write('FENCE', fence, 'Remove the redundant post-Cast V barrier; drain final DMA with PIPE_ALL instead of an event pair')

bank = body
for old, new in [(256,288),(512,576),(768,864),(1024,1152),(1280,1440),
                 (1536,1728),(1792,2016),(2048,2304),(2080,2368),(2336,2656)]:
    # Change UB constructor addresses only; values in operations are untouched.
    bank = bank.replace(', '+str(old)+', 64)', ', '+str(new)+', 64)')
    bank = bank.replace(', '+str(old)+', 8)', ', '+str(new)+', 8)')
write('BANK', bank, 'Separate the 32-byte bank phases of the short-row UB operands; identical math and synchronization')

parameter = '''    WaitFlag<HardEvent::MTE2_V>(1);
    if(sizeof(T)!=sizeof(float)) {
        ToFloat<T>(gf,gt,64);ToFloat<T>(bf,bt,64);PipeBarrier<PIPE_V>();
    }
'''
assert body.count(parameter) == 1
early = body.replace(parameter, '')
anchor = '    WholeReduceSum(sum, tmp, 64, 1, 1, 1, 8);\n    PipeBarrier<PIPE_V>();'
replacement = '''    WholeReduceSum(sum, tmp, 64, 1, 1, 1, 8);
    WaitFlag<HardEvent::MTE2_V>(1);
    ToFloat<T>(gf,gt,64);ToFloat<T>(bf,bt,64);
    // Parameter casts and the reduction are independent; join once.
    PipeBarrier<PIPE_V>();'''
assert early.count(anchor) == 1
early = early.replace(anchor, replacement)
write('EARLY', early, 'Issue independent gamma/bias casts beside the row reduction and share their final vector barrier')

old_norm = '''    Sqrt(sum, sum, 1);
    PipeBarrier<PIPE_V>();
    Brcb(work, sum, 1, {1, 8});
    PipeBarrier<PIPE_V>();
    Div(y, y, work, static_cast<uint64_t>(64), static_cast<uint8_t>(1),
        {1, 1, 0, 8, 8, 0});
    PipeBarrier<PIPE_V>();'''
assert body.count(old_norm) == 1
new_norm = '''    SetFlag<HardEvent::V_S>(2);WaitFlag<HardEvent::V_S>(2);
    const float mean = sum.GetValue(0);
    if(mean > 0.0f && mean < 3.402823e38f) {
        // One FP32 Newton refinement: r <- r * (1.5 - 0.5*z*r*r).
        // The exceptional-value branch retains the original Sqrt/Div path.
        Rsqrt(work[8],sum,1);
        Muls(work[16],sum,-0.5f,1);
        Duplicate(work[24],1.5f,1);
        PipeBarrier<PIPE_V>();
        Mul(work[32],work[8],work[8],1);PipeBarrier<PIPE_V>();
        FusedMulAdd(work[32],work[16],work[24],1);PipeBarrier<PIPE_V>();
        Mul(sum,work[8],work[32],1);PipeBarrier<PIPE_V>();
        Brcb(work,sum,1,{1,8});PipeBarrier<PIPE_V>();
        Mul(y,y,work,static_cast<uint64_t>(64),static_cast<uint8_t>(1),
            {1,1,0,8,8,0});PipeBarrier<PIPE_V>();
    } else {
'''+old_norm+'''
    }'''
nr = body.replace(old_norm, new_norm)
write('NR', nr, 'FP32 Rsqrt with one fused Newton correction; original Sqrt/Div for nonfinite statistics', True)
