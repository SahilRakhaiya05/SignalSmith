from __future__ import annotations

import argparse
import json
import sys

import httpx


def _api_base() -> str:
    return "http://127.0.0.1:8080"


def cmd_health(_: argparse.Namespace) -> int:
    r = httpx.get(f"{_api_base()}/api/health", timeout=10)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code == 200 else 1


def cmd_integrations(_: argparse.Namespace) -> int:
    r = httpx.get(f"{_api_base()}/api/integrations/status", timeout=30)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code == 200 else 1


def cmd_status(_: argparse.Namespace) -> int:
    r = httpx.get(f"{_api_base()}/api/session/status", timeout=10)
    data = r.json()
    print(
        f"splunk_connection={data.get('splunk_connection')} "
        f"baseline={data.get('baseline_event_count')} "
        f"candidate={data.get('candidate_event_count')}"
    )
    return 0 if r.status_code == 200 else 1


def cmd_reset(_: argparse.Namespace) -> int:
    r = httpx.post(f"{_api_base()}/api/session/reset", timeout=10)
    print(r.json())
    return 0


def cmd_bootstrap(_: argparse.Namespace) -> int:
    r = httpx.post(f"{_api_base()}/api/session/bootstrap", timeout=600.0)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code == 200 else 1


def cmd_run_pipeline(_: argparse.Namespace) -> int:
    r = httpx.post(f"{_api_base()}/api/session/run", timeout=600.0)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code == 200 else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="signalsmith", description="SignalSmith CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="API health check").set_defaults(func=cmd_health)
    sub.add_parser("integrations", help="Splunk integration status").set_defaults(func=cmd_integrations)
    sub.add_parser("status", help="Current session status").set_defaults(func=cmd_status)
    sub.add_parser("reset", help="Reset session state").set_defaults(func=cmd_reset)
    sub.add_parser("bootstrap", help="Bootstrap telemetry from Splunk").set_defaults(func=cmd_bootstrap)
    sub.add_parser("run", help="Run full optimization pipeline").set_defaults(func=cmd_run_pipeline)

    args = parser.parse_args()
    try:
        return args.func(args)
    except httpx.HTTPError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())