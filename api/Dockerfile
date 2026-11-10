# Small official Python image (Debian slim)
FROM python:3.12-slim

# Don't write .pyc files, print logs immediately (no buffering)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first: as long as requirements.txt does not change,
# Docker reuses this cached layer and doesn't reinstall packages on every build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py logic.py ./

# Don't run as root inside the container
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# gunicorn = production web server (Flask's built-in server is for development only)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]
