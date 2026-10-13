# E029交接入口

本轮正式775267为64.65分、15/15 Pass，未达到72分；根目录仍选FRESLONG65.34。

- [报告、实验取舍与后续方向](报告.md)
- [正式结果与15点耗时](COMBO4/official_state.json)、[完整候选源码](COMBO4/kernel.asc)、[8文件工程](COMBO4/submission_ready.zip)
- [赛事规则源码审查](rules_source_audit.json)
- [后续优化路线](后续优化路线.md)、[赛事规则](赛事规则与实现边界.md)
- [已淘汰的连续搬运候选](P9PACK/kernel.asc)、[协议](protocol_phase09.json)、[执行脚本](phase09.py)、`results/phase09b/metrics.json`流水诊断
- `results/phaseNN/completion.json`为实际状态；准备记录不等于测量结果。证据ZIP经云端/本地SHA与CRC核验，详见报告末尾。

先读取最新completion及PID，禁止因SSH观察超时重复启动；每个阶段使用独立目录和同一设备锁。初筛仅测目标和边界，淘汰负收益，确认完整方案时再执行保护及正式15点测评。
