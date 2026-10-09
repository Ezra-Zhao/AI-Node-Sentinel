# AI-Node-Sentinel

[English](README.md) | **[简体中文](README.zh-CN.md)** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

> **Note:** this translation tracks an older README version (v0.1). The English README.md is authoritative for v1.0.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**面向 PCIe/XID 分诊的后硅硬件诊断 Agent**

针对 AI 基础设施中 GPU 节点故障的 AI Agent 诊断流水线：接入节点遥测数据（内核日志、DCGM/NVML 指标），识别 NVIDIA XID 错误事件，输出结构化的分诊结论——让值班工程师直接看到"哪里坏了、多严重、先做什么"，而不是原始 `dmesg` 输出。

为大规模 GPU 集群的现实而造（后硅验证、数据中心运维，以及 AI 训练集群——一块坏 GPU 就能拖住上千块卡）。

> **项目状态：脚手架 v0.1（诚实版）。**
> 整条流水线今天跑在**模拟**遥测数据上。真实的部分：事件接入、对照公开文档的 XID 查询、报告渲染。
> 仍是 TODO（代码中明确标注）：经生产验证的 XID→修复决策树，以及 LangChain LLM 推理步骤。本仓库没有任何东西假装自己已是生产级诊断工具。

---

## 问题

在 1000+ GPU 的集群里，XID 错误（NVIDIA 的硬件／固件错误码）是 GPU 退化的第一个信号——但今天的分诊全靠人工：

1. 工程师在各节点上 grep `dmesg` 找 `Xid`。
2. 查这个代码是什么意思（NVIDIA Xid 目录、口口相传的经验）。
3. 做决定：排空节点？重置 GPU？重启？RMA 换卡？
4. 与此同时，训练任务还在坏硬件上不断重试。

分诊慢 = 浪费 GPU 小时 = 在 AI 基础设施规模下就是真金白银。

## 架构

```
                    +-------------------+
                    |  Node Telemetry   |
                    | dmesg / DCGM /    |
                    | NVML  (simulated) |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    | Event Ingestion   |  agent/schemas.py
                    | (parse, normalize)|
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
   +----------+----------+        +---------+---------+
   | XID Lookup Table  |        | Triage Decision   |
   | tools/xid_lookup  |        | Tree    [TODO]    |
   | (public docs)     |        |                   |
   +----------+----------+        +---------+---------+
              |                             |
              +--------------+--------------+
                             |
                             v
                    +--------+----------+
                    |  Triage Agent     |  agent/orchestrator.py
                    |  orchestration;   |
                    |  LLM reasoning    |
                    |  via LangChain    |
                    |      [TODO]       |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    |  Triage Report    |
                    |  console + JSON   |
                    +-------------------+
```

流水线阶段：

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## 技术栈

- **Python 3.11+**，`pydantic` 做数据模型
- **LangChain**（`requirements-llm.txt`，可选）——为 LLM 推理步骤预留
- `pytest` 跑测试；GitHub Actions CI

## 快速上手（2 分钟，不需要 GPU）

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# 在模拟遥测数据上跑端到端演示：
python examples/demo.py
```

演示模拟一个 4 节点集群，注入合成 XID 事件，跑完整分诊流水线，打印报告，并写入 `examples/demo_report.json`。每个事件都标注为模拟——见 `telemetry/simulator.py`。

```bash
# 跑测试
python -m pytest tests/ -q
```

### 接入真实 LLM（TODO）

```bash
pip install -r requirements-llm.txt   # langchain 技术栈
```

然后在 `agent/llm.py` 中实现 `LangChainChatProvider`，传给 `TriageAgent(llm=...)`。系统提示词草稿在 `prompts/triage_system.md`。

## 路线图

- [x] v0.1 脚手架：流水线、模拟器、演示、测试、CI
- [ ] 把经生产验证的 XID→修复决策树编码下来（`tools/triage_rules.py`）
- [ ] 基于证据提示词的 LangChain 推理步骤（`agent/llm.py`）
- [ ] 真实遥测连接器：`dmesg` 解析器、DCGM exporter、NVML
- [ ] 跨时间窗口的复发故障检测（flapping GPU）
- [ ] Alertmanager / PagerDuty webhook 输出

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

## 致谢

XID 代码元数据取自 NVIDIA 公开的 XID 错误文档（`https://docs.nvidia.com/deploy/xid-errors/`）和 Google Cloud 的 GPU 排错指南。本仓库与 NVIDIA 无关。
