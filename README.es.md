# AI-Node-Sentinel

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **[Español](README.es.md)** | [Português](README.pt.md) | [Русский](README.ru.md)

> **Note:** this translation tracks an older README version (v0.1). The English README.md is authoritative for v1.0.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**Agente de diagnóstico de hardware post-silicio para triaje PCIe/XID**

Un pipeline de diagnóstico basado en agentes de IA para fallos de nodos GPU en infraestructura de IA: ingiere telemetría de nodos (registros del kernel, métricas DCGM/NVML), identifica eventos de error NVIDIA XID y produce veredictos de triaje estructurados, para que los ingenieros de guardia obtengan "qué se rompió, qué tan grave, qué hacer primero" en lugar de la salida cruda de `dmesg`.

Construido para la realidad de las grandes flotas de GPU (validación post-silicio, operaciones de centros de datos y clústeres de entrenamiento de IA donde una sola GPU defectuosa puede paralizar miles).

> **Estado del proyecto: andamiaje v0.1 (edición honesta).**
> El pipeline completo funciona hoy con telemetría **simulada**. Lo que es real: ingesta de eventos, consulta XID contra documentación pública, renderizado de informes.
> Lo que sigue siendo TODO (marcado claramente en el código): el árbol de decisión XID→remediación validado en campo y el paso de razonamiento LLM con LangChain. Nada en este repo pretende ser todavía un sistema de diagnóstico de producción.

---

## Problema

En un clúster de más de 1,000 GPU, los errores XID (códigos de error de hardware/firmware de NVIDIA) son la primera señal de que una GPU se está degradando, pero el triaje hoy es manual:

1. Un ingeniero busca `Xid` con grep en el `dmesg` de los nodos.
2. Buscan qué significa el código (catálogo Xid de NVIDIA, conocimiento tribal).
3. Deciden: ¿drenar el nodo? ¿reiniciar la GPU? ¿reiniciar el equipo? ¿RMA de la tarjeta?
4. Mientras tanto, el trabajo de entrenamiento sigue reintentando sobre hardware roto.

Triaje lento = GPU-horas desperdiciadas = dinero real a escala de infra de IA.

## Arquitectura

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

Etapas del pipeline:

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## Tecnologías

- **Python 3.11+**, `pydantic` para esquemas
- **LangChain** (`requirements-llm.txt`, opcional): reservado para el paso de razonamiento LLM
- `pytest` para pruebas; GitHub Actions CI

## Inicio rápido (2 minutos, sin GPU)

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# Demo de extremo a extremo con telemetría SIMULADA:
python examples/demo.py
```

La demo simula un clúster de 4 nodos, inyecta eventos XID sintéticos, ejecuta el pipeline completo de triaje, imprime un informe y escribe `examples/demo_report.json`. Cada evento está etiquetado como simulado — ver `telemetry/simulator.py`.

```bash
# Ejecutar pruebas
python -m pytest tests/ -q
```

### Conectar un LLM real (TODO)

```bash
pip install -r requirements-llm.txt   # pila langchain
```

Luego implementa `LangChainChatProvider` en `agent/llm.py` y pásalo a `TriageAgent(llm=...)`. El borrador del system prompt está en `prompts/triage_system.md`.

## Hoja de ruta

- [x] Andamiaje v0.1: pipeline, simulador, demo, pruebas, CI
- [ ] Codificar el árbol de decisión XID→remediación validado en campo (`tools/triage_rules.py`)
- [ ] Paso de razonamiento LangChain con prompts basados en evidencia (`agent/llm.py`)
- [ ] Conectores de telemetría real: parser de `dmesg`, exportador DCGM, NVML
- [ ] Detección de fallos recurrentes en ventanas de tiempo (GPU inestables)
- [ ] Salida webhook a Alertmanager / PagerDuty

## Licencia

MIT — ver [LICENSE](LICENSE).

## Atribuciones

Los metadatos de códigos XID provienen de la documentación pública de errores XID de NVIDIA (`https://docs.nvidia.com/deploy/xid-errors/`) y de la guía de solución de problemas de GPU de Google Cloud. Este repo no está afiliado a NVIDIA.

---
All code in this repository is clean-room code written by Guangyi Zhao for learning and research purposes. It does not contain any client or employer confidential information.
