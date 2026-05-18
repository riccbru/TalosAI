<a id="auth-top"></a>

<p align="left">
  <a href="./index.md">← API Reference</a> 
</p>

# Auth API
#### Base Path: `/talos/api/auth`
The Auth API endpoints manage user identity and session lifecycle.

These endpoints allow users to securely register, authenticate, and maintain persistent access via token rotation.

## Table of Contents
- [`POST /signup`](#post-signup)
- [`POST /signin`](#post-signin)
- [`POST /refresh`](#post-refresh)
- [`POST /signout`](#post-signout)

## POST /signup
Creates a new user account. 

### Request
- #### Body
	```json
	{
		"email": "mail@domain.tld",
		"password": "Password123!"
	}
	```

	| Field      | Type   | Required | Description                  |
	|------------|:------:|:--------:|------------------------------|
	| `email`    | string | Yes      | Valid email address			|
	| `password` | string | Yes      | Password (minimum length: 8) |

### Response
- **`201 Created`**
	```json
	{
		"role": "admin",
		"is_active": true,
		"email": "mail@domain.tld",
		"created_at": "1970-01-01T00:00:00.000000+00:00",
		"updated_at": "1970-01-01T00:00:00.000000+00:00",
		"uid": "ffffffff-ffff-4fff-8fff-ffffffffffff"
	}
	```

	| Field        | Type    | Description                                  |
	|--------------|:-------:|----------------------------------------------|
	| `role`       | string  | Possible roles: `admin`, `auditor`, `user`   |
	| `is_active`  | boolean | Set to true if the user is active else false |
	| `email`      | string  | User's email address                         |
	| `created_at` | string  | Creation date in ISO 8601 (UTC)              |
	| `updated_at` | string  | Last update in ISO 8601 (UTC)                |
	| `uid`        | UUIDv4  | Universally Unique IDentifier                |

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/auth/signup' \
        -H 'Content-Type: application/json' \
        -d '{ "email": "mail@domain.tld", "password": "Password123!" }' | jq
```

<p align="right">(<a href="#auth-top">back to top ↑</a>)</p>


## POST /signin
Authenticates the user and starts a session setting a refresh_token cookie (Secure; HttpOnly; SameSite=Strict).

### Request
- #### Body
	```json
	{
		"email": "mail@domain.tld",
		"password": "Password123!"
	}
	```

	| Field      | Type   | Required | Description                  |
	|------------|:------:|:--------:|------------------------------|
	| `email`    | string | Yes      | Valid email address			|
	| `password` | string | Yes      | Password (minimum length: 8) |

### Response
- **`200 OK`**:
	```json
	{
		"status": "success",
		"access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJtZXNzYWdlIjoiSGVsbG8sIHdvcmxkIn0.P6yfApX7GyU6ajUiKhZJj2q3hqsOoMAEO31rC92n3VM",
		"user": {
		    "role": "admin",
		    "is_active": true,
		    "email": "mail@domain.tld",
		    "created_at": "1970-01-01T00:00:00.000000+00:00",
		    "updated_at": "1970-01-01T00:00:00.000000+00:00",
		    "uid": "ffffffff-ffff-4fff-8fff-ffffffffffff"
	    }
	}
	```

	| Field           | Type    | Description                                  |
	|-----------------|---------|----------------------------------------------|
	| status          | string  | Set to `success` if everything OK            |
	| access_token    | string  | JSON Web Token                               |
	| user            | object  | Full info of the logging user                |

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/auth/signup' \
        -H 'Content-Type: application/json' \
        -d '{ "email": "mail@domain.tld", "password": "Password123!" }' | jq
```

<p align="right">(<a href="#auth-top">back to top ↑</a>)</p>


## POST /refresh
Generates a new access token using the refresh token stored in the cookies. Implements token rotation.

### Response
- **`200 OK`**:

	Same as [signin endpoint](#post-signin)

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/auth/refresh' \
     -b 'refresh_token=REFRESH_TOKEN' | jq
```

<p align="right">(<a href="#auth-top">back to top ↑</a>)</p>


## POST /signout
Invalidates the current session in the database and removes the refresh cookie.

### Response
- **`204 No Content`**:

	Empty body response

### Example
```bash
curl -s -X 'POST' 'http://localhost:8000/talos/api/auth/signout' \
     -H 'Authorization: Bearer ACCESS_TOKEN' | jq
```

<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="./index.md">← API Reference</a>
  <div>
	(<a href="#auth-top">back to top ↑</a>)
  </div>
</div>