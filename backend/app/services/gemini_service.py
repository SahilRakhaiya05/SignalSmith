from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Standard (traffic) keys: AIza... — Auth keys (newer): AQ....
# https://ai.google.dev/gemini-api/docs/api-key
_STANDARD_KEY_RE = re.compile(r"^AIza[0-9A-Za-z_-]{20,}$")
_AUTH_KEY_RE = re.compile(r"^AQ\.[0-9A-Za-z_-]{20,}$")

SYSTEM_PROMPT = """You are SignalSmith Mentor — a direct, senior Splunk optimization guide embedded in the product.
Speak in second person ("you should…", "your baseline index…"). No vendor fluff.

Your job:
- Tell the operator exactly what to do next in the pipeline.
- Write runnable SPL when asked; explain it in one short paragraph after.
- Tie advice to baseline index {baseline} and candidate index {candidate}.
- Warn when a policy risks detection coverage.

Style:
- Short sentences. Bullet steps for procedures. **Bold** only for index names, detection names, and actions.
- SPL always in ```splunk fenced blocks (one query per block).
- Never mention underlying LLM providers, API keys, or model names.
- Never invent event counts — say "run this search to confirm" when data is missing.
- If validation failed, name the detection and suggest revise or policy rollback.
"""

SPL_PROMPT = """Convert this natural language request into a single Splunk SPL query.
Return ONLY the SPL query on one line — no markdown, no explanation, no backticks.

Baseline index: {baseline}
Candidate index: {candidate}

Request: {query}
"""

FORMAT_HINT = (
    "GEMINI_API_KEY is not a recognized Google key (expected AIza... or AQ....). "
    "Create one at https://aistudio.google.com/apikey"
)

AQ_KEY_401_HINT = (
    "Google rejected your AQ. authentication key (HTTP 401). This is a known Gemini API "
    "compatibility issue with newer AQ keys. Workaround: create a standard AIza key in "
    "Google Cloud Console > APIs & Services > Credentials, paste it in .env, and restart. "
    "Or set GEMINI_ENABLED=false — SPL generation still works via Splunk templates."
)

STANDARD_KEY_401_HINT = (
    "Gemini rejected your API key (HTTP 401). Verify GEMINI_API_KEY in .env, ensure the key "
    "is active in https://aistudio.google.com/apikey, then restart the backend."
)


class GeminiService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def model(self) -> str:
        return self.settings.gemini_model

    def is_configured(self) -> bool:
        return bool(self.settings.gemini_api_key.strip())

    @staticmethod
    def key_type(api_key: str) -> str | None:
        key = api_key.strip()
        if _STANDARD_KEY_RE.match(key):
            return "standard"
        if _AUTH_KEY_RE.match(key):
            return "auth"
        return None

    @staticmethod
    def key_format_valid(api_key: str) -> bool:
        return GeminiService.key_type(api_key) is not None

    def auth_issue(self) -> str | None:
        key = self.settings.gemini_api_key.strip()
        if not key:
            return "GEMINI_API_KEY is not set in .env"
        if not self.key_format_valid(key):
            return FORMAT_HINT
        return None

    def status_dict(self) -> dict[str, Any]:
        configured = self.is_configured()
        auth_issue = self.auth_issue()
        key = self.settings.gemini_api_key.strip()
        key_type = self.key_type(key) if configured else None
        available = configured and self.settings.gemini_enabled and auth_issue is None
        auth_hint = auth_issue
        if available and key_type == "auth":
            auth_hint = (
                "AQ. auth key detected. If chat fails with HTTP 401, create a standard AIza key "
                "in Google Cloud Console > Credentials."
            )
        return {
            "configured": configured,
            "available": available,
            "model": self.model if configured else None,
            "provider": "SignalSmith Mentor" if available else ("SPL templates" if configured else None),
            "display_name": "SignalSmith Mentor",
            "key_type": key_type,
            "auth_ok": auth_issue is None,
            "auth_hint": auth_hint,
            "setup_url": "https://aistudio.google.com/apikey",
            "gcp_credentials_url": "https://console.cloud.google.com/apis/credentials",
        }

    @staticmethod
    def friendly_error(status_code: int, body: str, api_key: str = "") -> str:
        if status_code in {401, 403}:
            if GeminiService.key_type(api_key) == "auth":
                return AQ_KEY_401_HINT
            return STANDARD_KEY_401_HINT
        if status_code == 404 and "model" in body.lower():
            return (
                f"Gemini model not found ({get_settings().gemini_model}). "
                "Try GEMINI_MODEL=gemini-2.0-flash in .env"
            )
        if status_code == 429:
            return "Gemini rate limit exceeded. Wait a moment and try again."
        snippet = body[:200].replace("\n", " ")
        return f"Gemini request failed (HTTP {status_code}): {snippet}"

    def _system_text(self) -> str:
        s = self.settings
        return SYSTEM_PROMPT.format(
            baseline=s.splunk_baseline_index,
            candidate=s.splunk_candidate_index,
        )

    async def _generate(self, prompt: str, temperature: float = 0.3) -> str:
        if not self.is_configured():
            raise RuntimeError("Gemini API key not configured")
        if not self.settings.gemini_enabled:
            raise RuntimeError("Gemini is disabled. Set GEMINI_ENABLED=true in .env")
        auth_issue = self.auth_issue()
        if auth_issue:
            raise RuntimeError(auth_issue)

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": self._system_text()}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.settings.gemini_api_key.strip(),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                detail = self.friendly_error(
                    response.status_code,
                    response.text,
                    self.settings.gemini_api_key,
                )
                logger.warning("Gemini API error %s: %s", response.status_code, response.text[:300])
                raise RuntimeError(detail)

            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError("Gemini returned no candidates")
            parts = candidates[0].get("content", {}).get("parts") or []
            texts = [p.get("text", "") for p in parts if p.get("text")]
            text = "\n".join(texts).strip()
            if not text:
                raise RuntimeError("Gemini returned empty response")
            return text

    @staticmethod
    def _clean_spl(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip().strip('"').strip("'")
        if not cleaned.lower().startswith("search"):
            cleaned = f"search {cleaned}"
        return cleaned

    async def generate_spl(self, natural_language: str) -> str:
        s = self.settings
        prompt = SPL_PROMPT.format(
            baseline=s.splunk_baseline_index,
            candidate=s.splunk_candidate_index,
            query=natural_language,
        )
        raw = await self._generate(prompt, temperature=0.1)
        return self._clean_spl(raw)

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        context_block = ""
        if context:
            context_block = f"\n\nCurrent session context:\n{json.dumps(context, indent=2, default=str)}"

        transcript = ""
        for turn in history or []:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            transcript += f"\n{role.upper()}: {content}"

        prompt = (
            f"{transcript}\nUSER: {message}{context_block}\n\n"
            "Respond as SignalSmith Mentor: direct, specific, no provider names."
        )
        return await self._generate(prompt, temperature=0.4)

    async def explain(self, topic: str, context: dict[str, Any] | None = None) -> str:
        context_block = ""
        if context:
            context_block = f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"
        prompt = f"Explain this topic for a Splunk operator using SignalSmith:\n\n{topic}{context_block}"
        return await self._generate(prompt, temperature=0.3)