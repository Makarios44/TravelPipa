# Production image for Railway (or any Docker host).
# Railway uses this file automatically when it is in the project root.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Railway provides PORT; bin/start.sh runs collectstatic, migrate, prepare_site and gunicorn.
CMD ["sh", "bin/start.sh"]
