# E026 云机复现

环境：Ascend910B3，CANN9.0.0，40 AIV。目录是实验源码布局，不含输入tensor和runner编译产物。

1. 将huawei-CANN放到/mnt/workspace/addrms_cloudbench/huawei-CANN。读cloud_bench/README.md了解输入生成/严格验证的契约。
2. 设置ASCEND_HOME_PATH并用cloud_bench/build.sh构建，例如KERNEL_SOURCE指向experiments/E026_target70/FACC/code/kernel.asc，BUILD_DIR指向experiments/E026_target70/build_FACC。
3. E026 run_round.py导入experiments/E006A_probe/cloud_driver.py，需要其protocol.json和source_manifest.json（已收录），以及cloud_bench/scripts、profile_cases.py。small列表给出合法形状。新云机缺少E021/E023输入时会在E026/inputs重新生成，seed42；输入hash以新记录为准。
4. 标准复跑：env ASCEND_HOME_PATH=/home/developer/Ascend/cann-9.0.0 bash cloud_bench/with_cann.sh python3 experiments/E026_target70/run_round.py build FACC SCHED1；随后运行sched1quick模式。
5. 推荐先在新的结果目录实验：默认已有record.json会恢复旧结果，不能直接声称重测。run_round.py使用绝对结果路径，换目录需修改OUT和core.origin，记录变更。
6. 完整BF16先运行prepare_bffull.py，检查/home的容量和目录映射。两个完整输入原始文件合计约14GB，完整比较输出额外占用几十GB。单个BF16大tensor约1.93GB，设备上限8GiB，不能沿用缩小测试默认2GiB总设备限制。
7. NPU测量始终串行，ABBA/BAAB。云机自建数据并非官方隐藏输入；正式分数来自对应官方完整提交。

最佳比赛工程使用根目录run.sh或best_submission包，模板case0验证与上述研究矩阵是不同入口。
