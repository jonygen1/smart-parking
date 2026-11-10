FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY camera.py .
RUN useradd --create-home camera
USER camera
CMD ["python", "camera.py"]
