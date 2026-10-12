# CANN_HuaiWei

AddRmsNormBias CANN 性能优化归档，更新于2026-10-12。

**最高完整官方成绩：64.98 分，15/15 Pass，观察排名 91。** 方案 FACC，提交 [743109](https://cannjudge.cn/public/op_challenge_xinan_prelim/addrmsnormbias/submission/6acc0f3d694b590c3c87def3)。相对上一阶段56.71分提高8.27分。排名是评测完成时观察值，会随他人提交变化。

最后一轮 HSM63：64.3 分，15/15 Pass，提交 744352。 用户要求本轮评分后停止。70分目标未达成；后续没有继续发起实验。

- [交接文档](HANDOFF.md)：最佳源码身份、15点耗时、复现和验证边界。
- [完整比赛工程](best_submission_743109.zip)：8个原始工程文件。根目录和scripts/保留同一套最佳源码。
- [kernel.asc](kernel.asc)、[选择记录](selection.json)、[全部官方结果](official_results.json)。
- [本阶段实验报告](实验报告_E026.md)、[完整实验与工具包](E026_full_experiment.zip)。原始云机报告分卷保存在 cloud_reports_E026_part*.zip，文件身份见MANIFEST.json。
- [文件哈希清单](MANIFEST.json)。此前E024文档和压缩包继续保留。

最佳版以实际 dtype、行数、列数和可用向量核数选择路径。FP32 宽行将多个64元素向量重复的平方和累加到同一组lane，最后一次 WholeReduceSum；FP16 长行保留整行残差，减少重复读写并用 mixed FP32 平方；短行按每核多行归约、原生FP16加法及affine融合减少指令；BF16 中宽行使用三阶段静态缓冲和参数复用，D128路径保留已验证批次。不同路径的实际守卫以 kernel.asc/run_kernel 为准。

![最高分官方记录](official_rank_743109.png)

构建复现见 HANDOFF.md。云机使用Ascend910B3、CANN9.0.0、40个向量核；本机Windows仅归档。自建输入不是官方隐藏输入，云机收益不能当作比赛收益，也不拼接不同提交的最快测试点。
