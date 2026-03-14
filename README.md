<a id="readme-top"></a>

<p align="center">
  <img src="banner.png" alt="TalosAI Banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/riccbru/TalosAI?color=red" />
  <img src="https://img.shields.io/github/languages/top/riccbru/TalosAI?color=green" />
  <img src="https://img.shields.io/github/languages/code-size/riccbru/TalosAI" />
</p>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ul>
    <li>
      <a href="#about">About TalosAI</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#documentation">Documentation</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
</details>

<!-- ABOUT THE PROJECT -->
## About TalosAI
TalosAI is a sovereign, self-hosted penetration testing agent designed for automated security auditing that executes local LLMs via Ollama.
### Built with
[![NVIDIA][nvidia-img]][nvidia-url] [![Ollama][ollama-img]][ollama-url] [![Hugging Face][huggingface-img]][huggingface-url]

[![FastAPI][fastapi-img]][fastapi-url] [![Swagger][swagger-img]][swagger-url] [![Pydantic][pydantic-img]][pydantic-url] [![Ruff][ruff-img]][ruff-url]

[![PostgreSQL][postgres-img]][postgres-url] [![SQLAlchemy][sqlalchemy-img]][sqlalchemy-url] [![Alembic][alembic-img]][alembic-url]

[![Docker][docker-img]][docker-url] [![Docker Compose][docker-compose-img]][docker-compose-url] [![Gitlab CI][gitlab-ci-img]][gitlab-ci-url] 

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started
### Prerequisites
Ensure your host machine meets the following requirements:
* [Ollama][ollama-download-url]
* [Docker][docker-download-url] & [Docker Compose][docker-compose-download-url]
* [NVIDIA Drivers][nvidia-drivers-download-url]
* [NVIDIA Container Toolkit][nvidia-container-toolkit-download-url]

### Installation
1. **Clone the repo**
    ```bash
    git clone https://github.com/riccbru/TalosAI.git
    ```
2. **Create and edit _.env_ file**
    ```bash
    cd TalosAI && cp .env.sample .env
    ```
3. **Launch**
    ```bash
    docker-compose up --build
    ```
<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DOCUMENTATION -->
## Documentation
The documentation provides a comprehensive deep-dive into the TalosAI ecosystem, including:
- **System Architecture**: A detailed look at the agents orchestration logic and GPU workflow
- **API Specification**: Documentation for all REST endpoints, including request/response schemas

_For more information, please refer to the [Documentation][docs-url]_

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact
Riccardo Bruno

Project Link: [https://github.com/riccbru/TalosAI](https://github.com/riccbru/TalosAI)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[ollama-download-url]: https://ollama.com/download
[docker-download-url]: https://docs.docker.com/get-started/get-docker/
[docker-compose-download-url]: https://docs.docker.com/compose/install/
[nvidia-drivers-download-url]: https://www.nvidia.com/en-us/drivers/
[nvidia-container-toolkit-download-url]: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

[docs-url]: ./docs/index.md

[ollama-url]: https://ollama.com
[ollama-img]: https://img.shields.io/badge/Ollama-black?style=for-the-badge&logo=ollama&logoColor=white

[nvidia-url]: https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4070-4070ti/
[nvidia-img]: https://img.shields.io/badge/NVIDIA-76B900?style=for-the-badge&logo=nvidia&logoColor=white

[huggingface-url]: https://huggingface.co/
[huggingface-img]: https://img.shields.io/badge/%F0%9F%A4%97%20Hugging_Face-FFD21E?style=for-the-badge&logoColor=white

[fastapi-url]: https://fastapi.tiangolo.com/
[fastapi-img]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white

[swagger-url]: https://swagger.io/
[swagger-img]: https://img.shields.io/badge/Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black

[pydantic-url]: https://pydantic-docs.helpmanual.io/
[pydantic-img]: https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white

[ruff-url]: https://github.com/astral-sh/ruff
[ruff-img]: https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black

[postgres-url]: https://www.postgresql.org/
[postgres-img]: https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white

[sqlalchemy-url]: https://www.sqlalchemy.org/
[sqlalchemy-img]: https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white

[alembic-url]: https://alembic.sqlalchemy.org/
[alembic-img]: https://img.shields.io/badge/Alembic-6BA539?style=for-the-badge&logo=sqlalchemy&logoColor=white

[docker-url]: https://www.docker.com/
[docker-img]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white

[docker-compose-url]: https://docs.docker.com/compose/
[docker-compose-img]: https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white

[gitlab-ci-url]: https://docs.gitlab.com/ee/ci/
[gitlab-ci-img]: https://img.shields.io/badge/GitLab_CI/CD-FC6D26?style=for-the-badge&logo=gitlab&logoColor=white