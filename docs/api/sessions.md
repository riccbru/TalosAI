<a id="sessions-top"></a>

# Sessions API
#### Base Path: `/talos/api/sessions`
The Sessions API endpoints allow users to view and manage their active and expired authentication sessions.

These endpoints are essential for security auditing, allowing clients to track login devices, IP addresses, and revoke compromised tokens.

## Table of Contents
- [`GET /`](#get-)
- [`GET /:session_uid`](#get-session_uid)
- [`DELETE /`](#delete-)
- [`DELETE /:session_uid`](#delete-session_uid)

## GET /
Retrieves a list of all sessions associated with the authenticated user. This list includes active, expired, and explicitly revoked sessions, sorted by the most recent activity.

### Request Parameters
| Parameter     | Location | Type    | Required | Description                           |
|---------------|:--------:|:-------:|:--------:|---------------------------------------|
| `session_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the sessions |

### Example
```bash
curl -s 'http://localhost:8000/talos/api/sessions' \
     -H 'Authorization: Bearer ACCESS_TOKEN' | jq
```

**Response** `200 OK`
```json
{
	"sessions": [
    {
      "is_revoked": false,
      "ip_address": "255.255.255.255",
      "user_agent": "user/0.0.0",
      "expires_at": "1970-01-01T00:00:00.000000Z",
      "last_active": "1970-01-01T00:00:00.000000Z",
      "created_at": "1970-01-01T00:00:00.000000Z",
      "session_uid": "ffffffff-ffff-4fff-8fff-ffffffffffff"
    },
    {
      "is_revoked": true,
      "ip_address": "255.255.255.255",
      "user_agent": "user/0.0.0",
      "expires_at": "1970-01-01T00:00:00.000000Z",
      "last_active": "1970-01-01T00:00:00.000000Z",
      "created_at": "1970-01-01T00:00:00.000000Z",
      "session_uid": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    }
  ]
}
```

**Response fields**
| Field       | Type        | Description                                                            |
|-------------|:-----------:|------------------------------------------------------------------------|
| is_revoked  | boolean     | Indicates whether the session has been manually revoked                |
| ip_address  | string      | The last known IP address used by this session (IPv4 or IPv6)          |
| user_agent  | string      | The browser or client application identifier used to log in            |
| expires_at  | timestamp   | ISO 8601 UTC expiration date of the refresh token                      |
| last_active | timestamp   | ISO 8601 UTC timestamp of the last API request made using this session |
| created_at  | timestamp   | ISO 8601 UTC timestamp when the session was originally created         |
| session_uid | UUIDv4      | Universally Unique IDentifier of the session                           |


<p align="right">(<a href="#sessions-top">Back to top ↑</a>)</p>



## GET /:session_uid
Retrieves the detailed information of a specific session by its unique identifier. This endpoint is useful for inspecting the detailed metadata of a single login connection.

### Request Parameters
| Parameter     | Location | Type    | Required | Description                           |
|---------------|:--------:|:-------:|:--------:|---------------------------------------|
| `session_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the sessions |

### Example
```bash
curl -s 'http://localhost:8000/talos/api/sessions/:session_uid' \
     -H 'Authorization: Bearer ACCESS_TOKEN' | jq
```

**Response** `200 OK`
```json
{
  "is_revoked": false,
  "ip_address": "255.255.255.255",
  "user_agent": "user/0.0.0",
  "expires_at": "1970-01-01T00:00:00.000000Z",
  "last_active": "1970-01-01T00:00:00.000000Z",
  "created_at": "1970-01-01T00:00:00.000000Z"
}
```

**Response** `404 Not Found`
```json
{
  "detail": "Session not found"
}
```

<p align="right">(<a href="#sessions-top">Back to top ↑</a>)</p>



## DELETE /
Revokes all active sessions belonging to the authenticated user. This immediately invalidates all associated refresh tokens across all devices.

### Example
```bash
curl -s -i -X 'DELETE' 'http://localhost:8000/talos/api/sessions' \
     -H 'Authorization: Bearer ACCESS_TOKEN'
```

**Response** `204 No Content`

<p align="right">(<a href="#sessions-top">Back to top ↑</a>)</p>

## DELETE /:session_uid
Manually revokes a specific session using its unique identifier. Once revoked, the associated refresh token becomes invalid immediately, forcing the client to re-authenticate.

### Request Parameters
| Parameter     | Location | Type    | Required | Description                           |
|---------------|:--------:|:-------:|:--------:|---------------------------------------|
| `session_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the sessions |

### Example
```bash
curl -s -X 'DELETE' 'http://localhost:8000/talos/api/sessions/:session_uid' \
     -H 'Authorization: Bearer ACCESS_TOKEN' | jq
```

**Response** `200 OK`
```json
{
  "is_revoked": true,
  "ip_address": "255.255.255.255",
  "user_agent": "user/0.0.0",
  "expires_at": "1970-01-01T00:00:00.000000Z",
  "last_active": "1970-01-01T00:00:00.000000Z",
  "created_at": "1970-01-01T00:00:00.000000Z"
}
```

<p align="right">
  <a href="index.md">← Back to API Index</a> 
  | 
  <a href="#sessions-top">Back to top ↑</a>
</p>