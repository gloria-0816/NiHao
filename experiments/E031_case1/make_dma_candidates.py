"""Coalesce only the addressed 128-byte rows; never read allocator gaps."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
raw=(HERE/'BASE/code/kernel.asc').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e'
base=raw.decode().replace('\r\n','\n')
start=base.index('template <typename T>\n__global__ __vector__ void single_row_64_custom(')
end=base.index('\ntemplate <typename T>\n__global__ __vector__ void single_row_custom(',start)
entry=base[start:end]
body=entry[entry.index('{')+1:entry.rfind('}')]
launch='''single_row_64_custom<half><<<1, nullptr, stream>>>(
                x, residual, gamma, bias, output, epsilon);'''
assert base.count(launch)==1
gm='''    GlobalTensor<T> xgm, rgm, ggm, bgm, outgm;
    xgm.SetGlobalBuffer((__gm__ T*)x);
    rgm.SetGlobalBuffer((__gm__ T*)residual);
    ggm.SetGlobalBuffer((__gm__ T*)gamma);
    bgm.SetGlobalBuffer((__gm__ T*)bias);
    outgm.SetGlobalBuffer((__gm__ T*)output);'''
slots='''    LocalTensor<T> xt(TPosition::VECIN, 0, 64);
    LocalTensor<T> rt(TPosition::VECIN, 256, 64);
    LocalTensor<T> gt(TPosition::VECIN, 512, 64);
    LocalTensor<T> bt(TPosition::VECIN, 768, 64);'''
copies='''    DataCopy(xt, xgm, copy);
    DataCopy(rt, rgm, copy);
    SetFlag<HardEvent::MTE2_V>(0);
    DataCopy(gt, ggm, copy);
    DataCopy(bt, bgm, copy);
    SetFlag<HardEvent::MTE2_V>(1);'''
assert body.count(gm)==body.count(slots)==body.count(copies)==1


def write(name,helper,host,description):
    dest=HERE/name
    assert not dest.exists()
    code=(base[:start]+helper+'\n\n'+base[start:]).replace(launch,host)
    assert code.replace(helper+'\n\n','',1).replace(host,launch)==base
    shutil.copytree(HERE/'BASE/code',dest/'code')
    (dest/'code/kernel.asc').write_bytes(code.encode())
    m=dict(variant=name,parent='H6SHARE',baseline_sha256=hashlib.sha256(raw).hexdigest(),
           source_sha256=hashlib.sha256(code.encode()).hexdigest(),description=description,
           guard='Only the existing FP16 rows=1,D=64 branch; pointer-distance safety guard otherwise retains original launch',
           numerical_change=False,other_paths_recovered_byte_equal=True,
           reads_only_valid_tensor_bytes=True,host_tensor_reads=False,kernels_per_valid_call=1)
    (dest/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    (dest/'change.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),code.splitlines(True),fromfile='H6SHARE',tofile=name)))
    print(json.dumps(m))


pair=body.replace(gm,'''    GlobalTensor<T> inputGm, parameterGm, outgm;
    inputGm.SetGlobalBuffer((__gm__ T*)inputBase);
    parameterGm.SetGlobalBuffer((__gm__ T*)parameterBase);
    outgm.SetGlobalBuffer((__gm__ T*)output);''').replace(slots,'''    LocalTensor<T> inputPacket(TPosition::VECIN,0,128);
    LocalTensor<T> parameterPacket(TPosition::VECIN,256,128);
    LocalTensor<T> xt(TPosition::VECIN,xOffset,64);
    LocalTensor<T> rt(TPosition::VECIN,128-xOffset,64);
    LocalTensor<T> gt(TPosition::VECIN,256+gammaOffset,64);
    LocalTensor<T> bt(TPosition::VECIN,384-gammaOffset,64);''').replace(copies,'''    DataCopyParams inputCopy={2,4,inputGap,0};
    DataCopyParams parameterCopy={2,4,parameterGap,0};
    DataCopy(inputPacket,inputGm,inputCopy);
    SetFlag<HardEvent::MTE2_V>(0);
    DataCopy(parameterPacket,parameterGm,parameterCopy);
    SetFlag<HardEvent::MTE2_V>(1);''')
helper='''__global__ __vector__ void e031_case1_pair_custom(
    GM_ADDR inputBase,GM_ADDR parameterBase,GM_ADDR output,float epsilon,
    uint16_t inputGap,uint16_t parameterGap,uint32_t xOffset,uint32_t gammaOffset)
{\n    using T=half;'''+pair+'}'
host='''const uint64_t xa=reinterpret_cast<uint64_t>(x),ra=reinterpret_cast<uint64_t>(residual);
            const uint64_t ga=reinterpret_cast<uint64_t>(gamma),ba=reinterpret_cast<uint64_t>(bias);
            const uint64_t dx=xa<ra?ra-xa:xa-ra,dg=ga<ba?ba-ga:ga-ba;
            if(dx>=128 && dx%32==0 && (dx-128)/32<=65535 &&
               dg>=128 && dg%32==0 && (dg-128)/32<=65535) {
                e031_case1_pair_custom<<<1,nullptr,stream>>>(
                    xa<ra?x:residual,ga<ba?gamma:bias,output,epsilon,
                    static_cast<uint16_t>((dx-128)/32),static_cast<uint16_t>((dg-128)/32),
                    xa<ra?0:128,ga<ba?0:128);
            } else {
                '''+launch+'''
            }'''
write('PAIR',helper,host,'Two strided DMA commands for X/residual and gamma/bias; arbitrary pair ordering preserved through UB offsets, actual pointer gaps are metadata')

packet=body.replace(gm,'''    GlobalTensor<T> packetGm,outgm;
    packetGm.SetGlobalBuffer((__gm__ T*)x);
    outgm.SetGlobalBuffer((__gm__ T*)output);''').replace(slots,'''    LocalTensor<T> packet(TPosition::VECIN,0,256);
    LocalTensor<T> xt(TPosition::VECIN,0,64);
    LocalTensor<T> rt(TPosition::VECIN,128,64);
    LocalTensor<T> gt(TPosition::VECIN,256,64);
    LocalTensor<T> bt(TPosition::VECIN,384,64);''').replace(copies,'''    DataCopyParams packetCopy={4,4,gap,0};
    DataCopy(packet,packetGm,packetCopy);
    SetFlag<HardEvent::MTE2_V>(0);''').replace('    WaitFlag<HardEvent::MTE2_V>(1);\n','')
helper='''__global__ __vector__ void e031_case1_dma4_custom(
    GM_ADDR x,GM_ADDR output,float epsilon,uint16_t gap)
{\n    using T=half;'''+packet+'}'
host='''const uint64_t xa=reinterpret_cast<uint64_t>(x),ra=reinterpret_cast<uint64_t>(residual);
            const uint64_t ga=reinterpret_cast<uint64_t>(gamma),ba=reinterpret_cast<uint64_t>(bias);
            const uint64_t distance=ra>xa?ra-xa:0;
            if(distance>=128 && distance%32==0 && (distance-128)/32<=65535 &&
               ga>ra && ba>ga && ga-ra==distance && ba-ga==distance) {
                e031_case1_dma4_custom<<<1,nullptr,stream>>>(
                    x,output,epsilon,static_cast<uint16_t>((distance-128)/32));
            } else {
                '''+launch+'''
            }'''
write('DMA4',helper,host,'One strided four-row DMA only for an actual equally-spaced X,residual,gamma,bias allocation; exact original fallback otherwise')
