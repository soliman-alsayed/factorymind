# FactoryMind — Industrial Fault Diagnosis AI

> AI-powered assistant for diagnosing mechanical and electrical equipment faults.
> Built with Ollama (local LLM) + Braintrust (evaluation platform) — **zero API costs.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-local-green.svg)](https://ollama.ai)
[![Braintrust](https://img.shields.io/badge/Braintrust-evaluation-purple.svg)](https://braintrust.dev)
[![Overall Score](https://img.shields.io/badge/Overall%20Score-98%25-brightgreen.svg)](#evaluation-results)

---

## 🏭 What is FactoryMind?

FactoryMind is an **industrial maintenance AI advisor** that helps factory engineers and technicians:

- Diagnose root causes of mechanical and electrical equipment faults
- Prioritize corrective actions (🔴 Immediate / 🟡 Urgent / 🟢 Scheduled)
- Detect safety-critical situations automatically
- Handle ambiguous queries by asking targeted clarifying questions

**Domain coverage:** Centrifugal & reciprocating pumps · Induction motors · Compressors · Hydraulic systems · Heat exchangers · Conveyor & fan systems

---

## 🧠 What Makes This Different

Most AI demos just show a chatbot responding. FactoryMind goes further:

| Typical AI Demo | FactoryMind |
|----------------|-------------|
| No evaluation | 6 automated scorers |
| "Looks good" judgment | 98% measured score |
| Single test | 25 diverse fault queries |
| No safety logic | 100% safety detection rate |
| No observability | Full Braintrust logging |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
system_prompt.md  ←── FactoryMind persona + output format
    │
    ▼
Ollama (local)  ←── qwen2.5-coder:7b running on your machine
    │
    ▼
Structured Response
    │
    ├──► Braintrust Logs  ←── observability + trace storage
    │
    └──► score_results.py  ←── 6 automated scorers
              │
              ▼
         scored_vX_TIMESTAMP.json
```

---

## 📁 Project Structure

```
factorymind/
├── backend/
│   └── system_prompt.md        ← FactoryMind persona & output format
├── data/
│   └── sample_queries.csv      ← 25 diverse fault diagnosis queries
├── scripts/
│   ├── bulk_test.py            ← runs all queries, logs to Braintrust
│   ├── score_results.py        ← applies 6 scorers to results JSON
│   └── test_single.py          ← manual single-query tester
├── results/
│   ├── results_TIMESTAMP.json  ← raw model responses
│   └── scored_vX_TIMESTAMP.json← scored results with breakdown
└── pyproject.toml
```

---

## ⚙️ Tech Stack

| Component | Tool | Why |
|-----------|------|-----|
| LLM Runtime | [Ollama](https://ollama.ai) | 100% local, zero cost |
| Model | qwen2.5-coder:7b | Strong reasoning, runs on consumer hardware |
| Evaluation Platform | [Braintrust](https://braintrust.dev) | Production-grade LLM observability |
| Package Manager | [uv](https://github.com/astral-sh/uv) | Fast, modern Python packaging |
| Language | Python 3.11+ | |

---

## 🚀 Setup & Usage

### Prerequisites
- [Ollama](https://ollama.ai) installed and running
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/soliman-alsayed/factorymind
cd factorymind

# 2. Install dependencies
uv sync

# 3. Pull the model
ollama pull qwen2.5-coder:7b

# 4. Make sure Ollama is running
ollama serve
```

### Run a single query

```bash
# Default query
uv run python scripts/test_single.py

# Custom query
uv run python scripts/test_single.py "My hydraulic pump is losing pressure"

# Built-in test presets
uv run python scripts/test_single.py --safety      # safety-critical scenario
uv run python scripts/test_single.py --vibration   # vibration diagnosis
uv run python scripts/test_single.py --scope       # out-of-scope handling
uv run python scripts/test_single.py --ambiguous   # ambiguous query handling
```

### Run all 25 queries + log to Braintrust

```bash
uv run python scripts/bulk_test.py
# Results saved to results/results_TIMESTAMP.json
# All traces logged to Braintrust automatically
```

### Score the results

```bash
uv run python scripts/score_results.py
# Applies 6 automated scorers
# Saves scored_vX_TIMESTAMP.json
```

---

## 📊 Evaluation Results

Evaluated on **25 queries across 9 failure categories** using 6 automated scorers.

### Overall Score: 98% ✅

| Scorer | Score | Description |
|--------|-------|-------------|
| `safety_alert` | **100%** | Detects smoke, fire, gas leaks — triggers safety block |
| `has_confidence_level` | **100%** | Every response ends with High/Medium/Low confidence |
| `out_of_scope` | **100%** | Correctly refuses non-maintenance queries |
| `ambiguous_handled` | **100%** | Asks clarifying questions for vague inputs |
| `template_compliance` | **96%** | Follows structured diagnosis template |
| `has_priority_level` | **95%** | Labels every response IMMEDIATE/URGENT/SCHEDULED |

### Results by Category

| Category | Queries | Perfect (1.0) | Notes |
|----------|---------|---------------|-------|
| specific_equipment | 6 | 6/6 ✅ | Pumps, motors, compressors |
| multi_symptom | 3 | 3/3 ✅ | Combined failure patterns |
| safety_critical | 2 | 2/2 ✅ | 100% safety detection |
| predictive_maintenance | 2 | 2/2 ✅ | Service intervals + oil analysis |
| symptom_vibration | 2 | 2/2 ✅ | ISO 10816 vibration analysis |
| diagnostic_interpretation | 2 | 2/2 ✅ | Oil analysis + vibration reports |
| out_of_scope | 2 | 2/2 ✅ | Correct refusal behavior |
| ambiguous | 2 | 2/2 ✅ | Clarifying questions triggered |
| comparison_knowledge | 2 | 2/2 ✅ | Comparison tables |
| beginner_user | 1 | 0/1 ⚠️ | Adapts tone — skips template |

> **Note on beginner_user (AVG: 0.56):** The model correctly adapts its response style for non-expert users, simplifying language and skipping the technical template. This is the *right* behavior — the scorer limitation, not a model failure.

---

## 🔍 Sample Response

**Query:** `My centrifugal pump is producing a high-pitched whining noise and the outlet pressure has dropped by 20% over the past 3 days. Operating at 1480 RPM, pumping water at 60°C.`

**Response structure:**
```markdown
## Centrifugal Pump — High-Pitched Noise + Pressure Drop

> Priority Level: 🟡 URGENT
> Equipment Context: Centrifugal pump, 1480 RPM, 60°C water, 20% pressure drop over 3 days

### 🔍 Probable Causes
| # | Cause          | Likelihood | Reasoning |
|---|----------------|------------|-----------|
| 1 | Cavitation      | High       | ... |
| 2 | Impeller wear   | Medium     | ... |
| 3 | Bearing failure | Low        | ... |

### 🔧 Recommended Actions
...

### 📊 Confidence Level: Medium
```

---

## 🛡️ Safety Design

FactoryMind implements a **Safety-First** design:

- Automatically detects: smoke, fire, burning smell, sparks, explosions, gas leaks, loud bangs
- Immediately outputs a ⚠️ SAFETY ALERT block before any diagnosis
- Instructs personnel to stop equipment and evacuate before proceeding
- **Tested and verified: 100% detection rate on safety-critical queries**

---

## 🧪 Evaluation Methodology

The scoring system uses **category-aware evaluation** — different query types are scored differently:

```python
# Diagnosis queries → full template check
# Out-of-scope queries → refusal check
# Ambiguous queries → clarifying questions check
# Comparison queries → skipped (different format by design)
```

This avoids penalizing correct behavior that doesn't follow the diagnosis template.

---

## 👤 Author

**Soliman Alsayed** — [GitHub](https://github.com/soliman-alsayed)
