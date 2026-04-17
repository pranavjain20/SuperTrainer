"""Smoke tests for active Anthropic model IDs.

Hits the real Anthropic API with a 1-token ping for each model in
ACTIVE_MODELS. Catches hallucinated / retired model IDs before merge.

Excluded from the default pytest run (see pytest.ini addopts).
Run explicitly: pytest -m smoke
CI should run this on pre-deploy steps with ANTHROPIC_API_KEY set.
"""

import anthropic
import pytest

from app.config import settings
from app.services.model_health import ACTIVE_MODELS

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize("model", ACTIVE_MODELS)
async def test_model_is_reachable(model: str) -> None:
    assert settings.anthropic_api_key, (
        "ANTHROPIC_API_KEY must be set to run smoke tests"
    )
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=1,
        messages=[{"role": "user", "content": "hi"}],
    )
    assert response.id, f"Expected a response from {model}, got empty id"
