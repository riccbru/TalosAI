<p align="center">
  <img src="banner.png" alt="TalosAI Banner" />
</p>

<p align="center">
  <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Ollama-black?style=flat&logo=ollama&logoColor=white"/></a>
  <a href="https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4070-4070ti/"><img src="https://img.shields.io/badge/NVIDIA-76B900?style=flat&logo=nvidia&logoColor=white"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white"/></a>
  <a href="https://swagger.io/"><img src="https://img.shields.io/badge/Swagger-85EA2D?style=flat&logo=swagger&logoColor=black"/></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white"/></a>
  <a href="https://alembic.sqlalchemy.org/"><img src="https://img.shields.io/badge/Alembic-6BA539?style=flat&logo=sqlalchemy&logoColor=white"/></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat&logo=sqlalchemy&logoColor=white"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white"></a>
  <a href="https://pydantic-docs.helpmanual.io/"><img src="https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white"/></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/Ruff-D7FF64?style=flat&logo=ruff&logoColor=black"/></a>
</p>

<p align="center">
TalosAI is a sovereign, self-hosted penetration testing agent designed for automated security auditing that executes local LLMs via Ollama.
</p>


# Installation

## Packages:
- `docker`
- `nvidia-container-toolkit`

## Setup
```bash
git clone https://github.com/riccbru/TalosAI.git
cd TalosAI
cp .env.sample .env
```

## Deploy
```bash
docker-compose up --build
```