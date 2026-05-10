FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY canary_controller.py .
CMD ["python", "canary_controller.py"]
