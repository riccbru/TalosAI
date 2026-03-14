# API Reference

This section provides the technical specifications for the **TalosAI** REST API. The API is built with FastAPI and follows RESTful principles, utilizing JSON for data exchange. Once the server is running, you can access the interactive Swagger UI at [http://localhost:8000/talos/docs](http://localhost:8000/talos/docs)

## Core services

The API is divided into functional modules based on the system's core capabilities:

### [Health API](./health.md)
Contains endpoints to verify the status of the ecosystem's infrastructure:
* API Server Uptime
* PostgreSQL connectivity
* Ollama availability
