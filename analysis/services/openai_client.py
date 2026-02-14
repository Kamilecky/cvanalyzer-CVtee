"""analysis/services/openai_client.py - Wrapper OpenAI API z retry i token tracking."""

import json
import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Klient OpenAI z retry logic, rate limiting i śledzeniem tokenów."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

    def chat(self, system_prompt, user_prompt, max_retries=3):
        """Wysyła request do OpenAI Chat API z retry logic.

        Returns:
            dict z kluczami: 'content' (str), 'tokens_used' (int), 'error' (str|None)
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                tokens = response.usage.total_tokens if response.usage else 0

                return {
                    'content': content,
                    'tokens_used': tokens,
                    'error': None,
                }

            except Exception as e:
                logger.warning(
                    f"OpenAI API attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                    return {
                        'content': None,
                        'tokens_used': 0,
                        'error': str(e),
                    }

    def parse_json_response(self, content):
        """Parsuje odpowiedź JSON z OpenAI. Zwraca dict lub None."""
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            return None
