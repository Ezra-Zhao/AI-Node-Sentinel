# AI-Node-Sentinel

[English](README.md) | [简体中文](README.zh-CN.md) | **[日本語](README.ja.md)** | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

> **Note:** this translation tracks an older README version (v0.1). The English README.md is authoritative for v1.0.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold](https://img.shields.io/badge/status-scaffold_v0.1-orange)

**PCIe/XID トリアージのためのポストシリコン・ハードウェア診断エージェント**

AI インフラにおける GPU ノード障害のための AI エージェント型診断パイプライン。ノードテレメトリ（カーネルログ、DCGM/NVML メトリクス）を取り込み、NVIDIA XID エラーイベントを特定し、構造化されたトリアージ判定を出力します——オンコールエンジニアが生の `dmesg` 出力ではなく「何が壊れたか、深刻度、まず何をすべきか」を得られるように。

大規模 GPU フリートの現実に向けて構築（ポストシリコン検証、データセンター運用、そして 1 枚の不良 GPU が数千枚を停滞させうる AI 学習クラスタ）。

> **プロジェクト状態：スキャフォールド v0.1（正直エディション）。**
> エンドツーエンドのパイプラインは現在、**シミュレーション**のテレメトリで動作します。実際に動く部分：イベント取り込み、公開ドキュメントに基づく XID 照会、レポート描画。
> 未実装（コード内で明示）：実地検証済みの XID→修復デシジョンツリーと LangChain LLM 推論ステップ。このリポジトリの何ものも、本番の診断ツールであるふりはしていません。

---

## 課題

1,000 基を超える GPU クラスタでは、XID エラー（NVIDIA のハードウェア／ファームウェアエラーコード）が GPU 劣化の最初のシグナルです——しかし今のトリアージは手作業です：

1. エンジニアが各ノードの `dmesg` を `Xid` で grep します。
2. コードの意味を調べます（NVIDIA Xid カタログ、暗黙知）。
3. 判断します：ノードをドレイン？GPU をリセット？再起動？カードを RMA？
4. その間、学習ジョブは壊れたハードウェア上でリトライを続けます。

遅いトリアージ ＝ GPU 時間の浪費 ＝ AI インフラ規模では実際のお金。

## アーキテクチャ

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

パイプラインのステージ：

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## 技術スタック

- **Python 3.11+**、スキーマに `pydantic`
- **LangChain**（`requirements-llm.txt`、任意）—— LLM 推論ステップ用に確保
- テストに `pytest`、GitHub Actions CI

## クイックスタート（2 分、GPU 不要）

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# シミュレーション・テレメトリでのエンドツーエンド・デモ：
python examples/demo.py
```

デモは 4 ノードクラスタをシミュレートし、合成 XID イベントを注入、トリアージパイプライン全体を実行、レポートを出力し、`examples/demo_report.json` に書き込みます。全イベントにシミュレーションのラベル付き——`telemetry/simulator.py` を参照。

```bash
# テスト実行
python -m pytest tests/ -q
```

### 実際の LLM の接続（TODO）

```bash
pip install -r requirements-llm.txt   # langchain スタック
```

`agent/llm.py` に `LangChainChatProvider` を実装し、`TriageAgent(llm=...)` に渡します。システムプロンプトのドラフトは `prompts/triage_system.md` にあります。

## ロードマップ

- [x] v0.1 スキャフォールド：パイプライン、シミュレータ、デモ、テスト、CI
- [ ] 実地検証済みの XID→修復デシジョンツリーをコード化（`tools/triage_rules.py`）
- [ ] 根拠に基づくプロンプトの LangChain 推論ステップ（`agent/llm.py`）
- [ ] 実際のテレメトリコネクタ：`dmesg` パーサ、DCGM exporter、NVML
- [ ] 時間ウィンドウをまたぐ再発障害検出（flapping GPU）
- [ ] Alertmanager / PagerDuty webhook 出力

## ライセンス

MIT —— [LICENSE](LICENSE) を参照。

## 謝辞

XID コードのメタデータは、NVIDIA 公開の XID エラードキュメント（`https://docs.nvidia.com/deploy/xid-errors/`）と Google Cloud の GPU トラブルシューティングガイドに基づきます。このリポジトリは NVIDIA と無関係です。
