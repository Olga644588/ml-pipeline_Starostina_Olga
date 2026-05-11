from flask import Flask, request, jsonify
import os
import time
from prometheus_client import start_http_server, Counter, Histogram, generate_latest

app = Flask(__name__)

MODEL_VERSION = os.environ.get('MODEL_VERSION', 'unknown')
PORT = int(os.environ.get('PORT', 8000))
EXPOSE_METRICS = os.environ.get('EXPOSE_METRICS', 'false').lower() == 'true'

REQUESTS = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'version']
)

LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ERRORS = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['code', 'version']
)

if EXPOSE_METRICS:
    try:
        start_http_server(8001)
    except Exception as e:
        print(f"Warning: Could not start metrics server on port 8001: {e}")

@app.route('/health')
def health():
    """Endpoint для проверки здоровья сервиса"""
    REQUESTS.labels(request.method, '/health', MODEL_VERSION).inc()
    return jsonify({
        "status": "ok",
        "version": MODEL_VERSION,
        "timestamp": int(time.time())
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Endpoint для предсказаний ML‑модели"""
    start_time = time.time()

    try:
        data = request.get_json()
        if not data or 'x' not in data:
            raise ValueError("Missing 'x' in request data")

        prediction = len(data['x'])

        duration = time.time() - start_time
        LATENCY.labels(request.method, '/predict').observe(duration)
        REQUESTS.labels(request.method, '/predict', MODEL_VERSION).inc()

        return jsonify({
            "prediction": prediction,
            "version": MODEL_VERSION,
            "processing_time": f"{duration:.4f}s"
        })

    except Exception as e:
        duration = time.time() - start_time
        ERRORS.labels(500, MODEL_VERSION).inc()
        LATENCY.labels(request.method, '/predict').observe(duration)
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """Endpoint для сбора метрик Prometheus"""
    return generate_latest()

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if request.endpoint != 'metrics':
        duration = time.time() - request.start_time
        LATENCY.labels(request.method, request.path).observe(duration)
    return response

if __name__ == '__main__':
    print(f"Starting ML service v{MODEL_VERSION} on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)  
