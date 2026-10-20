<a id="index-top"></a>

<p align="left">
  <a href="../README.md">← README</a> 
</p>

# `Documentation`

## Overview & Vision

**TalosAI** is an **agentic penetration-testing platform** that autonomously
drives real security tooling inside a sandboxed Kali Linux container and
validates every finding against observed execution evidence.

Unlike free-form agents, TalosAI's **Orchestrator V2** implements a
**deterministic, iterative (ReAct-style) loop** under a manager/executor
paradigm: a cloud reasoning model (Google Gemini) acts as *Lead Pentester* and
decides the next action, while a local non-LLM executor runs each command
verbatim through the Docker Engine API. The loop is **bounded** (a fixed
per-port attempt budget guarantees termination) and **knowledge-guided**
(high-confidence exploit modules are tried deterministically before any model
call). The result is a system that is reproducible, observable in real time, and
economical with LLM usage.

Design pillars:

- **Deterministic control flow** — bounded attempts, no unbounded recursion.
- **Exploit-First + Short-Circuit** — known vulnerabilities are confirmed with
  *zero* LLM calls where possible (see [Architecture §4](./arch.md#4-exploit-first--short-circuit)).
- **Evidence-based validation** — a finding is `confirmed` only on hard proof
  such as `uid=0(root)` (see [Architecture §5](./arch.md#5-the-validation-layer-evidence-confirmation)).
- **Full observability & FinOps** — durable persistence, a live WebSocket
  stream, and provider-agnostic per-agent token/latency accounting.

## [`Architecture`](./arch.md)
Detailed breakdown of the Multi-Agent System architecture: execution decoupling
(FastAPI ⇄ async worker thread ⇄ WebSocket), the Orchestrator V2 loop, the
Exploit-First + Short-Circuit strategy, the Validation Layer, and universal usage
tracking.

## [`API Reference`](./api/index.md)
This section provides the technical specifications breakdown of all REST endpoints.

The API is built with FastAPI and follows RESTful principles, utilizing JSON for data exchange.

Once the server is running, you can access the interactive Swagger UI at [http://localhost:8000/talos/docs](http://localhost:8000/talos/docs)

---

## Key Capabilities & Empirical Results

> ⚠️ **Data to populate** — the figures in this section must be filled from the
> latest real mission export (`last_hybrid_mission_results.json`). Placeholders are
> written as `‹…›` so they are never mistaken for measured values. The *columns
> and structure* below are final and match the live API schema.

### Deterministic validation outcome

Against a reference *metasploitable* target, the mission produced the following
confirmed compromises (each backed by real execution proof — `uid=0(root)` or a
service-account identity returned by the `whoami; id; uname -a` proof clause):

| Metric | Value |
|--------|------:|
| Services discovered | `‹N›` |
| Ports investigated | `‹N›` |
| **Vulnerabilities confirmed (with execution proof)** | **`‹N›`** |
| Unconfirmed / rejected attempts | `‹N›` |

### Execution time vs. LLM latency

A key efficiency indicator is the gap between **total mission wall-clock** and the
time actually spent **waiting on model responses** (network + generation): the
remainder is real tool execution (scanning, exploitation) inside Kali.

| Metric | Value | Source field |
|--------|------:|--------------|
| Total mission duration | `‹hh:mm:ss›` | `metrics.duration` |
| Total duration (seconds) | `‹s›` | `metrics.duration_seconds` |
| Aggregate LLM latency | `‹s›` | `metrics.total_latency_seconds` |
| Total LLM calls | `‹N›` | `metrics.total_llm_calls` |
| **LLM latency share** | `‹latency / duration %›` | derived |

### Models used & token accounting (FinOps)

Per-agent breakdown of token usage, accumulated across the mission and split by
role (`scanner` = Nmap parsing, `manager` = attack decisioning):

| Agent | Model | Provider | Prompt | Completion | Total | Calls | Latency (s) |
|-------|-------|----------|-------:|-----------:|------:|------:|------------:|
| scanner | `‹model›` | `‹provider›` | `‹…›` | `‹…›` | `‹…›` | `‹…›` | `‹…›` |
| manager | `‹model›` | `‹provider›` | `‹…›` | `‹…›` | `‹…›` | `‹…›` | `‹…›` |
| **Total** | — | — | **`‹…›`** | **`‹…›`** | **`‹…›`** | **`‹…›`** | **`‹…›`** |

### Scanned ports & services

| Port | Service | Version | Status | Attempts | Confirmed |
|-----:|---------|---------|--------|---------:|:---------:|
| `‹21›` | `‹ftp›` | `‹vsftpd 2.3.4›` | `‹completed›` | `‹…›` | `‹yes / no›` |
| … | … | … | … | … | … |

---

> **API response schemas** — the full JSON returned by the mission endpoints
> (mission record, ports, findings with execution proof, per-agent `models` and
> aggregated `metrics`), plus the live WebSocket events, is documented in
> [API Reference → Missions](./api/missions.md).

<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="../README.md">← README</a>
  <div>
    (<a href="#index-top">back to top ↑</a>)
  </div>
</div>
