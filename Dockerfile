FROM python:3.12.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a non-root user. generated/ is created here so the named volume mounted on it
# starts out owned by that user.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/generated \
    && chown app:app /app/generated

COPY --chown=app:app . .

USER app

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
