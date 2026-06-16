"""
Claude API analysis for individual YouTube videos.
"""
import json
import logging
import time
import re
from anthropic import Anthropic, APIError, RateLimitError

from analyzer.prompts import build_video_analysis_prompt

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", max_retries: int = 3):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.total_tokens = 0

    def analyze_video(
        self,
        title: str,
        description: str,
        transcript: str | None,
        channel_name: str,
        view_count: int,
    ) -> dict | None:
        prompt = build_video_analysis_prompt(title, description, transcript, channel_name, view_count)

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text.strip()
                self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

                result = self._parse_json(raw)
                if result:
                    result["_tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
                    return result

            except RateLimitError:
                wait = 60 * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait}s before retry {attempt + 1}/{self.max_retries}")
                time.sleep(wait)
            except APIError as e:
                logger.error(f"Claude API error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error in Claude analysis: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)

        return None

    def _parse_json(self, raw: str) -> dict | None:
        """Extract and parse JSON from Claude's response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block
        match = re.search(r"\{[\s\S]+\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from response: {raw[:300]}")
        return None

    def estimate_cost(self, n_videos: int, has_transcripts: bool = True) -> dict:
        """Rough cost estimate before running batch analysis."""
        # ~2000 input tokens per video without transcript, ~5000 with
        avg_input = 5000 if has_transcripts else 2000
        avg_output = 800

        total_input = n_videos * avg_input
        total_output = n_videos * avg_output

        # claude-sonnet-4 pricing: $3/M input, $15/M output
        input_cost = (total_input / 1_000_000) * 3.0
        output_cost = (total_output / 1_000_000) * 15.0

        return {
            "videos": n_videos,
            "estimated_input_tokens": total_input,
            "estimated_output_tokens": total_output,
            "estimated_cost_usd": round(input_cost + output_cost, 2),
            "model": self.model,
        }
