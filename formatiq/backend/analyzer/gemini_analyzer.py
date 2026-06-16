"""
Gemini-powered analysis:
- 5-angle video analysis (Villain/Hero/Virality/Credibility/Moral Ground)
- Own channel style profiling (tone, structure, vocabulary, credibility signals)
- Citation finder via Google Search grounding
"""
import json
import logging
import re

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]+\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.error(f"Could not parse Gemini JSON: {raw[:400]}")
    return None


class GeminiAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_angles(
        self,
        title: str,
        description: str,
        transcript: str | None,
        channel_name: str,
        view_count: int,
        is_short: bool = False,
    ) -> dict | None:
        from analyzer.prompts import build_angle_analysis_prompt
        prompt = build_angle_analysis_prompt(title, description, transcript, channel_name, view_count, is_short=is_short)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return _parse_json(response.text.strip())
        except Exception as e:
            logger.error(f"Gemini angle analysis error: {e}")
            raise

    def analyze_channel_style(
        self,
        transcripts: list[str],
        channel_name: str,
        shorts_transcripts: list[str] | None = None,
    ) -> dict | None:
        """
        Analyze multiple video transcripts from the creator's own channel to extract
        their unique tone, vocabulary, script structure, and credibility style.
        """
        combined = "\n\n---VIDEO SEPARATOR---\n\n".join(
            f"LONGFORM VIDEO {i+1}:\n{t[:8000]}" for i, t in enumerate(transcripts[:8])
        )

        shorts_section = ""
        if shorts_transcripts:
            shorts_combined = "\n\n---SHORTS SEPARATOR---\n\n".join(
                f"SHORT VIDEO {i+1}:\n{t[:3000]}" for i, t in enumerate(shorts_transcripts[:8])
            )
            shorts_section = f"""

SHORTS / REELS TRANSCRIPTS (under 2:30 min videos):
{shorts_combined}"""

        prompt = f"""You are analyzing the YouTube channel of a doctor-creator named "{channel_name}".

Below are transcripts from their videos. Study them carefully to extract a precise style profile INCLUDING their language pattern and separate styles for Shorts vs Long-form.

LONG-FORM VIDEO TRANSCRIPTS:
{combined}{shorts_section}

Return ONLY valid JSON with this exact structure:
{{
  "tone_description": "2-3 sentences describing exactly how this creator speaks. Are they formal or casual? Fast or measured? Warm or authoritative? Give specific examples of their speech patterns.",
  "vocabulary": {{
    "common_phrases": ["phrase they use often 1", "phrase 2", "phrase 3", "phrase 4", "phrase 5"],
    "words_they_avoid": ["jargon word 1", "overly formal term 2"],
    "signature_expressions": ["their unique sign-off or opener if any"],
    "hindi_words_used": ["list of Hindi/Devanagari words or phrases they use naturally, empty list if none"]
  }},
  "script_structure": {{
    "hook_style": "How do they open videos? Direct question? Shocking stat? Patient story?",
    "intro_pattern": "What do they cover in the first 60 seconds?",
    "body_pattern": "How do they structure the main content? Sections? Flow?",
    "cta_style": "How do they close and ask for engagement?"
  }},
  "credibility_style": "How do they establish trust? Do they cite studies? Mention their credentials? Use disclaimers? Quote organizations? Be specific.",
  "disclaimer_style": "Do they use medical disclaimers? Exact phrasing if present.",
  "topics_covered": ["topic 1", "topic 2", "topic 3", "topic 4", "topic 5"],
  "what_makes_them_unique": "1-2 sentences on what makes this creator's style distinct from generic health content.",
  "language_pattern": {{
    "detected_language": "english OR hinglish OR hindi — which best describes the primary language used",
    "mixing_style": "Describe exactly how they mix languages. e.g. '50-50 Hindi-English mix, switches mid-sentence, uses Devanagari for Hindi parts, keeps medical terms in English'",
    "hindi_script_used": "roman — all Hindi written in English/Roman alphabet (no Devanagari)",
    "sample_sentence": "Write one example sentence in their exact language style using Roman script for Hindi words (e.g. 'Aaj hum baat karenge sugar ke baare mein, jo India mein ek silent epidemic ban gayi hai')"
  }},
  "shorts_style": {{
    "hook_style": "How do their Shorts open in the first 2-3 seconds? Shocking question? Visual hook? Direct address? Give a specific example.",
    "cta_pattern": "How do they end Shorts? What exact CTA do they use?",
    "pacing": "Describe the energy and pace — fast cuts, slow explanation, high energy?",
    "top_topics": ["topic that works well in their Shorts 1", "topic 2", "topic 3"],
    "sample_hook": "Write one example opening line in their Shorts style and language"
  }}
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return _parse_json(response.text.strip())
        except Exception as e:
            logger.error(f"Gemini channel style analysis error: {e}")
            raise

    def generate_script(self, prompt: str, script_model: str | None = None) -> dict | None:
        """Generate a script using Gemini (uses gemini_script_model, e.g. gemini-2.5-pro)."""
        model = script_model or self.model
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return _parse_json(response.text.strip())
        except Exception as e:
            logger.error(f"Gemini script generation error: {e}")
            raise

    def find_citations(self, script_text: str, topic: str) -> list[dict]:
        """
        Use Gemini with Google Search grounding to find real article links
        for factual claims in the script. Returns list of {claim, source_name, url, snippet}.
        Only cites from authoritative health/medical organizations.
        """
        try:
            from google.genai import types

            prompt = f"""The following is a health/medical script on the topic: "{topic}"

SCRIPT:
{script_text[:4000]}

Find 3-5 real, verifiable citations from authoritative sources (PubMed, WHO, CDC, Mayo Clinic, NEJM, The Lancet, NIH, BMJ, Harvard Health) that support the main factual claims in this script.

For each citation:
1. Identify the specific claim being supported
2. Find a real published article or guideline
3. Provide the actual URL

Return ONLY valid JSON array:
[
  {{
    "claim": "The specific factual claim from the script",
    "source_name": "WHO / PubMed / CDC / etc.",
    "title": "Title of the article or guideline",
    "url": "https://actual-url.org/article",
    "year": "2023"
  }}
]"""

            # Enable Google Search grounding
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            raw = response.text.strip()
            # Parse JSON array
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw).strip()
            try:
                result = json.loads(raw)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
            # Try to find JSON array in response
            match = re.search(r'\[[\s\S]+\]', raw)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Could not parse citations JSON: {raw[:300]}")
            return []
        except Exception as e:
            logger.error(f"Gemini citation finder error: {e}")
            return []
