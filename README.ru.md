# AI-Node-Sentinel

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | **[Русский](README.ru.md)**

> **Note:** this translation tracks an older README version (v0.1). The English README.md is authoritative for v1.0.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**Агент диагностики оборудования посткремниевой стадии для сортировки PCIe/XID**

Диагностический конвейер на основе ИИ-агента для отказов GPU-узлов в ИИ-инфраструктуре: принимает телеметрию узлов (журналы ядра, метрики DCGM/NVML), выявляет события ошибок NVIDIA XID и формирует структурированные заключения сортировки — чтобы дежурный инженер получал «что сломалось, насколько серьёзно, что делать в первую очередь» вместо сырого вывода `dmesg`.

Создан для реалий крупных парков GPU (посткремниевая валидация, эксплуатация ЦОД и кластеры обучения ИИ, где один неисправный GPU может остановить тысячи других).

> **Статус проекта: каркас v0.1 (честная редакция).**
> Сквозной конвейер сегодня работает на **симулированной** телеметрии. Что реально: приём событий, поиск XID по публичной документации, формирование отчётов.
> Что пока TODO (явно помечено в коде): проверенное в эксплуатации дерево решений XID→устранение и шаг рассуждений LLM на LangChain. Ничто в этом репозитории не притворяется промышленным диагностом.

---

## Проблема

В кластере из 1000+ GPU ошибки XID (коды ошибок оборудования/прошивки NVIDIA) — первый сигнал деградации GPU, но сортировка сегодня выполняется вручную:

1. Инженер ищет `Xid` командой grep в `dmesg` на узлах.
2. Выясняют, что означает код (каталог Xid NVIDIA, неформальные знания).
3. Решают: осушить узел? сбросить GPU? перезагрузить? вернуть карту по RMA?
4. А задание обучения тем временем продолжает перезапускаться на неисправном оборудовании.

Медленная сортировка = потерянные GPU-часы = реальные деньги в масштабе ИИ-инфраструктуры.

## Архитектура

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

Этапы конвейера:

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## Технологии

- **Python 3.11+**, `pydantic` для схем
- **LangChain** (`requirements-llm.txt`, опционально) — зарезервирован для шага рассуждений LLM
- `pytest` для тестов; GitHub Actions CI

## Быстрый старт (2 минуты, GPU не нужен)

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# Сквозное демо на СИМУЛИРОВАННОЙ телеметрии:
python examples/demo.py
```

Демо симулирует кластер из 4 узлов, внедряет синтетические события XID, прогоняет полный конвейер сортировки, печатает отчёт и пишет `examples/demo_report.json`. Каждое событие помечено как симулированное — см. `telemetry/simulator.py`.

```bash
# Запуск тестов
python -m pytest tests/ -q
```

### Подключение настоящего LLM (TODO)

```bash
pip install -r requirements-llm.txt   # стек langchain
```

Затем реализуйте `LangChainChatProvider` в `agent/llm.py` и передайте его в `TriageAgent(llm=...)`. Черновик системного промпта — в `prompts/triage_system.md`.

## Планы развития

- [x] Каркас v0.1: конвейер, симулятор, демо, тесты, CI
- [ ] Закодировать проверенное в эксплуатации дерево решений XID→устранение (`tools/triage_rules.py`)
- [ ] Шаг рассуждений LangChain с промптами, опирающимися на доказательства (`agent/llm.py`)
- [ ] Коннекторы реальной телеметрии: парсер `dmesg`, экспортер DCGM, NVML
- [ ] Обнаружение повторяющихся отказов в скользящих окнах (flapping GPU)
- [ ] Вывод webhook в Alertmanager / PagerDuty

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Благодарности

Метаданные кодов XID взяты из публичной документации NVIDIA об ошибках XID (`https://docs.nvidia.com/deploy/xid-errors/`) и руководства Google Cloud по устранению неполадок GPU. Этот репозиторий не связан с NVIDIA.

---
All code in this repository is clean-room code written by Guangyi Zhao for learning and research purposes. It does not contain any client or employer confidential information.
