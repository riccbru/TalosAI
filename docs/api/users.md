<a id="users-top"></a>

<p align="left">
  <a href="./index.md">← API Reference</a> 
</p>

# Users API
#### Base Path: `/talos/api/users`
The Users API endpoints allow administrators to manage platform accounts, view user profiles, and monitor account statuses.

## Table of Contents
- [`GET /`](#get-)
- [`GET /:user_uid`](#get-user_uid)
- [`GET /:user_uid/sessions`](#get-user_uidsessions)
- [`PATCH /:user_uid`](#patch-user_uid)
- [`GET /profile`](#get-profile)
- [`PATCH /password`](#patch-password)

## GET /
Retrieves a list of all registered users in the platform. This endpoint supports administrative monitoring and user management.
> **Authorization**: Endpoints in this section require a valid Bearer Token with administrative privileges (`role: admin`) unless specified otherwise.

### Request
- #### Parameters
| Parameter | Location | Type    | Required | Description                          |
|-----------|:--------:|:-------:|:--------:|--------------------------------------|
| `active`  | Query    | boolean | No       | Filters users by status (true/false) |
| `search`  | Query    | boolean | No       | Filters users by email               |

### Response
- **`200 OK`**:
  ```json
  {
  	"users": [
      {
        "role": "admin",
        "is_active": true,
        "email": "admin@domain.tld",
        "created_at": "1970-01-01T00:00:00.000000Z",
        "updated_at": "1970-01-01T00:00:00.000000Z",
        "user_uid": "ffffffff-ffff-4fff-8fff-ffffffffffff"
      },
      {
        "role": "user",
        "is_active": true,
        "email": "user@domain.tld",
        "created_at": "1970-01-01T00:00:00.000000Z",
        "updated_at": "1970-01-01T00:00:00.000000Z",
        "user_uid": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
      }
    ]
  }
  ```

  | Field        | Type      | Description                                                        |
  |--------------|:---------:|--------------------------------------------------------------------|
  | `role`       | string    | The access control role assigned to the user                       |
  | `is_active`  | boolean   | Status flag indicating if the account is active or suspended       |
  | `email`      | string    | The primary email address and login identifier of the user         |
  | `created_at` | timestamp | ISO 8601 UTC timestamp when the user account was created           |
  | `updated_at` | timestamp | ISO 8601 UTC timestamp of the last modification to the user record |
  | `user_uid`   | UUIDv4    | Universally Unique IDentifier of the user                          |

### Example
```bash
curl -s 'http://localhost:8000/talos/api/users?active=&search=' \
     -H 'Authorization: Bearer ADMIN_TOKEN' | jq
```

<p align="right">(<a href="#users-top">back to top ↑</a>)</p>


## GET /:user_uid
Retrieves the detailed profile information of a specific user by their unique identifier.
> **Authorization**: Endpoints in this section require a valid Bearer Token with administrative privileges (`role: admin`) unless specified otherwise.

### Request
- #### Parameters
  | Parameter  | Location | Type    | Required | Description                       |
  |------------|:--------:|:-------:|:--------:|-----------------------------------|
  | `user_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the user |
  

### Response
- **`200 OK`**:
  ```json
  {
    "role": "user",
    "is_active": true,
    "email": "user@domain.tld",
    "created_at": "1970-01-01T00:00:00.000000Z",
    "updated_at": "1970-01-01T00:00:00.000000Z",
    "user_uid": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  }
  ```

- **`404 Not Found`**:
  ```json
  {
    "detail": "User not found"
  }
  ```

### Example
```bash
curl -s 'http://localhost:8000/talos/api/users/:user_uid' \
     -H 'Authorization: Bearer ADMIN_TOKEN' | jq
```

<p align="right">(<a href="#users-top">back to top ↑</a>)</p>


## GET /:user_uid/sessions
Retrieves a list of all active, expired, or revoked sessions belonging to a specific user.

This endpoint allows administrators to audit login history and monitor active connections for any given account.
> **Authorization**: Endpoints in this section require a valid Bearer Token with administrative privileges (`role: admin`) unless specified otherwise.

### Request
- #### Parameters

  | Parameter  | Location | Type    | Required | Description                             |
  |------------|:--------:|:-------:|:--------:|-----------------------------------------|
  | `user_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the user       |
  | `revoked`  | Query    | boolean | No       | Filters sessions by status (true/false) |

### Response
- **`200 OK`**:
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

### Example
```bash
curl -s 'http://localhost:8000/talos/api/users/:user_uid/sessions' \
     -H 'Authorization: Bearer ADMIN_TOKEN' | jq
```

<p align="right">(<a href="#users-top">back to top ↑</a>)</p>


## PATCH /:user_uid
Updates the profile metadata of a specific user. This endpoint is typically used by administrators to change a user's role or to activate/suspend an account.
> **Authorization**: Endpoints in this section require a valid Bearer Token with administrative privileges (`role: admin`) unless specified otherwise.

### Request
- #### Parameters
  | Parameter  | Location | Type    | Required | Description                       |
  |------------|:--------:|:-------:|:--------:|-----------------------------------|
  | `user_uid` | Path     | UUIDv4  | Yes      | The unique identifier of the user |
- #### Body
  | Field       | Type      | Required   | Description                                                   |
  |-------------|:---------:|:----------:|---------------------------------------------------------------|
  | `role`      | string    | No         | The new access control role to assign to the user             |
  | `is_active` | boolean   | No         | Sets the account status: `true` to enable, `false` to suspend |

### Response
- **`200 OK`**:
  ```json
  {
    "role": "admin",
    "is_active": false,
    "email": "user@domain.tld",
    "created_at": "1970-01-01T00:00:00.000000Z",
    "updated_at": "1970-01-01T00:00:00.000000Z",
    "user_uid": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  }
  ```

### Example
```bash
curl -s -X PATCH 'http://localhost:8000/talos/api/users/:user_uid' \
  -H 'Authorization: Bearer ADMIN_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{ "role": "admin", "is_active": false }' | jq
```

<p align="right">(<a href="#users-top">back to top ↑</a>)</p>


## GET /profile
Retrieves the detailed profile information of the currently authenticated user based on the active session token.

Unlike the administrative endpoints, this route is accessible by any user to fetch their own account details.

### Response
- **`200 OK`**:
  ```json
  {
    "role": "user",
    "is_active": true,
    "email": "user@domain.tld",
    "created_at": "1970-01-01T00:00:00.000000Z",
    "updated_at": "1970-01-01T00:00:00.000000Z",
    "user_uid": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  }
  ```

### Example
```bash
curl -s 'http://localhost:8000/talos/api/users/profile' \
     -H 'Authorization: Bearer ACCESS_TOKEN' | jq
```

<p align="right">(<a href="#users-top">back to top ↑</a>)</p>



## PATCH /password
Allows the currently authenticated user to update their password.

The request requires validation of the current password before applying the new one to prevent unauthorized changes.

### Request
- #### Body
  ```json
  {
    "current_password": "Password123!",
    "new_password": "Password123!!"
  }
  ```

  | Field              | Type   | Required | Description                            |
  |--------------------|:------:|:--------:|----------------------------------------|
  | `current_password` | string | Yes      | The current password                   |
  | `old_password`     | string | Yes      | New password to update (min lenght: 8) |

### Response
- **`204 No Content`**:
  Empty body

### Example
```bash
curl -s -i -X PATCH 'http://localhost:8000/talos/api/users/password' \
  -H 'Authorization: Bearer ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{ "current_password": "Password123!", "new_password": "Password123!!" }'
```


<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="./index.md">← API Reference</a>
  <div>
  (<a href="#users-top">back to top ↑</a>)
  </div>
</div>