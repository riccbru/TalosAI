FROM python:3.13
WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip
# Installazione Poetry e configurazione
RUN pip install poetry && poetry config virtualenvs.create false
# Copia dei file di configurazione
COPY pyproject.toml poetry.lock* ./
# Installazione dipendenze (Usa 'sync' per Poetry 2.0)
RUN poetry install --no-interaction --no-ansi

COPY . .
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]