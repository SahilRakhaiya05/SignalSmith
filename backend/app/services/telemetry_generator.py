from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.models.events import TelemetryEvent

SERVICES = ["auth-service", "checkout-service", "payment-service", "inventory-service"]
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "JP", "IN"]
ROUTES = {
    "auth-service": ["/login", "/logout", "/token", "/health"],
    "checkout-service": ["/cart", "/checkout", "/order", "/health"],
    "payment-service": ["/charge", "/refund", "/status", "/health"],
    "inventory-service": ["/stock", "/reserve", "/release", "/health"],
}


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


def _estimate_size(event: dict) -> int:
    return len(str(event).encode("utf-8"))


class TelemetryGenerator:
    def __init__(self, seed: int | None = None, event_count: int | None = None) -> None:
        settings = get_settings()
        self.seed = seed if seed is not None else settings.random_seed
        self.event_count = event_count if event_count is not None else settings.event_count_default
        self.rng = random.Random(self.seed)

    def generate(self) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []
        base_time = datetime(2026, 6, 14, 8, 0, 0, tzinfo=timezone.utc)

        scenario_plan = self._build_scenario_plan()

        for i in range(self.event_count):
            scenario = scenario_plan[i]
            event = self._generate_event(i, base_time, scenario)
            events.append(event)

        return events

    def _build_scenario_plan(self) -> list[str]:
        """Deterministic scenario distribution scaled to event_count."""
        weights = {
            "normal_traffic": 12000,
            "health_check": 3500,
            "debug_heartbeat": 2800,
            "payment_outage": 120,
            "http_500": 350,
            "slow_checkout": 180,
            "failed_login": 420,
            "credential_stuffing": 280,
            "privileged_anomaly": 45,
            "rare_exception": 305,
        }
        base_total = sum(weights.values())
        scale = self.event_count / base_total
        rare_scenarios = {"payment_outage", "privileged_anomaly", "slow_checkout"}

        plan: list[str] = []
        allocated = 0
        items = list(weights.items())
        for idx, (scenario, count) in enumerate(items):
            if idx == len(items) - 1:
                n = self.event_count - allocated
            else:
                n = int(round(count * scale))
                if scenario in rare_scenarios:
                    n = max(n, 1)
            plan.extend([scenario] * n)
            allocated += n

        while len(plan) < self.event_count:
            plan.append("normal_traffic")
        while len(plan) > self.event_count:
            if "normal_traffic" in plan:
                plan.remove("normal_traffic")
            else:
                plan.pop()

        self.rng.shuffle(plan)
        return plan

    def _generate_event(self, index: int, base_time: datetime, scenario: str) -> TelemetryEvent:
        service = self._pick_service(index, scenario)
        ts = base_time + timedelta(seconds=index * 3 + self.rng.randint(0, 2))
        trace_id = f"trace-{self.seed}-{index:06d}"
        user_id = f"user-{self.rng.randint(1, 5000)}" if service in {"auth-service", "checkout-service"} else None
        route = self.rng.choice(ROUTES[service])
        http_method = "GET" if route == "/health" else self.rng.choice(["GET", "POST", "PUT"])
        source_ip = f"10.{self.rng.randint(0, 255)}.{self.rng.randint(0, 255)}.{self.rng.randint(1, 254)}"
        country = self.rng.choice(COUNTRIES)
        is_privileged = False

        level = "INFO"
        event_type = "request"
        message = f"{service} request completed"
        http_status = 200
        duration_ms = self.rng.randint(20, 400)
        scenario_label = scenario

        if scenario == "health_check":
            route = "/health"
            http_method = "GET"
            event_type = "health_check"
            message = f"{service} health check OK"
            level = "INFO"
            http_status = 200
            duration_ms = self.rng.randint(5, 30)
            scenario_label = "health_check"

        elif scenario == "debug_heartbeat":
            event_type = "debug_heartbeat"
            level = "DEBUG"
            message = f"{service} debug heartbeat pulse"
            http_status = 200
            duration_ms = self.rng.randint(1, 10)
            scenario_label = "debug_heartbeat"

        elif scenario == "payment_outage":
            service = "payment-service"
            route = "/charge"
            level = "ERROR"
            event_type = "payment_error"
            message = "Payment gateway timeout during outage"
            http_status = 503
            duration_ms = self.rng.randint(2000, 5000)
            scenario_label = "payment_outage"

        elif scenario == "http_500":
            level = "ERROR"
            event_type = "http_error"
            message = f"{service} internal server error"
            http_status = 500
            duration_ms = self.rng.randint(100, 800)
            scenario_label = "http_500"

        elif scenario == "slow_checkout":
            service = "checkout-service"
            route = "/checkout"
            event_type = "slow_request"
            message = "Checkout request exceeded latency threshold"
            http_status = 200
            duration_ms = self.rng.randint(1500, 4000)
            scenario_label = "slow_checkout"

        elif scenario == "failed_login":
            service = "auth-service"
            route = "/login"
            http_method = "POST"
            level = "WARN"
            event_type = "failed_login"
            message = "Authentication failed: invalid credentials"
            http_status = 401
            duration_ms = self.rng.randint(50, 200)
            scenario_label = "failed_login"

        elif scenario == "credential_stuffing":
            service = "auth-service"
            route = "/login"
            http_method = "POST"
            level = "WARN"
            event_type = "failed_login"
            message = "Burst of failed login attempts detected"
            http_status = 401
            duration_ms = self.rng.randint(30, 120)
            user_id = f"attacker-{self.rng.randint(1, 50)}"
            scenario_label = "credential_stuffing"

        elif scenario == "privileged_anomaly":
            service = "auth-service"
            route = "/login"
            http_method = "POST"
            level = "INFO"
            event_type = "login"
            message = "Privileged user login from unusual region"
            http_status = 200
            duration_ms = self.rng.randint(80, 250)
            user_id = f"admin-{self.rng.randint(1, 10)}"
            is_privileged = True
            scenario_label = "privileged_anomaly"

        elif scenario == "rare_exception":
            level = "ERROR"
            event_type = "exception"
            message = f"Unhandled exception in {service}: NullPointerException"
            http_status = 500
            duration_ms = self.rng.randint(100, 600)
            scenario_label = "rare_exception"

        payload = {
            "timestamp": ts.isoformat(),
            "service": service,
            "environment": "production",
            "level": level,
            "event_type": event_type,
            "message": message,
            "trace_id": trace_id,
            "user_id": user_id,
            "http_method": http_method,
            "http_route": route,
            "http_status": http_status,
            "duration_ms": duration_ms,
            "source_ip": source_ip,
            "country": country,
            "is_privileged": is_privileged,
            "scenario": scenario_label,
        }
        payload["estimated_size_bytes"] = _estimate_size(payload)
        return TelemetryEvent.model_validate(payload)

    def _pick_service(self, index: int, scenario: str) -> str:
        if scenario in {"payment_outage"}:
            return "payment-service"
        if scenario in {"slow_checkout"}:
            return "checkout-service"
        if scenario in {"failed_login", "credential_stuffing", "privileged_anomaly"}:
            return "auth-service"
        return SERVICES[_stable_hash(f"{self.seed}-{index}") % len(SERVICES)]