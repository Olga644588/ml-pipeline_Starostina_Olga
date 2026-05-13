import math
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class ABTestConfig:
    test_name: str = "ML-Model-v2-vs-v1"
    traffic_fraction: float = 0.5
    min_sample_size: int = 1000
    max_duration_days: int = 7
    monitoring_interval: int = 500
    alpha: float = 0.05
    effect_size: float = 0.02

    metric_names: List[str] = field(default_factory=lambda: [
        "f1_score", "accuracy", "precision", "recall", "latency_ms", "error_rate"
    ])

    success_criteria: Dict[str, Dict] = field(default_factory=lambda: {
        "f1_score": {"improvement": 0.02, "direction": "greater"},
        "latency_ms": {"improvement": 150, "direction": "less"},
        "error_rate": {"improvement": 0.01, "direction": "less"}
    })

    failure_criteria: Dict[str, float] = field(default_factory=lambda: {
        "f1_score_drop": 0.01,
        "latency_threshold": 150.0,
        "error_rate_threshold": 0.02
    })

class SequentialABTester:
    def __init__(self, config: ABTestConfig):
        self.config = config
        self.control_metrics = {m: [] for m in config.metric_names}
        self.test_metrics = {m: [] for m in config.metric_names}
        self.n_observations = 0
        self.start_time = datetime.now()

    def _calculate_bounds(self, n: int) -> tuple:
        """Границы Pocock для последовательного теста"""
        I_n = n / (2 * self.config.min_sample_size)
        bound = math.sqrt((self.config.alpha**-2) * I_n * (1 - I_n))
        return -bound, bound

    def add_observation(self, is_test: bool, metrics: Dict[str, float]) -> Optional[str]:
        """Добавить наблюдение и проверить условия остановки"""
        target = self.test_metrics if is_test else self.control_metrics
        for metric, value in metrics.items():
            if metric in target:  # защита от неизвестных метрик
                target[metric].append(value)
        self.n_observations += 1

        if self.n_observations % self.config.monitoring_interval == 0:
            return self._check_stopping()
        return None

    def _check_stopping(self) -> Optional[str]:
        # Проверка по времени
        elapsed_days = (datetime.now() - self.start_time).days
        if elapsed_days >= self.config.max_duration_days:
            return "stop_timeout"

        n = min(
            len(self.control_metrics.get("f1_score", [])),
            len(self.test_metrics.get("f1_score", []))
        )
        if n < self.config.min_sample_size:
            return None

        control_f1 = self.control_metrics["f1_score"][:n]
        test_f1 = self.test_metrics["f1_score"][:n]

        if len(control_f1) == 0 or len(test_f1) == 0:
            return None

        t_stat, p_val = stats.ttest_ind(test_f1, control_f1, equal_var=False)
        lower, upper = self._calculate_bounds(n)

        if t_stat <= lower:
            return "stop_inferior"
        elif t_stat >= upper:
            return "stop_superior"

        return None

    def get_final_results(self) -> Dict:
        """Финальный анализ всех метрик"""
        results = {}
        for metric in self.config.metric_names:
            control_data = self.control_metrics[metric]
            test_data = self.test_metrics[metric]

            if len(control_data) > 0 and len(test_data) > 0:
                t_stat, p_val = stats.ttest_ind(test_data, control_data, equal_var=False)
                results[metric] = {
                    "control_mean": round(np.mean(control_data), 4),
            "test_mean": round(np.mean(test_data), 4),
            "p_value": round(p_val, 4),
            "significant": p_val < self.config.alpha
        }
        return results
