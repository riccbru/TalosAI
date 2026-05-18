<a id="api-top"></a>

<p align="left">
  <a href="../index.md">← Documentation</a>  
</p>

# `API Reference`
This section provides the technical specifications breakdown of all REST endpoints.

The API is built with FastAPI and follows RESTful principles, utilizing JSON for data exchange.

Once the server is running, you can access the interactive Swagger UI at [http://localhost:8000/talos/docs](http://localhost:8000/talos/docs)

### [`Auth API`](./AUTH.md)
Contains endpoints to authenticate a user and create sessions:
* User registration and account activation
* Secure Sign-in with JWT Access Token and HttpOnly Refresh Cookie
* Session termination and Sign-out
* Token rotation (Refresh) for persistent secure access

### [`Missions API`](./MISSIONS.md)
Contains endpoints to manage AI-driven penetration testing operations:
* Creation and orchestration of new security missions
* Real-time monitoring of agent task execution
* Retrieval of mission logs and automated security reports

### [`Sessions API`](./SESSIONS.md)
Contains endpoints to track, monitor, and audit user sessions:
* Retrieval of all security sessions for the authenticated user
* Real-time state validation (`is_revoked` and `expires_at` checks)
* Device-specific session termination (selective logout per platform)
* Administrative global session lookup and mass revocation controls

### [`Status API`](./STATUS.md)
Contains endpoints to verify the status of the ecosystem's infrastructure:
* PostgreSQL connectivity
* API Server Uptime
* Ollama availability
* Docker containers reachability (Kali & Metasploitable)

### [`Users API`](./USERS.md)
Contains endpoints to manage user profiles and monitor account security:
* Retrieval of the authenticated user's profile information
* Update of user preferences and account details
* Management of active security sessions across different devices
* Selective revocation of sessions to prevent unauthorized access

<div style="display: flex; justify-content: space-between; align-items: center;">
  <a href="../index.md">← Documentation</a>
  <div>
    (<a href="#api-top">back to top ↑</a>)
  </div>
</div>
