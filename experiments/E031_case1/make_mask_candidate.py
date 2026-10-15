"""Explicit repeat/mask FP16 D64 kernel using the installed CANN 9 API."""
from pathlib import Path
import hashlib,json,shutil,difflib
HERE=Path(__file__).resolve().parent
raw=(HERE/'BASE/code/kernel.asc').read_bytes();base=raw.decode().replace('\r\n','\n')
assert hashlib.sha256(raw).hexdigest()=='e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
helper='''__global__ __vector__ void e031_case1_mask_custom(
    GM_ADDR x,GM_ADDR residual,GM_ADDR gamma,GM_ADDR bias,GM_ADDR output,float epsilon)
{
    InitSocState();
    GlobalTensor<half> xgm,rgm,ggm,bgm,outgm;
    xgm.SetGlobalBuffer((__gm__ half*)x);rgm.SetGlobalBuffer((__gm__ half*)residual);
    ggm.SetGlobalBuffer((__gm__ half*)gamma);bgm.SetGlobalBuffer((__gm__ half*)bias);
    outgm.SetGlobalBuffer((__gm__ half*)output);
    LocalTensor<half> xt(TPosition::VECIN,0,64),rt(TPosition::VECIN,256,64);
    LocalTensor<half> gt(TPosition::VECIN,512,64),bt(TPosition::VECIN,768,64);
    LocalTensor<float> y(TPosition::VECCALC,1024,64),tmp(TPosition::VECCALC,1280,64);
    LocalTensor<float> gf(TPosition::VECCALC,1536,64),bf(TPosition::VECCALC,1792,64);
    LocalTensor<float> sum(TPosition::VECCALC,2048,8),work(TPosition::VECCALC,2080,64);
    LocalTensor<half> result(TPosition::VECOUT,2336,64);
    DataCopyParams copy={1,4,0,0};
    DataCopy(xt,xgm,copy);DataCopy(rt,rgm,copy);SetFlag<HardEvent::MTE2_V>(0);
    DataCopy(gt,ggm,copy);DataCopy(bt,bgm,copy);SetFlag<HardEvent::MTE2_V>(1);
    WaitFlag<HardEvent::MTE2_V>(0);
    SetMaskNorm();SetVectorMask<float,MaskMode::NORMAL>(0,0xffffffffffffffffULL);
    Add<half,false>(xt,xt,rt,static_cast<uint64_t>(64),1,{1,1,1,8,8,8});PipeBarrier<PIPE_V>();
    Cast<float,half,false>(y,xt,RoundMode::CAST_NONE,static_cast<uint64_t>(64),1,{1,1,8,4});PipeBarrier<PIPE_V>();
    Mul<float,false>(tmp,y,y,static_cast<uint64_t>(64),1,{1,1,1,8,8,8});PipeBarrier<PIPE_V>();
    WholeReduceSum<float,false>(sum,tmp,static_cast<uint64_t>(64),1,1,1,8);PipeBarrier<PIPE_V>();
    SetVectorMask<float,MaskMode::NORMAL>(0,1);
    Muls<float,false>(sum,sum,0.015625f,static_cast<uint64_t>(1),1,{1,1,8,8});PipeBarrier<PIPE_V>();
    Adds<float,false>(sum,sum,epsilon,static_cast<uint64_t>(1),1,{1,1,8,8});PipeBarrier<PIPE_V>();
    Sqrt<float,false>(sum,sum,static_cast<uint64_t>(1),1,{1,1,8,8});PipeBarrier<PIPE_V>();
    Brcb(work,sum,1,{1,8});PipeBarrier<PIPE_V>();
    SetVectorMask<float,MaskMode::NORMAL>(0,0xffffffffffffffffULL);
    Div<float,false>(y,y,work,static_cast<uint64_t>(64),1,{1,1,0,8,8,0});PipeBarrier<PIPE_V>();
    WaitFlag<HardEvent::MTE2_V>(1);
    Cast<float,half,false>(gf,gt,RoundMode::CAST_NONE,static_cast<uint64_t>(64),1,{1,1,8,4});
    Cast<float,half,false>(bf,bt,RoundMode::CAST_NONE,static_cast<uint64_t>(64),1,{1,1,8,4});PipeBarrier<PIPE_V>();
    FusedMulAdd<float,false>(y,gf,bf,static_cast<uint64_t>(64),1,{1,1,1,8,8,8});PipeBarrier<PIPE_V>();
    Cast<half,float,false>(result,y,RoundMode::CAST_RINT,static_cast<uint64_t>(64),1,{1,1,4,8});PipeBarrier<PIPE_V>();
    SetFlag<HardEvent::V_MTE3>(1);WaitFlag<HardEvent::V_MTE3>(1);
    DataCopy(outgm,result,copy);SetFlag<HardEvent::MTE3_V>(2);WaitFlag<HardEvent::MTE3_V>(2);
    SetVectorMask<half,MaskMode::NORMAL>(0xffffffffffffffffULL,0xffffffffffffffffULL);
}

'''
anchor='template <typename T>\n__global__ __vector__ void single_row_64_custom('
launch='single_row_64_custom<half><<<1, nullptr, stream>>>'
assert base.count(anchor)==base.count(launch)==1
code=base.replace(anchor,helper+anchor).replace(launch,'e031_case1_mask_custom<<<1, nullptr, stream>>>')
assert code.replace(helper,'').replace('e031_case1_mask_custom<<<1, nullptr, stream>>>',launch)==base
dest=HERE/'MASK';assert not dest.exists();shutil.copytree(HERE/'BASE/code',dest/'code')
(dest/'code/kernel.asc').write_bytes(code.encode())
m=dict(variant='MASK',parent='H6SHARE',baseline_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(code.encode()).hexdigest(),
       description='Explicit high-dimensional repeat APIs with shared normal masks (64/1/64); preserve the baseline FP16 residual sum, FP32 Sqrt/Div and affine sequence',
       numerical_change=False,other_paths_recovered_byte_equal=True,guard='FP16 rows=1 D=64',
       prior_direction='A mask-reuse direction was tried historically without clear benefit; this explicit CANN9 repeat-API implementation is independently measured, not claimed as a novel direction')
(dest/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(dest/'change.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),code.splitlines(True),fromfile='H6SHARE',tofile='MASK')))
print(json.dumps(m))
