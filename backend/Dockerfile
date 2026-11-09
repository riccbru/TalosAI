FROM python:3.13
WORKDIR /app

# System libraries required by WeasyPrint (PDF report rendering):
#   libpango-1.0-0 / libpangocairo-1.0-0 -> text layout (pangocairo pulls libcairo2)
#   libgdk-pixbuf-2.0-0                   -> raster image (PNG logo) decoding
#   fonts-*                               -> glyphs: the Debian base ships no fonts,
#                                            so text would render as tofu without them.
#                                            Carlito = Calibri-metric substitute used
#                                            by the report; DejaVu covers the mono box.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        fonts-dejavu-core \
        fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip
COPY . .
ENV PYTHONPATH=/app
ARG BACKEND_PORT
EXPOSE ${BACKEND_PORT}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${BACKEND_PORT}}", "--reload"]