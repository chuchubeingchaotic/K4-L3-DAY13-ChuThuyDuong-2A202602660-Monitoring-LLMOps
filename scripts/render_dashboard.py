#!/usr/bin/env python3
"""
Dashboard renderer for Day 13 Monitoring & LLMOps Lab.
Reads data/logs.jsonl and renders 6 panels matching config/dashboard.yaml:
1. Latency (P50, P95, P99, TTFT P95, threshold 3000ms)
2. Traffic (count, req/min, threshold >= 1 rpm)
3. Errors (error rate %, retrieval success %, threshold <= 2%)
4. Cost (total cost USD, threshold <= $2.50)
5. Tokens (sum tokens_in, sum tokens_out, threshold <= 50,000)
6. Quality (mean quality score, threshold >= 0.75)
Outputs both a CLI summary and a standalone interactive HTML dashboard in submission/evidence/dashboard.html.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"


def percentile(values: list[float | int], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_v[int(k)])
    d0 = sorted_v[int(f)] * (c - k)
    d1 = sorted_v[int(c)] * (k - f)
    return float(round(d0 + d1, 2))


def main() -> None:
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found. Run load_test.py first to generate logs.")
        return

    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not records:
        print("Error: No valid JSON logs found.")
        return

    req_received = [r for r in records if r.get("event") == "request_received"]
    resp_sent = [r for r in records if r.get("event") == "response_sent"]
    req_failed = [r for r in records if r.get("event") == "request_failed"]

    # 1. Latency Panel
    latencies = [r["latency_ms"] for r in resp_sent if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in resp_sent if "ttft_ms" in r]
    p50_lat = percentile(latencies, 50)
    p95_lat = percentile(latencies, 95)
    p99_lat = percentile(latencies, 99)
    p95_ttft = percentile(ttfts, 95)

    # 2. Traffic Panel
    total_requests = len(req_received)
    timestamps = [
        datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
        for r in req_received
        if "ts" in r
    ]
    if timestamps and len(timestamps) > 1:
        span_seconds = max((max(timestamps) - min(timestamps)).total_seconds(), 60.0)
        req_per_min = round(total_requests / (span_seconds / 60.0), 2)
    else:
        req_per_min = float(total_requests)

    # 3. Errors Panel
    total_received_count = max(total_requests, 1)
    error_count = len(req_failed)
    error_rate_pct = round((error_count / total_received_count) * 100, 2)
    tool_events = [r for r in records if "tool_success" in r and r.get("tool_success") is not None]
    tool_successes = [r for r in tool_events if r.get("tool_success") is True]
    tool_success_rate = (
        round((len(tool_successes) / len(tool_events)) * 100, 2) if tool_events else 100.0
    )

    # 4. Cost Panel
    costs = [r["cost_usd"] for r in resp_sent if "cost_usd" in r]
    total_cost = round(sum(costs), 6)

    # 5. Tokens Panel
    tokens_in = sum(r.get("tokens_in", 0) for r in resp_sent)
    tokens_out = sum(r.get("tokens_out", 0) for r in resp_sent)
    total_tokens = tokens_in + tokens_out

    # 6. Quality Panel
    qualities = [r["quality_score"] for r in resp_sent if "quality_score" in r]
    mean_quality = round(sum(qualities) / len(qualities), 3) if qualities else 0.0

    print("=" * 60)
    print("      K4-L3B Day 13 Monitoring & LLMOps Dashboard Summary")
    print("=" * 60)
    print(f"Time range: Last 60m | Source: {LOG_PATH} ({len(records)} records)")
    print("-" * 60)
    print(f"[Panel 1: Latency]       P50={p50_lat}ms, P95={p95_lat}ms, P99={p99_lat}ms | TTFT P95={p95_ttft}ms (Threshold: <= 3000ms) -> {'PASS' if p95_lat <= 3000 else 'ALERT'}")
    print(f"[Panel 2: Traffic]       Total={total_requests} requests | Rate={req_per_min} req/min (Threshold: >= 1 rpm) -> {'PASS' if req_per_min >= 1 else 'ALERT'}")
    print(f"[Panel 3: Errors]        Error rate={error_rate_pct}% | Retrieval success={tool_success_rate}% (Threshold: <= 2%) -> {'PASS' if error_rate_pct <= 2 else 'ALERT'}")
    print(f"[Panel 4: Cost]          Total cost=${total_cost:.6f} USD (Threshold: <= $2.50) -> {'PASS' if total_cost <= 2.5 else 'ALERT'}")
    print(f"[Panel 5: Tokens]        Tokens in={tokens_in:,}, out={tokens_out:,}, total={total_tokens:,} (Threshold: <= 50,000) -> {'PASS' if total_tokens <= 50000 else 'ALERT'}")
    print(f"[Panel 6: Quality]       Mean quality={mean_quality:.2f} (Threshold: >= 0.75) -> {'PASS' if mean_quality >= 0.75 else 'ALERT'}")
    print("=" * 60)

    # Export Standalone HTML Dashboard
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    html_path = EVIDENCE_DIR / "dashboard.html"

    # Prepare time-series points
    points = []
    for r in resp_sent:
        ts = r.get("ts", "")
        points.append({
            "ts": ts[-13:-1] if len(ts) >= 13 else ts,
            "latency": r.get("latency_ms", 0),
            "ttft": r.get("ttft_ms", 0),
            "cost": r.get("cost_usd", 0.0),
            "tokens_in": r.get("tokens_in", 0),
            "tokens_out": r.get("tokens_out", 0),
            "quality": r.get("quality_score", 0.0),
        })

    labels_json = json.dumps([p["ts"] for p in points])
    lat_json = json.dumps([p["latency"] for p in points])
    ttft_json = json.dumps([p["ttft"] for p in points])
    cost_json = json.dumps([p["cost"] for p in points])
    t_in_json = json.dumps([p["tokens_in"] for p in points])
    t_out_json = json.dumps([p["tokens_out"] for p in points])
    qual_json = json.dumps([p["quality"] for p in points])

    p95_is_alert = p95_lat > 3000
    latency_badge_class = "stat-badge alert" if p95_is_alert else "stat-badge"
    latency_status_text = "ALERT" if p95_is_alert else "PASS"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #09090b; color: #f4f4f5; margin: 0; padding: 24px; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #27272a; padding-bottom: 16px; margin-bottom: 24px; }}
    .header h1 {{ font-size: 22px; font-weight: 600; margin: 0; color: #ffffff; letter-spacing: -0.3px; }}
    .meta {{ font-size: 13px; color: #a1a1aa; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
    .card {{ background: #121215; border-radius: 10px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); border: 1px solid #27272a; }}
    .card-title {{ font-size: 15px; font-weight: 600; margin-bottom: 4px; color: #f4f4f5; display: flex; justify-content: space-between; align-items: center; }}
    .card-sub {{ font-size: 12px; color: #71717a; margin-bottom: 14px; }}
    .stat-badge {{ font-size: 12px; padding: 3px 10px; border-radius: 6px; background: #18181b; color: #d4d4d8; border: 1px solid #2e2e33; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    .stat-badge.alert {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.4); }}
    .status-healthy {{ color: #22c55e; background: #14291e; border: 1px solid #166534; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 500; }}
    .status-alert {{ color: #ef4444; background: #2b1515; border: 1px solid #7f1d1d; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 500; }}
    canvas {{ max-height: 220px; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</h1>
      <div class="meta">Service: day13-l3b-monitoring-llmops-lab | Time range: Last 60m | Refresh: 30s | Source: data/logs.jsonl</div>
    </div>
    <div class="meta">
      Total Requests: <strong style="color:#ffffff;">{total_requests}</strong> &nbsp;|&nbsp; Status: <span class="{'status-alert' if p95_is_alert else 'status-healthy'}">{'ANOMALY DETECTED' if p95_is_alert else 'HEALTHY (6/6 Panels Active)'}</span>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="card">
      <div class="card-title">
        <span>1. Latency percentiles and TTFT (Unit: ms)</span>
        <span class="{latency_badge_class}">P50: {p50_lat}ms | P95: {p95_lat}ms ({latency_status_text}) | Threshold: 3000ms</span>
      </div>
      <div class="card-sub">Event: response_sent | P95 TTFT: {p95_ttft}ms</div>
      <canvas id="latencyChart"></canvas>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="card">
      <div class="card-title">
        <span>2. Request traffic (Unit: requests_per_minute)</span>
        <span class="stat-badge">{req_per_min} req/min | Threshold: &gt;= 1 rpm</span>
      </div>
      <div class="card-sub">Event: request_received | Total requests in window: {total_requests}</div>
      <canvas id="trafficChart"></canvas>
    </div>

    <!-- Panel 3: Errors -->
    <div class="card">
      <div class="card-title">
        <span>3. Error rate and retrieval success (Unit: percent)</span>
        <span class="stat-badge">Error: {error_rate_pct}% | Retrieval: {tool_success_rate}% | Threshold: &lt;= 2%</span>
      </div>
      <div class="card-sub">Events: request_received, request_failed | Failures: {error_count}</div>
      <canvas id="errorChart"></canvas>
    </div>

    <!-- Panel 4: Cost -->
    <div class="card">
      <div class="card-title">
        <span>4. Cost over time (Unit: usd)</span>
        <span class="stat-badge">Total: ${total_cost:.6f} USD | Threshold: &lt;= $2.50</span>
      </div>
      <div class="card-sub">Event: response_sent | Aggregation: sum(cost_usd)</div>
      <canvas id="costChart"></canvas>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="card">
      <div class="card-title">
        <span>5. Input and output tokens (Unit: tokens)</span>
        <span class="stat-badge">In: {tokens_in:,} | Out: {tokens_out:,} | Threshold: &lt;= 50,000</span>
      </div>
      <div class="card-sub">Event: response_sent | Total: {total_tokens:,} tokens</div>
      <canvas id="tokenChart"></canvas>
    </div>

    <!-- Panel 6: Quality -->
    <div class="card">
      <div class="card-title">
        <span>6. Quality proxy (Unit: score_0_to_1)</span>
        <span class="stat-badge">Mean: {mean_quality:.2f} | Threshold: &gt;= 0.75</span>
      </div>
      <div class="card-sub">Event: response_sent | Metric: heuristic_quality</div>
      <canvas id="qualityChart"></canvas>
    </div>
  </div>

  <script>
    Chart.defaults.color = '#a1a1aa';
    Chart.defaults.borderColor = '#222226';
    if (Chart.defaults.scale && Chart.defaults.scale.grid) {{
      Chart.defaults.scale.grid.color = '#1c1c20';
    }}

    const labels = {labels_json};

    // 1. Latency (White line + Rose TTFT + Red alert threshold)
    new Chart(document.getElementById('latencyChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{ label: 'Latency (ms)', data: {lat_json}, borderColor: '#f4f4f5', backgroundColor: 'rgba(255,255,255,0.05)', fill: true, tension: 0.2, borderWidth: 2, pointRadius: 2 }},
          {{ label: 'TTFT (ms)', data: {ttft_json}, borderColor: '#fb7185', borderDash: [4, 4], tension: 0.2, borderWidth: 1.8, pointRadius: 0 }}
        ]
      }},
      options: {{
        plugins: {{
          annotation: {{
            annotations: {{
              line1: {{ type: 'line', yMin: 3000, yMax: 3000, borderColor: '#ef4444', borderWidth: 2, label: {{ content: 'SLO Threshold: 3000ms', display: true, position: 'end', color: '#f87171', backgroundColor: 'rgba(24,24,27,0.85)' }} }}
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1c1c20' }} }},
          y: {{ beginAtZero: true, suggestedMax: 3500, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});

    // 2. Traffic (Warm Amber Yellow bars)
    new Chart(document.getElementById('trafficChart'), {{
      type: 'bar',
      data: {{
        labels: labels,
        datasets: [{{ label: 'Requests per request point', data: labels.map(() => 1), backgroundColor: '#fbbf24', borderRadius: 3 }}]
      }},
      options: {{
        plugins: {{
          annotation: {{
            annotations: {{
              line1: {{ type: 'line', yMin: 1, yMax: 1, borderColor: '#71717a', borderWidth: 1.5, borderDash: [3, 3], label: {{ content: 'Threshold: 1 req/min', display: true, position: 'end', color: '#a1a1aa', backgroundColor: 'rgba(24,24,27,0.85)' }} }}
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1c1c20' }} }},
          y: {{ beginAtZero: true, suggestedMax: 5, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});

    // 3. Errors (Rose/Red error + Emerald green retrieval)
    new Chart(document.getElementById('errorChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{ label: 'Error Rate (%)', data: labels.map(() => {error_rate_pct}), borderColor: '#f43f5e', backgroundColor: 'rgba(244,63,94,0.12)', fill: true, borderWidth: 2, pointRadius: 2 }},
          {{ label: 'Retrieval Success (%)', data: labels.map(() => {tool_success_rate}), borderColor: '#10b981', borderWidth: 2, pointRadius: 0 }}
        ]
      }},
      options: {{
        plugins: {{
          annotation: {{
            annotations: {{
              line1: {{ type: 'line', yMin: 2, yMax: 2, borderColor: '#ef4444', borderWidth: 1.5, borderDash: [4, 4], label: {{ content: 'Threshold: 2%', display: true, position: 'end', color: '#f87171', backgroundColor: 'rgba(24,24,27,0.85)' }} }}
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1c1c20' }} }},
          y: {{ beginAtZero: true, max: 100, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});

    // 4. Cost (Golden Yellow line with soft glow)
    new Chart(document.getElementById('costChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{ label: 'Cost USD', data: {cost_json}, borderColor: '#facc15', fill: true, backgroundColor: 'rgba(250,204,21,0.1)', tension: 0.2, borderWidth: 2, pointRadius: 2 }}]
      }},
      options: {{
        plugins: {{
          annotation: {{
            annotations: {{
              line1: {{ type: 'line', yMin: 2.5, yMax: 2.5, borderColor: '#71717a', borderWidth: 1.5, borderDash: [4, 4], label: {{ content: 'Threshold: $2.50', display: true, position: 'end', color: '#a1a1aa', backgroundColor: 'rgba(24,24,27,0.85)' }} }}
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1c1c20' }} }},
          y: {{ beginAtZero: true, suggestedMax: 0.005, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});

    // 5. Tokens (Pastel Pink in + Hot Pink out)
    new Chart(document.getElementById('tokenChart'), {{
      type: 'bar',
      data: {{
        labels: labels,
        datasets: [
          {{ label: 'Tokens In', data: {t_in_json}, backgroundColor: '#fbcfe8', borderRadius: 3 }},
          {{ label: 'Tokens Out', data: {t_out_json}, backgroundColor: '#ec4899', borderRadius: 3 }}
        ]
      }},
      options: {{
        scales: {{
          x: {{ stacked: true, grid: {{ color: '#1c1c20' }} }},
          y: {{ stacked: true, suggestedMax: 500, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});

    // 6. Quality (Emerald Green line with soft fill)
    new Chart(document.getElementById('qualityChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{ label: 'Quality Score', data: {qual_json}, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: true, tension: 0.2, borderWidth: 2, pointRadius: 2 }}]
      }},
      options: {{
        plugins: {{
          annotation: {{
            annotations: {{
              line1: {{ type: 'line', yMin: 0.75, yMax: 0.75, borderColor: '#fbbf24', borderWidth: 1.5, borderDash: [4, 4], label: {{ content: 'Threshold: 0.75', display: true, position: 'end', color: '#fbbf24', backgroundColor: 'rgba(24,24,27,0.85)' }} }}
            }}
          }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1c1c20' }} }},
          y: {{ min: 0.0, max: 1.0, grid: {{ color: '#1c1c20' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

    html_path.write_text(html_content, encoding="utf-8")
    print(f"\nHTML Dashboard rendered to: {html_path}")


if __name__ == "__main__":
    main()
