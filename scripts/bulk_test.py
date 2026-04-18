"""
bulk_test.py — FactoryMind
Runs all queries from data/sample_queries.csv against Ollama qwen2.5-coder:7b
and saves results to results/results_TIMESTAMP.json
Also logs all results to Braintrust for evaluation and monitoring.
"""

import csv
import json
import time
import requests
from datetime import datetime
from pathlib import Path
import braintrust

# ── Config ──────────────────────────────────────────────────────────────────
OLLAMA_URL         = "http://localhost:11434/api/chat"
MODEL              = "qwen2.5-coder:7b"
SYSTEM_PROMPT_PATH = Path("backend/system_prompt.md")
QUERIES_PATH       = Path("data/sample_queries.csv")
RESULTS_DIR        = Path("results")

BRAINTRUST_API_KEY  = "sk-XwVSHTd7CwO7Z8Um4gpI3yvlUNvGfxaHH4daiyiXL8CyWaLD"   # ← حط الـ key بتاعك هنا
BRAINTRUST_PROJECT  = "My Project"     # ← نفس اسم المشروع في Braintrust

# Model options — keep temperature low for consistent, clinical diagnosis output
MODEL_OPTIONS = {
    "temperature": 0.3,
    "num_predict": 1500,
    "top_p": 0.9,
}

DELAY_BETWEEN_REQUESTS = 0.3  # seconds


# ── Helpers ──────────────────────────────────────────────────────────────────
def load_system_prompt() -> str:
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_PATH}")
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def load_queries() -> list[dict]:
    if not QUERIES_PATH.exists():
        raise FileNotFoundError(f"Queries CSV not found: {QUERIES_PATH}")

    queries = []
    with open(QUERIES_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(dict(row))

    if not queries:
        raise ValueError("sample_queries.csv is empty or has no data rows")

    return queries


def check_ollama_running() -> bool:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def check_model_available(model: str) -> bool:
    try:
        resp   = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(model in m for m in models)
    except Exception:
        return False


def call_ollama(system_prompt: str, user_query: str) -> dict:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_query},
        ],
        "stream":  False,
        "options": MODEL_OPTIONS,
    }

    start_time = time.time()
    response   = requests.post(OLLAMA_URL, json=payload, timeout=180)
    response.raise_for_status()
    elapsed = round(time.time() - start_time, 2)

    data = response.json()

    return {
        "response":         data["message"]["content"],
        "elapsed_seconds":  elapsed,
        "model":            data.get("model", MODEL),
        "prompt_tokens":    data.get("prompt_eval_count", 0),
        "response_tokens":  data.get("eval_count", 0),
        "total_duration_s": round(data.get("total_duration", 0) / 1e9, 2),
    }


# ── Main runner ───────────────────────────────────────────────────────────────
def run_bulk_test():
    print("=" * 60)
    print("  FactoryMind — Bulk Test Runner")
    print(f"  Model  : {MODEL}")
    print(f"  Ollama : {OLLAMA_URL}")
    print("=" * 60)

    # ── Pre-flight checks ──
    if not check_ollama_running():
        print("\n[ERROR] Ollama is not running.")
        print("  Fix: open a terminal and run:  ollama serve")
        return

    if not check_model_available(MODEL):
        print(f"\n[ERROR] Model '{MODEL}' is not pulled in Ollama.")
        print(f"  Fix: ollama pull {MODEL}")
        return

    print("\n[OK] Ollama is running and model is available.\n")

    # ── Init Braintrust ──
    bt_logger = braintrust.init_logger(
        project=BRAINTRUST_PROJECT,
        api_key=BRAINTRUST_API_KEY,
    )
    print(f"[OK] Braintrust logger initialized → project: '{BRAINTRUST_PROJECT}'\n")

    # ── Load inputs ──
    system_prompt = load_system_prompt()
    queries       = load_queries()
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results   = []

    print(f"Loaded {len(queries)} queries. Starting run...\n")

    # ── Run queries ──
    for i, row in enumerate(queries, 1):
        query_id = row.get("id",       str(i))
        category = row.get("category", "unknown")
        severity = row.get("severity", "unknown")
        query    = row.get("query",    "").strip()

        short_q = query[:65] + "..." if len(query) > 65 else query
        print(f"[{i:02d}/{len(queries)}] [{category}] {short_q}")

        try:
            result = call_ollama(system_prompt, query)

            entry = {
                "id":              query_id,
                "category":        category,
                "severity":        severity,
                "query":           query,
                "response":        result["response"],
                "elapsed_seconds": result["elapsed_seconds"],
                "model":           result["model"],
                "tokens": {
                    "prompt":   result["prompt_tokens"],
                    "response": result["response_tokens"],
                },
                "status":    "success",
                "timestamp": datetime.now().isoformat(),
            }

            # ── Log to Braintrust ──
            bt_logger.log(
                input=query,
                output=result["response"],
                metadata={
                    "id":              query_id,
                    "category":        category,
                    "severity":        severity,
                    "model":           result["model"],
                    "elapsed_seconds": result["elapsed_seconds"],
                    "prompt_tokens":   result["prompt_tokens"],
                    "response_tokens": result["response_tokens"],
                    "status":          "success",
                }
            )

            print(f"         OK — {result['elapsed_seconds']}s "
                  f"| {result['response_tokens']} tokens\n")

        except requests.exceptions.Timeout:
            entry = {
                "id": query_id, "category": category, "severity": severity,
                "query": query, "response": None,
                "error": "Request timed out after 180s",
                "status": "timeout", "timestamp": datetime.now().isoformat(),
            }

            bt_logger.log(
                input=query,
                output=None,
                metadata={
                    "id": query_id, "category": category,
                    "severity": severity, "status": "timeout",
                    "error": "Request timed out after 180s",
                }
            )

            print(f"         TIMEOUT — skipping\n")

        except Exception as e:
            entry = {
                "id": query_id, "category": category, "severity": severity,
                "query": query, "response": None,
                "error": str(e),
                "status": "error", "timestamp": datetime.now().isoformat(),
            }

            bt_logger.log(
                input=query,
                output=None,
                metadata={
                    "id": query_id, "category": category,
                    "severity": severity, "status": "error",
                    "error": str(e),
                }
            )

            print(f"         ERROR — {e}\n")

        results.append(entry)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # ── Save results locally ──
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count   = len(results) - success_count
    total_tokens  = sum(r.get("tokens", {}).get("response", 0) for r in results)
    avg_time      = round(
        sum(r.get("elapsed_seconds", 0) for r in results) / len(results), 1
    )

    output = {
        "metadata": {
            "model":          MODEL,
            "total_queries":  len(queries),
            "successful":     success_count,
            "failed":         error_count,
            "total_tokens":   total_tokens,
            "avg_response_s": avg_time,
            "run_timestamp":  timestamp,
        },
        "results": results,
    }

    output_path = RESULTS_DIR / f"results_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"  Run complete!")
    print(f"  Successful : {success_count} / {len(queries)}")
    print(f"  Failed     : {error_count}")
    print(f"  Avg time   : {avg_time}s per query")
    print(f"  Local file : {output_path}")
    print(f"  Braintrust : https://www.braintrust.dev → Logs")
    print("=" * 60)
    return output_path


if __name__ == "__main__":
    run_bulk_test()
