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

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/missions/hybrid' \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ACCESS_TOKEN" \
     -d '{"target": "255.255.255.255", "prompt": "Identify open ports and look for vulnerable services"}' | jq
```


<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="./index.md">← API Reference</a>
  <div>
     (<a href="#missions-top">back to top ↑</a>)
  </div>
</div>