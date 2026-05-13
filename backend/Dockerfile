FROM python:3.13
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip
COPY . .
ENV PYTHONPATH=/app
ARG BACKEND_PORT
EXPOSE ${BACKEND_PORT}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${BACKEND_PORT}}", "--reload"]