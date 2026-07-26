"""
Thin wrapper around OpenRouter's OpenAI-compatible chat completions API.

Not every free/cheap model actually honors `response_format: json_schema`
(confirmed empirically: our chosen model accepted the parameter without
error, then answered in plain prose anyway). So this client treats
`response_format` as a hint, not a guarantee, and parses defensively.
"""

import json
import os
import re

from openai import AsyncOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMOutputError(Exception):
    """Raised when the model's response couldn't be parsed as the expected JSON."""


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = AsyncOpenAI(
            api_key=api_key or os.environ["OPENROUTER_API_KEY"], base_url=OPENROUTER_BASE_URL
        )
        self._model = model or os.environ["OPENROUTER_MODEL"]

    async def structured_completion(self, system: str, user: str, schema: dict, schema_name: str) -> dict:
        strict_instruction = (
            "Respond with ONLY a single valid JSON object matching this schema - "
            "no prose, no markdown fences, no explanation:\n" + json.dumps(schema)
        )
        messages = [
            {"role": "system", "content": f"{system}\n\n{strict_instruction}"},
            {"role": "user", "content": user},
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        }

        # Confirmed empirically (not guessed): this model sometimes returns
        # empty content with finish_reason="stop" and normal token counts -
        # not a token-budget issue, just occasional flakiness (~1-in-3 in
        # testing). Retrying is the correct fix; a few attempts drives the
        # compound failure rate low without masking a real bug.
        last_error: Exception | None = None
        for attempt in range(3):
            response = await self._client.chat.completions.create(
                model=self._model, messages=messages, response_format=response_format
            )
            content = response.choices[0].message.content or ""
            try:
                return self._parse_json_object(content)
            except LLMOutputError as e:
                last_error = e
        raise last_error

    @staticmethod
    def _parse_json_object(content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = _JSON_OBJECT_RE.search(content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise LLMOutputError(f"Model did not return parseable JSON. Raw content: {content!r}")
