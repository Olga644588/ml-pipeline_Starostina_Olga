import requests
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CanaryController:
    def __init__(self):
        self.traefik_api = os.getenv('TRAEFIK_API_URL', 'http://traefik:8080')
        self.stable_service = os.getenv('STABLE_SERVICE', 'ml-service-stable')
        self.canary_service = os.getenv('CANARY_SERVICE', 'ml-service-canary')
        self.error_threshold = float(os.getenv('ERROR_THRESHOLD', '0.05'))
        self.monitor_interval = int(os.getenv('MONITOR_INTERVAL', '60'))

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
    response = requests.put(url, json=payload)
    if response.status_code == 200:
        logger.info(f"Weights updated: stable={stable_weight}, canary={canary_weight}")
    else:
        logger.error(f"Failed to update weights: {response.text}")

    def canary_deployment(self):
        stable_weight = 9
        canary_weight = 1
        self.update_weights(stable_weight, canary_weight)