# AI-Node-Sentinel

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **[한국어](README.ko.md)** | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

> **Note:** this translation tracks an older README version (v0.1). The English README.md is authoritative for v1.0.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**PCIe/XID 트리아지를 위한 포스트실리콘 하드웨어 진단 에이전트**

AI 인프라의 GPU 노드 장애를 위한 AI 에이전트 기반 진단 파이프라인. 노드 텔레메트리(커널 로그, DCGM/NVML 메트릭)를 수집하고 NVIDIA XID 오류 이벤트를 식별하여 구조화된 트리아지 판정을 출력합니다. 당직 엔지니어가 raw `dmesg` 출력 대신 "무엇이 고장났는지, 얼마나 심각한지, 무엇을 먼저 해야 하는지"를 바로 확인할 수 있습니다.

대규모 GPU 플릿의 현실을 위해 구축(포스트실리콘 검증, 데이터센터 운영, 그리고 하나의 불량 GPU가 수천 개를 멈추게 할 수 있는 AI 학습 클러스터).

> **프로젝트 상태: 스캐폴드 v0.1(정직 에디션).**
> 엔드투엔드 파이프라인은 현재 **시뮬레이션**된 텔레메트리에서 동작합니다. 실제로 동작하는 부분: 이벤트 수집, 공개 문서 기반 XID 조회, 리포트 렌더링.
> 아직 TODO(코드에 명시): 현장 검증된 XID→조치 결정 트리와 LangChain LLM 추론 단계. 이 리포지토리의 어떤 것도 상용 진단 도구인 척하지 않습니다.

---

## 문제

1,000개 이상의 GPU 클러스터에서 XID 오류(NVIDIA 하드웨어/펌웨어 오류 코드)는 GPU 성능 저하의 첫 신호입니다. 하지만 현재 트리아지는 수동입니다:

1. 엔지니어가 노드들에서 `dmesg`를 `Xid`로 grep합니다.
2. 코드의 의미를 조회합니다(NVIDIA Xid 카탈로그, 구전 지식).
3. 결정합니다: 노드를 드레인할까? GPU를 리셋할까? 재부팅할까? 카드를 RMA할까?
4. 그 사이 학습 작업은 고장난 하드웨어에서 계속 재시도합니다.

느린 트리아지 = GPU 시간 낭비 = AI 인프라 규모에서는 실제 비용.

## 아키텍처

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

파이프라인 단계:

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## 기술 스택

- **Python 3.11+**, 스키마용 `pydantic`
- **LangChain**(`requirements-llm.txt`, 선택) — LLM 추론 단계용으로 예약
- 테스트용 `pytest`, GitHub Actions CI

## 빠른 시작(2분, GPU 불필요)

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# 시뮬레이션된 텔레메트리로 엔드투엔드 데모:
python examples/demo.py
```

데모는 4노드 클러스터를 시뮬레이션하고 합성 XID 이벤트를 주입한 뒤 전체 트리아지 파이프라인을 실행하고 리포트를 출력하며 `examples/demo_report.json`에 기록합니다. 모든 이벤트에는 시뮬레이션 라벨이 붙습니다 — `telemetry/simulator.py` 참조.

```bash
# 테스트 실행
python -m pytest tests/ -q
```

### 실제 LLM 연결(TODO)

```bash
pip install -r requirements-llm.txt   # langchain 스택
```

`agent/llm.py`에 `LangChainChatProvider`를 구현하고 `TriageAgent(llm=...)`에 전달하세요. 시스템 프롬프트 초안은 `prompts/triage_system.md`에 있습니다.

## 로드맵

- [x] v0.1 스캐폴드: 파이프라인, 시뮬레이터, 데모, 테스트, CI
- [ ] 현장 검증된 XID→조치 결정 트리 코드화(`tools/triage_rules.py`)
- [ ] 근거 기반 프롬프트의 LangChain 추론 단계(`agent/llm.py`)
- [ ] 실제 텔레메트리 커넥터: `dmesg` 파서, DCGM exporter, NVML
- [ ] 시간 창에 걸친 반복 장애 감지(flapping GPU)
- [ ] Alertmanager / PagerDuty 웹훅 출력

## 라이선스

MIT — [LICENSE](LICENSE) 참조.

## 출처

XID 코드 메타데이터는 NVIDIA 공개 XID 오류 문서(`https://docs.nvidia.com/deploy/xid-errors/`)와 Google Cloud GPU 문제 해결 가이드에서 가져왔습니다. 이 리포지토리는 NVIDIA와 무관합니다.
