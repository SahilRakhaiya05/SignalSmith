from __future__ import annotations

from typing import Any

import yaml

from app.models.proposals import ProposalRecord

WARNING = (
    "# WARNING: This configuration must be reviewed and tested outside production before deployment.\n"
    "# SignalSmith AI generated this policy. Human approval is required.\n"
)


def generate_otel_yaml(proposal: ProposalRecord) -> str:
    processors: list[dict[str, Any]] = [
        {
            "filter/health_checks": {
                "logs": {
                    "log_record": [
                        'attributes["event_type"] != "health_check"',
                    ]
                }
            }
        },
        {
            "filter/debug_heartbeats": {
                "logs": {
                    "log_record": [
                        'attributes["event_type"] != "debug_heartbeat"',
                    ]
                }
            }
        },
        {
            "filter/preserve_errors": {
                "logs": {
                    "log_record": [
                        'attributes["level"] == "ERROR" or attributes["level"] == "CRITICAL" or attributes["http_status"] >= 500',
                    ]
                }
            }
        },
        {
            "filter/preserve_high_latency": {
                "logs": {
                    "log_record": [
                        'attributes["duration_ms"] >= 1500',
                    ]
                }
            }
        },
        {
            "filter/preserve_security": {
                "logs": {
                    "log_record": [
                        'attributes["scenario"] == "credential_stuffing" or attributes["event_type"] == "failed_login"',
                    ]
                }
            }
        },
        {
            "filter/preserve_privileged": {
                "logs": {
                    "log_record": [
                        'attributes["is_privileged"] == true',
                    ]
                }
            }
        },
        {
            "probabilistic_sampler/normal_traffic": {
                "sampling_percentage": 25,
                "hash_seed": 42,
            }
        },
    ]

    config = {
        "receivers": {"otlp": {"protocols": {"grpc": {}, "http": {}}}},
        "processors": processors,
        "exporters": {"logging": {"loglevel": "info"}},
        "service": {
            "pipelines": {
                "logs": {
                    "receivers": ["otlp"],
                    "processors": [
                        "filter/health_checks",
                        "filter/debug_heartbeats",
                        "filter/preserve_errors",
                        "filter/preserve_high_latency",
                        "filter/preserve_security",
                        "filter/preserve_privileged",
                        "probabilistic_sampler/normal_traffic",
                    ],
                    "exporters": ["logging"],
                }
            }
        },
        "signalsmith_metadata": {
            "proposal_id": proposal.id,
            "version": proposal.version,
            "status": proposal.status.value,
            "warning": "Review and test outside production before deployment.",
        },
    }

    return WARNING + yaml.dump(config, default_flow_style=False, sort_keys=False)


def generate_rollback_yaml(proposal: ProposalRecord) -> str:
    config = {
        "receivers": {"otlp": {"protocols": {"grpc": {}, "http": {}}}},
        "processors": {"batch": {}},
        "exporters": {"logging": {"loglevel": "info"}},
        "service": {
            "pipelines": {
                "logs": {
                    "receivers": ["otlp"],
                    "processors": ["batch"],
                    "exporters": ["logging"],
                }
            }
        },
        "signalsmith_metadata": {
            "proposal_id": proposal.id,
            "rollback": True,
            "description": "Original no-filter configuration for rollback.",
            "warning": "Review and test outside production before deployment.",
        },
    }
    return WARNING + yaml.dump(config, default_flow_style=False, sort_keys=False)