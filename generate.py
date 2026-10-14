
"""
The one place FitFindr talks to the model.

Two of your three tools call out to a service. Everything that does goes
through generate() below.

This module:
- Paces requests to respect the per-minute limit.
- Caches responses during development, but not evaluation.
- Guards against excessive session requests.
- Retries rate-limit errors and temporary service-unavailable errors.
- Provides readable error messages.
- Tracks model calls and token usage.

The model name and temperature are configured in config.py.
"""

import hashlib
import json
import os
import re
import sys
import time

import config


_call_times: list[float] = []
_session_calls = 0
_cache_hits = 0
_prompt_tokens = 0
_output_tokens = 0
_client = None
_budget_warned = False


class QuotaGuard(Exception):
    """Raised when a session exceeds its request budget."""


class ModelUnavailable(Exception):
    """Raised when the model cannot be reached or a request cannot complete."""


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_key(
    prompt: str,
    system: str | None,
    temperature: float,
) -> str:
    blob = json.dumps(
        [config.MODEL, system or "", prompt, temperature],
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_read(key: str) -> str | None:
    path = config.CACHE_DIR / f"{key}.json"

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    except Exception:
        return None


def _cache_write(key: str, response: str) -> None:
    config.CACHE_DIR.mkdir(exist_ok=True)
    path = config.CACHE_DIR / f"{key}.json"
    path.write_text(
        json.dumps({"response": response}),
        encoding="utf-8",
    )


def clear_cache() -> int:
    """Delete cached responses and return the number removed."""
    if not config.CACHE_DIR.exists():
        return 0

    files = list(config.CACHE_DIR.glob("*.json"))

    for file in files:
        file.unlink()

    return len(files)


# ─── Pacing and guards ────────────────────────────────────────────────────────


def _wait_for_slot() -> None:
    """Wait if the per-minute request allowance has been reached."""
    now = time.monotonic()

    _call_times[:] = [
        t for t in _call_times
        if now - t < 60.0
    ]

    if len(_call_times) < config.REQUESTS_PER_MINUTE:
        return

    sleep_for = 60.0 - (now - _call_times[0]) + 0.1

    if sleep_for > 0:
        if sleep_for >= 1.0:
            print(
                f"  [rate limit] {config.REQUESTS_PER_MINUTE} requests "
                f"used this minute. Waiting {sleep_for:.0f}s. "
                f"This is normal.",
                file=sys.stderr,
                flush=True,
            )

        time.sleep(sleep_for)

        _call_times[:] = [
            t for t in _call_times
            if time.monotonic() - t < 60.0
        ]


def _check_budget() -> None:
    global _budget_warned

    if _session_calls < config.SESSION_REQUEST_BUDGET:
        return

    if not _budget_warned:
        _budget_warned = True

    raise QuotaGuard(
        f"This session has made {_session_calls} requests, which is the "
        f"budget set in config.py (SESSION_REQUEST_BUDGET).\n"
        f"That usually means a loop is running away rather than that you've "
        f"done {_session_calls} requests' worth of real work.\n"
        f"Stop the program and look for the loop. If you really do need more, "
        f"raise the number in config.py — but look first."
    )


def usage() -> str:
    """Return a summary of model calls, cache hits, and token usage."""
    tokens = ""

    if _prompt_tokens or _output_tokens:
        tokens = (
            f", {_prompt_tokens} prompt + "
            f"{_output_tokens} output tokens"
        )

    cache_info = (
        f", {_cache_hits} served from cache"
        if _cache_hits
        else ""
    )

    return (
        f"{_session_calls} model calls this session"
        f"{cache_info}"
        f"{tokens}"
    )


def call_count() -> int:
    return _session_calls


def token_counts() -> dict:
    """Return token counts reported by the model service."""
    return {
        "prompt": _prompt_tokens,
        "output": _output_tokens,
        "total": _prompt_tokens + _output_tokens,
    }


def _record_tokens(response) -> None:
    """Record available token counts without disrupting a successful call."""
    global _prompt_tokens, _output_tokens

    try:
        meta = getattr(response, "usage_metadata", None)

        if meta is None:
            return

        prompt = getattr(meta, "prompt_token_count", None)
        output = getattr(meta, "candidates_token_count", None)

        if isinstance(prompt, int):
            _prompt_tokens += prompt

        if isinstance(output, int):
            _output_tokens += output

    except Exception:
        pass


# ─── Model calls ──────────────────────────────────────────────────────────────


def _explain(exc: Exception) -> str:
    """Convert provider exceptions into actionable error messages."""
    message = str(exc).lower()

    if (
        "api key" in message
        or "api_key" in message
        or "unauthenticated" in message
    ):
        return (
            "The model rejected your API key. Check GEMINI_API_KEY "
            "in your .env file, or create a fresh key at "
            "aistudio.google.com."
        )

    if "not found" in message or "404" in message:
        return (
            f"The model name '{config.MODEL}' did not resolve. "
            "If you changed AI201_MODEL in your .env, put it back. "
            "Otherwise post in the help channel."
        )

    if (
        "connection" in message
        or "timeout" in message
        or "network" in message
    ):
        return (
            "Couldn't reach the model. "
            "Check your internet connection and try again."
        )

    return f"Couldn't reach the model: {exc}"


def _retry_delay(exc: Exception, attempt: int) -> float:
    """
    Determine the retry delay.

    Honor the provider's suggested delay when available.
    Otherwise use exponential backoff, capped at 65 seconds.
    """
    error_text = str(exc)

    match = (
        re.search(
            r"retry in (\d+(?:\.\d+)?)\s*s",
            error_text,
            re.I,
        )
        or re.search(
            r"""retryDelay['"]?\s*:\s*['"]?(\d+(?:\.\d+)?)s""",
            error_text,
        )
    )

    hinted = float(match.group(1)) + 1.0 if match else 0.0

    return min(
        65.0,
        max(2.0 ** attempt, hinted),
    )


def _get_client():
    global _client

    if _client is None:
        from google import genai

        key = os.getenv("GEMINI_API_KEY", "").strip()

        if not key:
            raise RuntimeError(
                "No GEMINI_API_KEY found.\n"
                "Copy .env.example to .env and paste your key in, "
                "then try again. `python test.py` will confirm "
                "it's working."
            )

        _client = genai.Client(api_key=key)

    return _client


def generate(
    prompt: str,
    system: str | None = None,
    cache: bool = True,
    temperature: float | None = None,
) -> str:
    """
    Send a prompt to the model and return generated text.

    Args:
        prompt: The prompt to send.
        system: Optional system instruction.
        cache: Whether to reuse a previously cached response.
        temperature: Sampling temperature; defaults to config.TEMPERATURE.

    Temporary 429 and 503 errors are retried with backoff.
    Other errors are surfaced immediately as ModelUnavailable.
    """
    global _session_calls, _cache_hits

    use_cache = cache and config.CACHE_ENABLED

    temperature = (
        config.TEMPERATURE
        if temperature is None
        else temperature
    )

    key = _cache_key(prompt, system, temperature)

    if use_cache:
        hit = _cache_read(key)

        if hit is not None:
            _cache_hits += 1
            return hit

    _check_budget()

    last_error: Exception | None = None

    for attempt in range(config.MAX_RETRIES):
        _wait_for_slot()
        _check_budget()

        try:
            client = _get_client()

            _call_times.append(time.monotonic())
            _session_calls += 1

            call_config = {
                "temperature": temperature,
            }

            if system:
                call_config["system_instruction"] = system

            kwargs = {
                "model": config.MODEL,
                "contents": prompt,
                "config": call_config,
            }

            response = client.models.generate_content(**kwargs)

            _record_tokens(response)

            text = (response.text or "").strip()

            if use_cache:
                _cache_write(key, text)

            return text

        except Exception as exc:
            last_error = exc
            message = str(exc).lower()

            # Existing behavior: retry rate-limit errors.
            rate_limited = (
                "429" in message
                or ("resource" in message and "exhaust" in message)
                or ("rate" in message and "limit" in message)
            )

            # Milestone 5 improvement: also retry temporary 503 errors.
            service_unavailable = "503" in message

            # Do not retry invalid keys, missing models, or other errors.
            if not rate_limited and not service_unavailable:
                raise ModelUnavailable(_explain(exc)) from exc

            # No need to sleep after the final attempt.
            if attempt == config.MAX_RETRIES - 1:
                break

            backoff = _retry_delay(exc, attempt)

            error_type = (
                "rate limit"
                if rate_limited
                else "model unavailable"
            )

            print(
                f"  [{error_type}] Retrying in {backoff:.0f}s "
                f"(attempt {attempt + 1} of "
                f"{config.MAX_RETRIES}).",
                file=sys.stderr,
                flush=True,
            )

            time.sleep(backoff)

    # The agent can catch this and show a friendly message.
    raise ModelUnavailable(
        f"The model is temporarily unavailable after "
        f"{config.MAX_RETRIES} attempts. "
        f"Please try again later. Last error: {last_error}"
    ) from last_error
