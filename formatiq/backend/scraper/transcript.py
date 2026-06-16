"""
Extracts transcripts from YouTube videos using youtube-transcript-api.
Falls back to auto-generated captions if manual transcript unavailable.
"""
import re
import logging
import threading
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

# Module-level flag: when YouTube rate-limits us, skip all further transcript
# requests for the rest of this scrape session to avoid wasting time.
_rate_limited = threading.Event()


def get_transcript(video_id: str, languages: list[str] | None = None) -> tuple[str | None, bool]:
    """
    Returns (transcript_text, is_available).
    Skips immediately if YouTube has rate-limited this session (429).
    """
    if _rate_limited.is_set():
        return None, False

    if languages is None:
        languages = ["en", "en-US", "en-GB", "hi"]

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try manual transcript first
        try:
            transcript = transcript_list.find_manually_created_transcript(languages)
        except NoTranscriptFound:
            # Fall back to auto-generated
            try:
                transcript = transcript_list.find_generated_transcript(languages)
            except NoTranscriptFound:
                # Take whatever is available and translate if needed
                available = list(transcript_list)
                if not available:
                    return None, False
                transcript = available[0]
                if not transcript.is_translatable:
                    return None, False
                try:
                    transcript = transcript.translate("en")
                except Exception:
                    pass

        entries = transcript.fetch()
        text = _format_transcript(entries)
        return text, True

    except TranscriptsDisabled:
        return None, False
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg:
            _rate_limited.set()
            logger.warning("YouTube transcript API rate-limited (429) — skipping transcripts for this session")
        else:
            logger.debug(f"No transcript for {video_id}: {msg[:80]}")
        return None, False


def _format_transcript(entries: list[dict]) -> str:
    """Convert transcript entries to clean text with rough timestamps."""
    lines = []
    for entry in entries:
        start = entry.get("start", 0)
        text = entry.get("text", "").strip()
        if not text:
            continue
        minutes = int(start // 60)
        seconds = int(start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
    return "\n".join(lines)


def get_plain_transcript(video_id: str) -> tuple[str | None, bool]:
    """Returns transcript without timestamps (for AI analysis)."""
    text, available = get_transcript(video_id)
    if text and available:
        clean = re.sub(r"\[\d{2}:\d{2}\] ", "", text)
        clean = " ".join(clean.split())
        # Truncate at ~15,000 chars to stay within token limits
        if len(clean) > 15000:
            clean = clean[:15000] + "\n...[transcript truncated]"
        return clean, True
    return text, available
