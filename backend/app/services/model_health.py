"""Model availability verification.

Single source of truth for which Anthropic model IDs the app uses,
and a ping that confirms each one is reachable. Intended for:
- App startup (fail fast before serving traffic)
- Smoke tests (catch hallucinated model IDs before merge)
"""

import logging

import anthropic

from app.config import settings
from app.services.parser import DEFAULT_MODEL

logger = logging.getLogger("supertrainer")

ACTIVE_MODELS: list[str] = [DEFAULT_MODEL]


async def verify_active_models() -> None:
    """Ping each active Anthropic model with a 1-token request.

    Raises RuntimeError if any model returns 404 (hallucinated / retired ID).
    Silently returns if no API key is configured — lets tests and
    keyless dev envs boot without hitting the network.
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping model availability check")
        return

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    for model in ACTIVE_MODELS:
        try:
            await client.messages.create(
                model=model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            logger.info("Model %s is reachable", model)
        except anthropic.NotFoundError as e:
            raise RuntimeError(
                f"Model {model!r} is not available on the Anthropic API. "
                f"Check ACTIVE_MODELS in app/services/model_health.py. "
                f"Upstream error: {e}"
            ) from e
