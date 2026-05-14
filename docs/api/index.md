<a id="api-top"></a>
# API Reference

This section provides the technical specifications for the **TalosAI** REST API. The API is built with FastAPI and follows RESTful principles, utilizing JSON for data exchange. Once the server is running, you can access the interactive Swagger UI at [http://localhost:8000/talos/docs](http://localhost:8000/talos/docs)

## Core services

The API is divided into functional modules based on the system's core capabilities:

### [Auth API](./auth.md)
Contains endpoints to authenticate a user and create sessions:
* User registration and account activation
* Secure Sign-in with JWT Access Token and HttpOnly Refresh Cookie
* Session termination and Sign-out
* Token rotation (Refresh) for persistent secure access

### [Missions API](./missions.md)
Contains endpoints to manage AI-driven penetration testing operations:
* Creation and orchestration of new security missions
* Real-time monitoring of agent task execution
* Retrieval of mission logs and automated security reports

### [Sessions API](./sessions.md)
Contains endpoints to :
* 
* 
* 
* 

### [Status API](./status.md)
Contains endpoints to verify the status of the ecosystem's infrastructure:
* PostgreSQL connectivity
* API Server Uptime
* Ollama availability
* Docker containers reachability (Kali & Metasploitable)

### [Users API](./users.md)
Contains endpoints to manage user profiles and monitor account security:
* Retrieval of the authenticated user's profile information
* Update of user preferences and account details
* Management of active security sessions across different devices
* Selective revocation of sessions to prevent unauthorized access

<p align="right">(<a href="#api-top">Back to top ↑</a>)</p>



