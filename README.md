# CANN_HuaiWei

AddRmsNormBias 的 CANN 9.0 性能优化实验与交接，归档日期 2026-10-11。

**最高完整官方提交：56.71 分，15/15 Pass，观察排名 158。** 提交 [735124](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acb926f694b590c3c439f38)，提交时间 2026/10/11 21:43:11。相对 E023/M6 的 55.16 分提高 1.55 分；这是完整提交的最高观察成绩，保留同源码两次计时，不以单次最高分宣称稳定收益。

## 接手入口

- [实验报告](实验报告_E024.md)：方法来源、采用/淘汰原因、云机对照、全部 15 点官方时间。
- [交接文档](HANDOFF.md)：最佳版本、目录、复跑方式及后续重点。
- [完整比赛工程 ZIP](best_submission_735124.zip)：8 文件原始工程；根目录及 scripts/ 也保留同一工程源码。
- [当前完整 kernel.asc](kernel.asc)、[版本选择记录](selection.json)、[完整官方结果](official_results.json)。
- [E024 全部实验与工具归档](E024_full_experiment.zip)：候选源码、基线、驱动及其依赖、正式结果和完整云机报告包；保留原目录结构。
- [438 条云机记录汇总](audit_summary.json)、[原始云机报告](cloud_reports.zip)。

## 本轮改动

从完整 M6 基线出发，采用 FP32 小行静态批量归约、FP16 整块 Cast，以及每核可一次装下的 FP16 短行静态缓存。新增路径依据实际 shape、dtype 和可用核数选择。

|版本|官方分数|通过|观察排名|
|---|---:|---|---:|
|M6（此前基线）|55.16|15/15|181|
|TINY2|56.11|15/15|162|
|COMBO|56.25|15/15|163|
|HALFSTATIC 首次|56.08|15/15|164|
|HALFSTATIC 同源码复测|56.71|15/15|158|

HALFSTATIC 两组云机交错对照的第4场景分别快 10.24% 和 9.76%；两次官方第4点分别为 8.57 / 8.65 μs，COMBO 为 9.62 μs。ONEROW 只有约0.9%收益，ONEINV 回退约6.3%，均未采用。所有原始结果已保留，不拼接各轮最快测试点。

![官方分数](official_score_735124.png)
![官方排名](official_rank_735124.png)

## 构建及运行

在已配置 CANN 9.0.0 的 A2 环境中，根目录保留完整比赛工程（包括 scripts/）。`run.sh` 的行为来自比赛工程，运行前按自身环境设置 CANN 路径。Windows 本机归档环境没有 NPU，正式测试在云机和比赛网站完成。

云机实验复跑请解压 `E024_full_experiment.zip` 并阅读其中 `REPRODUCE.md`。自建输入不是官方隐藏输入的复现，云机耗时也不等于官方耗时。

原研究来源仓库：[ttal6688/huawei-CANN](https://github.com/ttal6688/huawei-CANN)。本仓库是本轮独立归档；该来源仓库内的旧任务表不作为本轮状态。
