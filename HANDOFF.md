# E024 接手文档

## 当前版本

最高完整源码为 HALFSTATIC（复测提交 735124），56.71 分、15/15 Pass，观察排名158。以根目录 `kernel.asc` 或 `best_submission_735124.zip` 为后续起点。源码 SHA256 `2973d43eec7cb4e727ff088429cf71573f535fc053f226a47ff94712d1b2595d`；网页编辑器只将 CRLF 统一为 LF，其完整文本 SHA256 `c572e0b397df473f83a65d3c434febd2fd2ced410747595d34ada444a25afcad`。对应云机 runner SHA256 `911653b126d86b3374c7ad90b7a8c2bc73b3cef0da0c7e1e34d91f59ab8171b4`。

复测与首次 HALFSTATIC 源码完全相同。第一次56.08分、第二次56.71分，说明完整总分存在计时波动；第4点在两次正式测试及两组云机对照中均改善。M6→最新提交第3点4.94→3.49μs，第4点9.57→8.65μs。

## 内容

根目录与 `scripts/` 是当前最佳8文件比赛工程。`实验报告_E024.md` 与 JSON/PNG/TXT 记录正式成绩及全部对照。`E024_full_experiment.zip` 内保留以下路径：

- `experiments/E024_small_batch/`：TINY、SHORTR2、TINY2、FLAT、COMBO、ONEROW、ONEINV、HALFSTATIC 及复测/selected；驱动、资料、数字审计和438条云机记录的完整报告包。
- `experiments/E023_performance_rewrite/M6/code/`：本轮父版本；`selected/selection.json` 保留其官方成绩及身份。
- `experiments/E006A_probe/`：E024 驱动导入所需的3个文件。
- `cloud_bench/`：构建器、执行器、输入生成器和校验/Profiling工具，不含 build 目录或二进制。

## 验证边界

正式提交全部15/15 Pass。HALFSTATIC 的51个数值用例、102次对照运行均与 COMBO 输出逐位一致；候选FP16 43次、FP32 5次 strict通过，3个BF16缩小场景的旧strict失败与父版一致。18个特殊值用例共36次运行无新增失败。详情见 `half_numerical_audit.json`。

TINY2/COMBO 采用不同FP32归约顺序，按实际数值容差检查。原始失败、未采用候选和同源码复测完整保留。NPU最后健康且无运行进程；本归档上传不会启动新的云机试验。

## 后续重点

从最高分完整版本继续，优先研究大规模 FP32 非对齐行的搬运/存储效率及 BF16 的吞吐。第13、14、15点距 TBest 仍有空间。每次只改变一个数据流方法，与父版本做交错测量，再合并完整源码到比赛网站测试。不要直接重试本轮已淘汰的 ONEROW / ONEINV。公开技术来源在 `research.json` 和实验报告中。
