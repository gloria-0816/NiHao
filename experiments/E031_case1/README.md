# E031：只针对 case1 的独立优化实验

2026-10-15。本轮完成 11 个候选，尚未确认稳定的 case1 收益；继续保留 H6SHARE，未将任何候选合入基线。正式页面最后恢复为完全相同的 H6SHARE 工程，提交 824837，15/15 Pass。

## 基线来源与范围

使用仓库 `gloria-0816/CANN_HuaiWei`，实验起点为 `main` 的 `2a532820040826724c09133f6b60b8ea94eda70d`。本轮结束再次检查，远端 `main` 仍为该提交。

队友已于北京时间 10 月 15 日 10:31 将最佳完整工程同步到云机：

`/home/developer/addrms_experiments/E030/best_801341_H6SHARE_20261015`

精确副本保存在 `BASE/`，其中同步回执与八文件清单逐字节核验通过。这一回执取代早期报告中“云机尚未确认同步”的旧结论。保留方案为 801341 / H6SHARE，历史同源码复测为 810016；历史最高观察分数 68.32 不能作为本轮新收益。

H6SHARE 的 `kernel.asc` SHA256：

`e6a9f33d0d730fcd20d8a4f6d533929b89cd9bbeb84ce6090e2a8eed8501394e`

仓库根目录仍是旧 FRESLONG 归档，本轮未改动。后续应从本目录 `BASE/code/` 继续。

历史场景记录将 case1 定位到 FP16、总行数 1、D=64。云机使用 `[1,1,64]` 作为代表场景，没有把隐藏输入分布或前导单维的具体写法当作已知事实。本轮不需要额外场景探针。

所有候选都保留 H6SHARE 原函数，新增独立 helper，只替换原有 `rows == 1 && d == 64` 中的 FP16 调用。其他数据类型、尺寸与七个工程文件保持一致；`audit_scope.py` 独立解析括号并验证这些范围约束。PAIR、DMA4 依据实际指针间距选择合法的跨步拷贝，条件不满足时回到原实现。

## 云机筛选

环境：Ascend 910B3、CANN 9.0.0、40 个向量核。每个性能进程先预热 10 次；普通分析保留 31 个设备任务，取最后 20 个任务的用时。云机普通分析有明显的快慢交替现象，故同时列出排序后较快十个、较慢十个任务的中位数。这两列只是描述分布，不是独立重复试验。

所有用时单位为 µs；完整逐任务数据在 `cloud_summary.json` 和原始日志包内。

| 候选 | 改动 | 20 次中位数 | 快半组中位数 | 慢半组中位数 |
|---|---|---:|---:|---:|
| FENCE | 精简同步，最终输出改用 PIPE_ALL 等待 | 2.2705 | 1.39 | 3.22 |
| BANK | 调整 UB 区域的 32 字节相位 | 2.33 | 1.40 | 3.19 |
| EARLY | 提前 gamma/bias 转换并共享屏障 | 2.34 | 1.41 | 3.35 |
| NR | Rsqrt 加一次 Newton 修正，非有限统计量回退 | 2.54 | 1.59 | 3.40 |
| PAIR | 四个输入合成两次跨步拷贝 | 2.27 | 1.38 | 3.23 |
| DMA4 | 实际等间距分配时合成一次跨步拷贝 | 2.27 | 1.37 | 3.32 |
| MASK | 显式 repeat 接口，共享 64/1/64 mask | 2.24 | 1.37 | 3.33 |
| OUTNC | 128 字节输出绕过 L2 分配 | 2.71 | 1.33 | 3.91 |
| INNC | 四个短输入绕过 L2 分配 | 2.7805 | 1.53 | 4.0705 |
| READY | 四次读入共享一个完成事件 | 2.42 | 1.41 | 3.30 |
| NR2 | 全向量 Rsqrt/Newton，避免向标量传值 | 2.39 | 1.54 | 3.45 |

| 同批基线对照 | 20 次中位数 | 快半组中位数 | 慢半组中位数 |
|---|---:|---:|---:|
| 开始 BASE | 2.2305 | 1.39 | 3.21 |
| screen01 结束 BASE | 2.32 | 1.38 | 3.36 |
| screen02 结束 BASE | 2.36 | 1.39 | 3.211 |
| screen03 结束 BASE | 2.2905 | 1.35 | 3.3605 |
| screen04 结束 BASE | 2.20 | 1.41 | 3.15 |
| screen05 结束 BASE | 2.31 | 1.43 | 3.2505 |

没有候选在快慢两组和正式评测中显示一致收益，故没有进入收益确认用的多轮交替复测，也没有合并候选。MASK 与历史的 mask 复用属于同一方向，本轮是显式接口实现的独立测量，不声称方向首次提出。

基线单算子分析另取 5 个样本：向量计算时间约 0.193µs，读入约 0.60–0.825µs，标量活动约 0.42–0.497µs，且观察到取指等待波动。各流水时间可能重叠，不能相加当作关键路径。它们提示短任务的传输、指令发射与等待成本值得继续研究，不能证明某个单一瓶颈。PAIR、DMA4 的普通分析 CSV 中算子名均为新增 helper，确认本机快路径确实执行。

## 精度与运行完整性

12 次编译成功，包括 BASE 和全部 11 个候选。8 组输入为 uniform(seed=42、7、2026)、zeros、cancel、checkerboard、wide_range、specials。

- BASE 8 次、候选 88 次，共 96 次云机精度运行全部严格通过。
- 除 NR、NR2 在 cancel 上各一次非逐位相同外，其余逐位等于基线；这两次也通过严格误差检查。
- 额外以正/负 Inf 构造 2 组输入，BASE、NR2 共 4 次运行严格通过且逐位相同。这些检查不代表覆盖所有非有限组合。
- 普通性能分析 17 次，单算子分析 1 次，均同时验证输出。成功云机进程合计 118 次，全部 `measured_strict_pass`。

`baseline_01` 留有一次准备失败记录：未加载 CANN 环境导致找不到 msprof，尚未启动 NPU。原始记录的 `running` 是异常退出前遗留状态；已在汇总中明确排除，不能当作有效计时或仍在运行的任务。

## 正式评测

每次提交前通过页面的复制按钮读回完整编辑器内容，校验源码 SHA256；结果保存全部 15 个点，仅以 case1 判断是否值得继续。以下每次都是 15/15 Pass，case1 输出错误占比均为 0.00%。

| 顺序 | 方案 | 提交 | case1 | TBest |
|---|---|---|---:|---:|
| 1 | H6SHARE BASE | [823983](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad073ddaad397b6d9b97a07) | 2.04µs | 1.07µs |
| 2 | FENCE | [824187](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad075b1aad397b6d9bb9c31) | 2.06µs | 1.07µs |
| 3 | PAIR | [824363](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad0777faad397b6d9bd9d18) | 2.10µs | 1.07µs |
| 4 | NR2 | [824731](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad07b42aad397b6d9c1d2e7) | 2.06µs | 1.07µs |
| 5 | H6SHARE 恢复对照 | [824837](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6ad07c3eaad397b6d9c2e68b) | 2.10µs | 1.07µs |

相同源码的开始与结束对照已相差 0.06µs。FENCE、NR2 相对最后一次对照的 0.04µs 表面优势落在本轮基线波动范围内，并且未超过起始基线，因此不能宣称成功。这里也不把其他点的随机波动、单次最低值或变化中的总分拼成“新最佳”。

恢复后额外从评测页面下载完整工程，确认八个文件全部与 `BASE/code/` 逐字节相同。凭据在 `official/BASE_restore_project.zip`、对应验证 JSON、结果页面快照和 PNG；`record_official.py` 可重新核验。

## 证据与复现

- `BASE/`：精确最佳工程、队友同步回执与历史评测记录。
- 各候选目录：完整八文件工程、独立差异和源码身份清单。候选均是未采用的实验版本。
- `cloud_summary.json`、`scope_audit.json`、`official_results.json`：本轮结论的机器可读依据。
- `evidence_metadata_20261015.zip`：1,077 个日志/JSON/CSV/TXT 及逐文件 SHA256 清单。原始输入、输出、可执行文件和 profiler 二进制留在 `/home/developer/addrms_experiments/E031_case1`，身份哈希记录在日志里。
- `harness_snapshot_20261015.zip`：第一次不可变导出，26 个文件。初始筛选误把文件名 `build.sh` 当作 build 目录排除；随后只读取回缺失脚本，完整包为 `harness_snapshot_complete_20261015.zip`，27 个文件。`package_harness.py` 记录补全过程，导出脚本也已修正目录判断。

主要归档 SHA256：

| 文件 | SHA256 |
|---|---|
| evidence_metadata_20261015.zip | `7b3572730fca728b656bdb9494fb8ef1dbb3fc228cd6e657f2dd2dadc438a22b` |
| harness_snapshot_20261015.zip | `dd643a5f5cbc931fbf7ce7ff10b60aa1be9f5ddcfac950bf6ac27624d8457d94` |
| harness_snapshot_complete_20261015.zip | `e0d25308bf5d8d17e0e42c7e36f3c183836f0b12d458b34809a88ed664126a68` |

本地 Python 3 可直接运行以下核验，无需 NPU，也无需解压长路径日志：

```text
python audit_scope.py
python summarize_cloud.py
python record_official.py
```

云机重现需 CANN 9.0.0、NumPy、CMake 与 Ascend 设备。将完整 harness 包解压到本目录的 `harness/`，保留内部目录结构；`run_cloud.py` 在旧完整仓库中复用原 harness，在单独 checkout 中自动使用该快照。现有云机路径下的命令示例：

```bash
cd /mnt/workspace/addrms_cloudbench/huawei-CANN/experiments/E031_case1
export ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0
bash harness/cloud_bench/with_cann.sh python3 run_cloud.py build BASE FENCE
bash harness/cloud_bench/with_cann.sh python3 run_cloud.py check FENCE
bash harness/cloud_bench/with_cann.sh python3 run_cloud.py screen repeat06 FENCE
```

驱动的输出目录固定为上述云机实验目录。原测量文件保留，性能标签必须使用新名称；已有精度记录会复用。迁移到其他账号或全新机器时，先调整驱动与快照中工具链/输出目录，并确保 `/home/developer/addrms_experiments` 存在。候选生成器会拒绝覆盖已有目录；复核当前结果无需重新生成候选。
