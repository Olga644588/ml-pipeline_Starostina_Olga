import requests
import time
import os
import logging
from flask import Flask, jsonify, request 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class CanaryController:
    def __init__(self):
        self.traefik_api = os.getenv('TRAEFIK_API_URL', 'http://traefik:8080')
        self.stable_service = os.getenv('STABLE_SERVICE', 'ml-service-stable')
        self.canary_service = os.getenv('CANARY_SERVICE', 'ml-service-canary')
        self.error_threshold = float(os.getenv('ERROR_THRESHOLD', '0.05'))
        self.monitor_interval = int(os.getenv('MONITOR_INTERVAL', '60'))
        self.stable_weight = 9
        self.canary_weight = 1

    def get_error_rate(self):
        return 0.03

    def update_weights(self, stable_weight, canary_weight):
        url = f"{self.traefik_api}/api/http/services/ml-weighted@docker"
        payload = {
            "weighted": {
                "services": [
                    {
                        "name": self.stable_service,
                        "weight": stable_weight
                    },
            {
                "name": self.canary_service,
                "weight": canary_weight
            }
        ]
        }
        }
        try:
            response = requests.put(url, json=payload)
            if response.status_code == 200:
                logger.info(f"Weights updated: stable={stable_weight}, canary={canary_weight}")
                self.stable_weight = stable_weight
                self.canary_weight = canary_weight
            else:
                logger.error(f"Failed to update weights: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")

    def canary_deployment(self):
        self.update_weights(self.stable_weight, self.canary_weight)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data or 'x' not in data or not isinstance(data['x'], list):
            return jsonify({
                "error": "Invalid input format. Expected JSON with field 'x' as a list"
            }), 400
        prediction = sum(data['x']) / len(data['x'])
        return jsonify({
            "prediction": prediction,
            "model_version": "1.0",
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    controller = CanaryController()

    from threading import Thread
    server_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=80, threaded=True))
    server_thread.daemon = True
    server_thread.start()

    while True:
        try:
            error_rate = controller.get_error_rate()
            if error_rate < controller.error_threshold:
                new_canary = min(controller.canary_weight + 1, 10)
                new_stable = 10 - new_canary
                controller.update_weights(new_stable, new_canary)
            time.sleep(controller.monitor_interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            time.sleep(30)
