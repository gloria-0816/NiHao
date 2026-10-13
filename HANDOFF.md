# E027：更换优化方法的十次正式评测交接（2026-10-13）

<!-- E029 latest continuation -->
后续状态见[E029交接](experiments/E029_target72_latest/报告.md)：用户已恢复优化，目标72；新增正式775267为64.65分、15/15 Pass，根工程继续保持FRESLONG65.34。下面十次停止记录保留为当时历史，不作为后续停止指令。

本轮 **10/10 次正式评测已经结束，全部 15/15 Pass；最高完整成绩为 FRESLONG 65.34 分**，提交 [768708](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd8ea9e769892927ee263e)。最后一版 AXSMALL 为 64.02 分。最高未超过 70 分，因此按用户设定停止新增实验。没有继续提交第 11 次，也没有把“恢复最好版本”算作额外测试。网站目前显示最新提交 AXSMALL 的 64.02 分；仓库根目录与最佳工程包选择历史最高完整源码 FRESLONG。

## 正式比赛结果

|次数|完整候选|提交|总分|通过|评测时观察排名|
|---|---|---|---:|---|---:|
|1|DBLOCK|[768104](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd8445e769892927e6277d)|63.95|15/15|104|
|2|CONST|[768306](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd8859e769892927e93601)|63.52|15/15|104|
|3|FRES8|[768574](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd8cbae769892927ec8d8e)|64.11|15/15|89|
|4|FRESLONG|[768708](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd8ea9e769892927ee263e)|65.34|15/15|78|
|5|FRESWL|[769154](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd94bae769892927f3bb58)|64.04|15/15|92|
|6|FRES15|[769607](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd99dce769892927f90d58)|64.18|15/15|91|
|7|AFFLONG|[770144](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acd9fd9e769892927ffbfd7)|64.42|15/15|92|
|8|HFAST128|[771506](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acdb0b4e769892927111ce2)|63.63|15/15|98|
|9|RMSCF|[771696](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acdb392e76989292713fd9e)|64.03|15/15|93|
|10|AXSMALL|[771910](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acdb6d3e769892927173e50)|64.02|15/15|95|

排名会变化，记录值是当时观察结果。各候选的 official/ 保存原始页面文本、结果 JSON、结果和排名截图。小数耗时来自网页显示值，毫秒换算为微秒；没有拼接不同提交的最快点。TBest 在本轮和前一日之间发生变化，不能将相对历史 FACC 64.98 的 0.36 分全部归因于算法改进，也不能据一次 65.34 分声称稳定突破 65 分。

## 实际实施的方法与取舍

正百分比表示云机候选比对照快，负百分比表示更慢。以下是自建形状的设备计时，不代表官方隐藏用例。

|候选|方法|云机观察|处理|
|---|---|---|---|
|TREE|二叉树归约|s11 -2.42%；s13 +0.09%|云机筛选后淘汰|
|BTREE|块归约后树形归约|s11 +7.74%；s13 -0.07%|未提交；保留对照|
|DBLOCK|两级块归约|s11 +8.92%；s13 -0.02%|正式63.95|
|CONST|FP16 编译期行宽特化|s8 +1.69%；s10 +0.55%|正式63.52|
|LIBRARY|高阶 RmsNorm 接口|s3 -3.72%|云机筛选后淘汰|
|FRES8|FP32 参数常驻、双输入/输出槽、静态同步|1024×4097/8192：+65.64%/+63.01%|正式64.11|
|FRESLONG|FP32 整行残差驻留、直接搬入最终 Y、槽位复用|1024×16384/32768：+21.50%/+12.65%|正式65.34；选用完整版本|
|FRESWL|参数常驻扩展至中宽行，保留长行路径|s9 +16.84%；s11 -10.66%；s13 -1.18%|正式64.04|
|FRES15|只选择有收益的行宽区间|s9 +16.82%|正式64.18|
|AFFEARLY|提前 gamma 缩放，与归约重叠；最终 FMA|s11 +1.32%；s13 -0.11%|用于合成 AFFLONG|
|AFFLONG|提前 affine 与最佳长行驻留组合|s11 +0.59%；s13 +0.01%|正式64.42|
|RSMALL|原生 Rsqrt 替换 Sqrt/Div|s1/s2/s3：+4.12%/+7.60%/+1.24%|9个常规输入新增8个 strict 失败；未作为最佳|
|RSMALLF|Rsqrt 加一次 FMA Newton 修正|s1/s2/s3：-7.47%/-11.16%/-4.17%|性能下降；部分 strict 失败；淘汰|
|RFMAW|批量路径 Rsqrt 修正|s4/s6/s11：-1.55%/-5.59%/-6.54%|性能下降；淘汰|
|HVAR128|FP16 方差归约及输入幅值回退|实现存在未清零 padding 的问题|无效原型；不得作为有效方法收益|
|HFAST128|清零 padding 后 FP16 方差、溢出回退 FP32|s6 +0.87%；s7 -0.95%；s8 +5.84%；s10 -2.16%|正式63.63；15/15|
|HWAVE2|FP16 逻辑核波次改为物理 AIV 的两倍|s6 -29.83%；s7 -27.74%|淘汰；未提交|
|HWAVE4|FP16 逻辑核波次改为物理 AIV 的四倍|s6 -67.66%；s7 -66.16%|淘汰；未提交|
|RMSCF|缓存常量、融合 sum/D+epsilon|云机已编译；SSH 断开后未测 NPU|正式64.03；15/15|
|HFRMSCF|融合均方计算与 FP16 方差候选组合|云机已编译；未测 NPU|未提交|
|AXSMALL|小输入连续地址 DMA 合并、独立 fallback、Axpy 均方融合|未做云机测试；比赛端编译成功|正式64.02；15/15|

额外保留 FRESW（已编译但未单独测量）、AXPROTO（与 AXSMALL 源码相同的准备版本，未云机编译）和 HVAR128_failed_scope（第一次编译失败的原始版本）。它们不是额外正式比赛次数。HVAR128 随后修复了编译作用域，但 padding 错误仍使该实现无效；修复 padding 后独立生成的是 HFAST128，不混用两者记录。

本轮没有仅围绕原方案调整常数，已尝试归约拓扑、静态片上驻留与槽位复用、计算重排、低精度方差、近似倒平方根及修正、逻辑核波次和搬运融合。多个自建输入出现明显设备收益，正式成绩却没有对应幅度的改善。这说明这些形状的云机收益不足以预测隐藏测试的总分；本轮无法证明新方法能超过 70 分。

## 最佳完整源码身份及路径

采用 `FRESLONG/code` 的完整八文件工程。kernel.asc SHA256：`d676dd20267c736d2c35d245c043be933a13f84ba0e0fc67d887e30611e66bce`。云机 runner SHA256：`9052108564f96a75d24abece7fc780f52c0ffbf2464545cfe233f35dc78d42a4`。

FRESLONG 继承 FACC 的少行/短行、FP16 非对齐短行、中行、长行、FP32 中宽行与 BF16 路径；新增 FP32 D8193..32768 的静态整行残差驻留路径。该路径使用约 168992 字节 UB，X 直接进入最终 Y，两个 residual/square 槽随后复用于 gamma/bias，归约完成后流式输出 affine FMA。分派只使用实际 dtype、维度、行数和设备核数；准确守卫和顺序见完整源码 run_kernel。云机的七个边界形状和五类模式共十二组检查均 strict 通过，正式评测全部 15 点通过。

|测试点|本方案 μs|当次 TBest μs|结果|
|---|---:|---:|---|
|1|2.24|1.14|Pass|
|2|2.48|1.64|Pass|
|3|2.78|2.12|Pass|
|4|7.70|4.32|Pass|
|5|5.91|4.62|Pass|
|6|11.75|7.97|Pass|
|7|16.61|10.68|Pass|
|8|31.80|29.72|Pass|
|9|69.18|67.81|Pass|
|10|47.67|45.87|Pass|
|11|156.89|131.05|Pass|
|12|80.16|75.96|Pass|
|13|554.26|397.00|Pass|
|14|4050.00|3530.00|Pass|
|15|9380.00|7960.00|Pass|

## 计时与数值验证边界

云机为 Ascend 910B3、CANN 9.0.0、40 AIV。对照是原 FACC，通常执行 ABBA/BAAB，warmup10、batch20；每次 msprof 收集 31 个任务，取最后 20 个设备任务的中位数。输入由 seed42 及实际 shape/dtype/pattern 生成。后期部分筛选只运行一个 ABBA 块，读原始 driver 模式和记录确认次数，不把所有数据称为两块。

代表输入 s1=1×64 FP16，s2=7×197 FP32，s3=128×256 FP32，s4=767×193 FP16，s5=8×32768 FP16，s6=1513×577 FP16，s7=3113×397 FP16，s8=10240×512 FP16，s9=4096×1536 FP32，s10=8192×1024 FP16，s11=3749×3083 FP32，s12=3408×4096 BF16，s13=10300×3079 FP32；s14/s15 使用较小 BF16 形状。行数以合法 batch/seq 组合表达；这些名称不证明与官方 1..15 点一一对应。

部分 FP16/BF16 自建输入在 FACC 基线就未通过更严格的本地 strict 阈值；保留基线与候选结果，没有把“官方 Pass”改写成“本地 strict 全通过”。原生 Rsqrt 和 Newton 修正候选的数值与性能结果单独记录。未因为单个精度候选失败而中止其他方法。

## 归档及复现

E027_full_experiment.zip 包含所有候选八文件源码、生成脚本、驱动、清单、十次网页证据和已下载云机 metadata 快照。ROOT/cloud_bench 与 experiments/E006A_probe 的必要依赖一起保留。将 experiments/E027_new_methods/BASE/code/kernel.asc 用 cloud_bench/build.sh 构建到 experiments/E026_target70/build_FACC，再运行 run_round.py 对应模式；Windows 本机仅做归档、源码和压缩包一致性验证，不声称本机运行过 NPU。

云机当前结果位于 /home/developer/addrms_experiments/E027。工作盘满后的迁移及失败尝试记录在早期 metadata 中。已保存 results_complete.tar.gz 和 metadata_20261013_0958.tar.gz，完整元数据不含原始输入 tensor 和二进制 runner。后期 SSH 返回连接关闭/拒绝登录，因而后期云机完整原始日志尚留在云机；本报告后期云机数字来自已读取的执行输出，归档包未假称包含全部后期云机原始日志。RMSCF/HFRMSCF 云机只编译未测量，AXSMALL 未云机编译/测量而由比赛端成功编译并通过。

## 参考资料

归约方案依据 [Huawei AddRmsNormBias 原始归约实现](https://dev.modelhub.org.cn/EngineX/xc-llm-ascend/src/commit/fbae41697e83574f073cd1eb663b66caad19d91a/csrc/add_rms_norm_bias/op_kernel/reduce_common.h)。高阶接口候选依据 [RmsNorm API](https://asc.gitcode.com/api/SIMD-API/adv_api/normalization/RmsNorm.html) 并读取已安装 CANN9 头文件。静态流水参考 [Ascend C 手动同步接口](https://www.hiascend.com/doc_center/source/zh/canncommercial/80RC3/apiref/ascendcopapi/atlasascendc_api_07_0256.html)。

倒平方根方案查阅了 [Rsqrt 官方精度说明](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/900beta2/API/ascendcopapi/atlasascendc_api_07_0036.html)，A2 原生精度需实测而不能假设满足本题阈值。最后两版融合均方使用支持实际平台的 [Axpy 基础接口](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0063.html)，没有将仅适用于其他型号的寄存器接口当作 A2 能力。

## 停止状态

最高 65.34 ≤ 70，停止条件已触发。本轮新增研究和比赛评测停止，未达到 70 分；当前仅整理并发布实验交接。所有已启动云机任务均已返回，本地记录 npu_jobs_running=false。后续如继续，需重新确认可用云机并首先校准能预测比赛收益的工作负载；这些建议尚未执行。
