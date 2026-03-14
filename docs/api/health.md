<a id="health-top"></a>

# Health API
The Health API endpoints provide real-time status updates for the TalosAI infrastructure.
These endpoints allow the system to verify that the core services are operational before initiating complex agent workflows.
These endpoints do not require authentication to check system viability.

## Base Path: `/talos/api/v1/health`

## Table of Contents
- [`GET /`](#get-)
- [`GET /db`](#get-db)
- [`GET /ollama`](#get-ollama)

## GET /
Returns the current status of the service. Does not require authentication.

```bash
curl -s http://localhost:8000/talos/api/v1/health | jq
```

**Response** `200 OK`
```json
{
  "status": "up",
  "timestamp": "1970-01-01T00:00:00.000000+00:00",
  "uptime_seconds": 0,
  "response_time_ms": 0,
  "system": {
    "os": "Linux",
    "os_release": "0.0.0-linux",
    "os_version": "#1",
    "architecture": "arch",
    "hostname": "linux",
    "python_version": "0.0.0"
  },
  "cpu": {
    "usage_percent": 0.0,
    "load_avg": [
      0.0,
      0.0,
      0.0 
    ]
  },
  "memory": {
    "used_percent": 0,
    "available_gb": 0
  },
  "disk": {
    "free_gb": 0,
    "used_percent": 0
  },
  "gpu": [
    {
      "id": 0,
      "name": "NVIDIA GeForce RTX [MODEL]",
      "memory_used_gb": 0,
      "memory_total_gb": 0,
      "load_percent": 0
    }
  ],
  "warnings": []
}
```

**Response fields**
| Field                 | Type          | Description                                   |
|-----------------------|---------------|-----------------------------------------------|
| status                | string        | Service status, always `up` when healthy      |
| timestamp             | string        | ISO 8601 timestamp of the response            |
| uptime_seconds        | integer       | Seconds elapsed since the service started     |
| response_time_ms      | integer       | Time taken to process the health check in ms  |
| system                | object        | Host machine information                      |
| system.os             | string        | Operating system name                         |
| system.os_release     | string        | OS release identifier                         |
| system.os_version     | string        | OS version string                             |
| system.architecture   | string        | CPU architecture                              |
| system.hostname       | string        | Machine hostname                              |
| system.python_version | string        | Python runtime version                        |
| cpu                   | object        | CPU usage metrics                             |
| cpu.usage_percent     | float         | Current overall CPU usage percentage          |
| cpu.load_avg          | array[float]  | Load averages over 1, 5, and 15 minutes       |
| memory                | object        | Memory usage metrics                          |
| memory.used_percent   | integer       | Percentage of memory currently in use         |
| memory.available_gb   | integer       | Available memory in gigabytes                 |
| disk                  | object        | Disk usage metrics                            |
| disk.free_gb          | integer       | Free disk space in gigabytes                  |
| disk.used_percent     | integer       | Percentage of disk space currently in use     |
| gpu                   | array[object] | List of detected GPUs, empty if none present  |
| gpu[].id              | integer       | GPU device index                              |
| gpu[].name            | string        | GPU model name                                |
| gpu[].memory_used_gb  | integer       | GPU memory currently in use in gigabytes      |
| gpu[].memory_total_gb | integer       | Total GPU memory in gigabytes                 |
| gpu[].load_percent    | integer       | Current GPU load percentage                   |
| warnings              | array[string] | List of non-critical warning messages, if any |

<p align="right">(<a href="#health-top">back to top</a>)</p>

## GET /db
Returns the current status of the Database. Does not require authentication.

```bash
curl -s http://localhost:8000/talos/api/v1/health/db | jq
```

**Response** `200 OK`
```json
{
  "timestamp": "1970-01-01T00:00:00.000000+00:00",
  "status": "up",
  "connection": {
    "state": "connected",
    "latency_ms": 0.0
  },
  "version": "PostgreSQL 0.0",
  "pool": {
    "size": 10,
    "checkedin": 0,
    "checkedout": 1,
    "overflow": -9
  },
  "warnings": []
}
```

**Response fields**
| Field                 | Type          | Description                                             |
|-----------------------|---------------|---------------------------------------------------------|
| timestamp             | string        | ISO 8601 timestamp of the response                      |
| status                | string        | Database status, always `up` when healthy               |
| connection            | object        | Database connection details                             |
| connection.state      | string        | Connection state, always `connected` when healthy       |
| connection.latency_ms | float         | Round-trip query latency in milliseconds                |
| version               | string        | PostgreSQL server version string                        |
| pool                  | object        | Connection pool metrics                                 |
| pool.size             | integer       | Total number of connections in the pool                 |
| pool.checkedin        | integer       | Connections currently idle in the pool                  |
| pool.checkedout       | integer       | Connections currently in use by the application         |
| pool.overflow         | integer       | Connections opened beyond pool size, negative if unused |
| warnings              | array[string] | List of non-critical warning messages, if any           |

<p align="right">(<a href="#health-top">back to top</a>)</p>

## GET /ollama
Returns the current status of Ollama service. Does not require authentication.

```bash
curl -s http://localhost:8000/talos/api/v1/health/ollama | jq
```

**Response** `200 OK`
```json
{
  "status": "up",
  "latency_ms": 0.0,
  "summary": {
    "total_installed": 1,
    "currently_active": 0
  },
  "active_models": {
    "models": []
  },
  "library": {
    "models": [
      {
        "model": "model-0B:latest",
        "modified_at": "1970-01-01T00:00:00.000000+00:00",
        "digest": "0000000000000000000000000000000000000000000000000000000000000000",
        "size": 0,
        "details": {
          "parent_model": "",
          "format": "gguf",
          "family": "llama",
          "families": [
            "llama"
          ],
          "parameter_size": "0.0B",
          "quantization_level": "Q4_K_M"
        }
      }
    ]
  }
}
```

**Response fields**
| Field                                       | Type          | Description                                         |
|---------------------------------------------|---------------|-----------------------------------------------------|
| status                                      | string        | Service status, always `up` when healthy            |
| latency_ms                                  | float         | Round-trip request latency in milliseconds          |
| summary                                     | object        | High-level overview of available models             |
| summary.total_installed                     | integer       | Total number of models installed in the library     |
| summary.currently_active                    | integer       | Number of models currently loaded and running       |
| active_models                               | object        | Details about currently running models              |
| active_models.models                        | array[object] | List of active model entries, empty if none running |
| library                                     | object        | Full list of installed models                       |
| library.models                              | array[object] | List of installed model entries                     |
| library.models[].model                      | string        | Model identifier including tag                      |
| library.models[].modified_at                | string        | ISO 8601 timestamp of the last modification         |
| library.models[].digest                     | string        | SHA-256 digest of the model file                    |
| library.models[].size                       | integer       | Model file size in bytes                            |
| library.models[].details                    | object        | Additional metadata about the model                 |
| library.models[].details.parent_model       | string        | Parent model identifier, empty if none              |
| library.models[].details.format             | string        | Model file format                                   |
| library.models[].details.family             | string        | Primary model architecture family                   |
| library.models[].details.families           | array[string] | All architecture families the model belongs to      |
| library.models[].details.parameter_size     | string        | Number of model parameters                          |
| library.models[].details.quantization_level | string        | Quantization method applied to the model            |

<p align="right">(<a href="#health-top">back to top</a>)</p>