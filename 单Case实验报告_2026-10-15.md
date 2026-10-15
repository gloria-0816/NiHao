# AddRmsNormBias 单 Case 实验报告

整理日期：2026-10-15（北京时间）。数据截至 2026-10-14 22:16:31，最后提交 810016；本次整理没有新增测评。

## 当前保留方案与同步状态

- **整体最佳：H6SHARE，[801341](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf3990aad397b6d9a30163)，15/15 Pass，历史最高观察成绩 68.32 分。** 后续抓取该记录时为 68.05 分。
- 最后恢复相同源码：[810016](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf8ebfaad397b6d90321df) / H6RESTORE2，15/15 Pass，67.32 分。核对过的源码 SHA-256：`e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e`。
- 最佳源码保存在本机并已提交比赛平台。云机 SSH 此前关闭，**尚未确认最佳源码成功同步到云机**；以下新成绩均来自官方平台。
- 本次 GitHub 仅新增本报告。仓库现有根目录 `kernel.asc` 和旧 README 属于先前归档，未随本次报告更新为 801341 源码。

## Case1：极短单行，尚无明显突破

已验证命中 FP16、单行 D=64 实现。近期同源码基线 [807787](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf791aaad397b6d9e9e606) 为 2.08µs；本轮 TBest 为 1.09µs。

| 提交编号 / 方案 | 修改方法 | case1（µs） | 总分 / 状态 | 结论 |
|---|---|---:|---|---|
| [808405](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf7ef5aad397b6d9f0b999) / H1MASK | 复用全局向量掩码 | 2.11 | 66.91 / 15/15 Pass | 未提速 |
| [808690](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf818faad397b6d9f3f4a3) / H1SCALAR | 标量倒数＋向量乘法替代广播/向量除法 | 2.02 | 67.24 / 15/15 Pass | 本轮最快，暂不采用 |
| [809076](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf851caad397b6d9f7e1e1) / H1DMA | 按实际地址间距尝试合并输入 DMA | 2.28 | 67.25 / 15/15 Pass | 变慢；合并分支是否命中未确认 |
| [809374](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf885caad397b6d9fb9413) / H1MIX | half 输入混合精度平方累加至 float | 2.06 | 67.70 / 15/15 Pass | 未超过 808690 |
| [809844](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf8d28aad397b6d9011043) / H1DIVH | FP32 统计＋FP16 除法和仿射 | 2.12 | 67.62 / 15/15 Pass | 未提速，随后恢复整体最佳 |

本轮最快 2.02µs，较 2.08µs 少约 2.9%；仅为单次、非配对测量，尚未证明稳定收益，仍比 TBest 多约 85.3%。更早的 [798719](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf1f39aad397b6d98567d5) 曾记录 case1 1.97µs，因此 2.02µs 不是全部历史最快。早期 [795564](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acef99de7698929271c897b) / H64INV 使用原始 Rsqrt，case1 2.14µs、错误占比 1.56%，已淘汰；原始页面为 14/15 通过，旧 JSON 解析漏记失败行。

结论：五个新候选都通过全套精度，但没有明显接近 TBest。启动、搬运、同步和计算的占比尚未通过设备 profiling 分离。按用户要求结束本轮，保留整体最佳。

## Case4：残差先相加，再统一 Gather

基线 [795168](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acef482e76989292717866d) / FRAW2：8.24µs，总分 66.81。针对非对齐短行 FP16 路径；准确隐藏形状未确认，767×193 仅为旧自建代理输入。

| 提交编号 / 方案 | 修改方法 | case4（µs） | 总分 / 状态 | 结论 |
|---|---|---:|---|---|
| [798200](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf193daad397b6d97eb480) / HGRID | 连续搬运、向量生成整包索引、统一 Gather | — | 0.00 / Runtime Error | case4 Runtime Error，淘汰 |
| [798505](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf1c71aad397b6d9827286) / HGADD2 | 紧凑 FP16 数据先相加，整包只做一次 Gather | 7.09 | 66.98 / 15/15 Pass | 明显提速 |
| [798719](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf1f39aad397b6d98567d5) / HG64 | 列索引标量种子 256→64，向量扩展及尾部处理 | 7.25 | 67.36 / 15/15 Pass | 当轮整体总分更高，保留 |

HGADD2 的 7.09µs 较基线减少约 14.0%；HG64 的 7.25µs 减少约 12.0%，完整总分更高，因此当轮选择 HG64。后续同一路径的计时波动不计为新算法收益。

## Case6：复用 UB 生命周期，扩大批量

基线 [800258](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf2f0eaad397b6d996d7cb) / HMDENSE：11.95µs，总分 67.74。准确隐藏形状未确认，1513×577 仅为旧代理输入。

| 提交编号 / 方案 | 修改方法 | case6（µs） | 总分 / 状态 | 结论 |
|---|---|---:|---|---|
| [801081](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf3720aad397b6d9a01e50) / H6DENSE | 连续搬运＋残差 Add 后 Gather、临时区复用 | 12.36 | 66.85 / 15/15 Pass | 变慢，回退 |
| [801341](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf3990aad397b6d9a30163) / H6SHARE | 保留按行搬运；复用 residual/平方区及已消费 X；批量 9408→15232 元素 | 11.24 | 68.05 / 15/15 Pass | 选为整体最佳 |

H6SHARE 保持原归约和 Sqrt/Div 顺序，延后输出槽等待；11.24µs 较基线减少约 5.9%。全套 15/15 Pass，历史最高观察成绩 68.32 分。

## Case7：首轮有效，第二轮未再突破

首轮基线 [798719](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf1f39aad397b6d98567d5) / HG64：16.77µs。准确隐藏形状未确认，3113×397 仅为旧代理输入。

| 提交编号 / 方案 | 修改方法 | case7（µs） | 总分 / 状态 | 结论 |
|---|---|---:|---|---|
| [799707](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf298aaad397b6d990989e) / HMSHARE | 复用 residual/平方区和已消费 X，扩大批量 | 16.52 | 未留存 / 15/15 Pass | 改善有限，总分未独立留存 |
| [800258](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf2f0eaad397b6d996d7cb) / HMDENSE | 连续搬运＋紧凑 Add＋整包一次 Gather；双 X 槽延后输出等待 | 15.12 | 67.74 / 15/15 Pass | 减少约 9.8%，保留 |

第二轮在整体最佳 801341 上继续，case7 对照为 15.29µs：

| 提交编号 / 方案 | 修改方法 | case7（µs） | 总分 / 状态 | 结论 |
|---|---|---:|---|---|
| [806891](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf7104aad397b6d9df8343) / H7DOUBLE | 索引表按行数倍增扩展，减少 Adds 发射 | 15.31 | 67.83 / 15/15 Pass | 无收益 |
| [807049](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf728daad397b6d9e1979e) / H7BANK | 调整静态 UB 地址的 bank 相位 | 15.25 | 66.70 / 15/15 Pass | 仅约 0.26%，整体表现更差 |
| [807237](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf7450aad397b6d9e3d8d5) / H7VEC | CreateVecIndex＋整数 Add 替代标量索引写入 | — | 0.00 / Runtime Error | case7 Runtime Error，根因未定位 |
| [807512](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acf769caad397b6d9e6c6d5) / H7REPLAY | 去除独立平方区，以第二次 Gather＋Cast 重建 Y；批量 11520→13056 | 20.00 | 66.95 / 15/15 Pass | 较对照慢约 30.8% |

结论：保留已进入 H6SHARE 的 HMDENSE 路径。更少指令或更大批量没有自动带来提速；额外 Gather/Cast 抵消了工作区节省。第二轮四个候选均未采用。

## Case13：大输入缓存策略带来较大收益

此前多次完整提交约 554–573µs。[794009](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acee778e769892927098552) / COLD 在实际输入张量达到 96MiB 时对 X/residual 使用硬件缓存旁路，gamma、bias、输出维持原策略，case13 降至 **425.22µs**，15/15 Pass，总分 66.73；较此前水平约减少 23%–26%。条件依据实际张量字节数，没有使用隐藏 case 编号或输入值识别。

801341 中 case13 为 418.85µs；最后同源码复测 810016 为 423.22µs，当时 TBest 396.73µs。精确 dtype、行数和 D 未确认。早期 FPACK3、FLATE、FOUT2 等没有同等幅度收益，缓存策略保留进入后续整体方案。

## 最佳完整方案的重点 Case 对照

以下分别来自两次完整提交，没有拼接不同实验的单点最小值。单位为 µs。

| Case | 801341 / H6SHARE | 810016 / 同源码复测 | 复测当时 TBest |
|---|---:|---:|---:|
| 1 | 2.10 | 2.17 | 1.09 |
| 4 | 7.19 | 7.43 | 4.28 |
| 6 | 11.24 | 11.30 | 7.64 |
| 7 | 15.29 | 15.19 | 10.21 |
| 13 | 418.85 | 423.22 | 396.73 |

其他 case 随完整提交一起检验，本报告不为缺少独立证据的 case 编造优化结论。不同时间的 TBest、计时及成绩会变化，小幅单次波动不足以认定算法收益。后续若继续实验，应从 801341 完整源码出发，分别判断单点耗时与整体表现。

## 方法资料与数据依据

- [Gather 接口](https://asc.gitcode.com/api/SIMD-API/basic_api/memory_vector_compute/scatter_gather/Gather.html)：case4、7 重排参考。
- [静态 Tensor 编程](https://asc.gitcode.com/guide/programming_guide/programming_model/ai_core_simd_programming/cpp_tensor_programming/static_tensor_programming.html)、[Double Buffer 实践](https://asc.gitcode.com/guide/operator_practice/simd_operator_optimization/pipeline_scheduling/enable_double_buffer.html)：UB 生命周期及流水安排参考。
- [Mask 接口](https://asc.gitcode.com/api/appendix/Mask_interface_summary.html)、[Div 接口](https://asc.gitcode.com/api/SIMD-API/basic_api/memory_vector_compute/basic_arithmetic/Div.html)：case1 掩码、除法实验参考。

实验编号、逐点时间和取舍来自本机 E030 官方结果快照、stage_state.json、候选 manifest 及最佳实验索引；历史 68.32 分另有用户提供的平台截图。上述提交链接可供复核。本文只记录报告，没有附源码、压缩包或大体积日志。
