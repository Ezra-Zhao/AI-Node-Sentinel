# AI-Node-Sentinel

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | **[Português](README.pt.md)** | [Русский](README.ru.md)

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**Agente de diagnóstico de hardware pós-silício para triagem PCIe/XID**

Um pipeline de diagnóstico baseado em agentes de IA para falhas de nós GPU em infraestrutura de IA: ingere telemetria dos nós (logs do kernel, métricas DCGM/NVML), identifica eventos de erro NVIDIA XID e produz veredictos de triagem estruturados — para que os engenheiros de plantão recebam "o que quebrou, quão grave, o que fazer primeiro" em vez da saída bruta do `dmesg`.

Construído para a realidade das grandes frotas de GPU (validação pós-silício, operações de data center e clusters de treinamento de IA onde uma única GPU defeituosa pode paralisar milhares).

> **Estado do projeto: scaffold v0.1 (edição honesta).**
> O pipeline de ponta a ponta hoje roda com telemetria **simulada**. O que é real: ingestão de eventos, consulta XID contra documentação pública, renderização de relatórios.
> O que ainda é TODO (marcado claramente no código): a árvore de decisão XID→remediação validada em campo e a etapa de raciocínio LLM com LangChain. Nada neste repo finge ser ainda uma ferramenta de diagnóstico de produção.

---

## Problema

Em um cluster com mais de 1.000 GPUs, os erros XID (códigos de erro de hardware/firmware da NVIDIA) são o primeiro sinal de que uma GPU está se degradando — mas a triagem hoje é manual:

1. Um engenheiro faz grep de `Xid` no `dmesg` dos nós.
2. Consultam o que o código significa (catálogo Xid da NVIDIA, conhecimento tribal).
3. Decidem: drenar o nó? redefinir a GPU? reiniciar? RMA da placa?
4. Enquanto isso, o trabalho de treinamento continua tentando no hardware defeituoso.

Triagem lenta = GPU-horas desperdiçadas = dinheiro real na escala da infra de IA.

## Arquitetura

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

Etapas do pipeline:

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## Tecnologias

- **Python 3.11+**, `pydantic` para esquemas
- **LangChain** (`requirements-llm.txt`, opcional) — reservado para a etapa de raciocínio LLM
- `pytest` para testes; GitHub Actions CI

## Início rápido (2 minutos, sem GPU)

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# Demo de ponta a ponta com telemetria SIMULADA:
python examples/demo.py
```

A demo simula um cluster de 4 nós, injeta eventos XID sintéticos, executa o pipeline completo de triagem, imprime um relatório e escreve `examples/demo_report.json`. Cada evento é rotulado como simulado — ver `telemetry/simulator.py`.

```bash
# Executar testes
python -m pytest tests/ -q
```

### Conectar um LLM real (TODO)

```bash
pip install -r requirements-llm.txt   # pilha langchain
```

Em seguida, implemente `LangChainChatProvider` em `agent/llm.py` e passe-o para `TriageAgent(llm=...)`. O rascunho do system prompt está em `prompts/triage_system.md`.

## Roteiro

- [x] Scaffold v0.1: pipeline, simulador, demo, testes, CI
- [ ] Codificar a árvore de decisão XID→remediação validada em campo (`tools/triage_rules.py`)
- [ ] Etapa de raciocínio LangChain com prompts baseados em evidência (`agent/llm.py`)
- [ ] Conectores de telemetria real: parser de `dmesg`, exportador DCGM, NVML
- [ ] Detecção de falhas recorrentes em janelas de tempo (GPUs instáveis)
- [ ] Saída webhook para Alertmanager / PagerDuty

## Licença

MIT — ver [LICENSE](LICENSE).

## Atribuições

Os metadados de códigos XID vêm da documentação pública de erros XID da NVIDIA (`https://docs.nvidia.com/deploy/xid-errors/`) e do guia de solução de problemas de GPU do Google Cloud. Este repo não é afiliado à NVIDIA.
