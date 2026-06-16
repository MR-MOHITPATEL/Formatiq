"""
Script generation pipeline: validates content angle, fetches trending topics,
calls Groq (preferred) or Claude to generate full scripts and outlines.
"""
import json
import logging
import time
from sqlalchemy.orm import Session

from database import GeneratedScript, Video, Channel, ChannelStyleProfile, VideoAngleAnalysis
from analyzer.claude_analyzer import ClaudeAnalyzer
from analyzer.prompts import build_shorts_script_prompt, build_longform_script_prompt
from recommender.content_validator import validate_content_angle
from scraper.news_fetcher import get_trending_topics

logger = logging.getLogger(__name__)


def _parse_llm_json(raw: str) -> dict | None:
    """Parse JSON from LLM output — handles plain JSON and markdown code fences."""
    import re
    raw = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Find the outermost {...} block
    match = re.search(r"\{[\s\S]+\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.error(f"Could not parse LLM JSON response: {raw[:400]}")
    return None


def _call_groq(prompt: str, groq_api_key: str, model: str, max_tokens: int) -> dict | None:
    """Call Groq API and return parsed JSON result."""
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        # Groq compound-beta context limit — cap output to stay safe
        safe_max = min(max_tokens, 8000)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional health content scriptwriter. Always respond with valid JSON only — no markdown, no code fences, no explanation outside the JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=safe_max,
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
        result = _parse_llm_json(raw)
        if result:
            logger.info(f"Groq script generated successfully ({len(raw)} chars)")
        return result
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise  # re-raise so caller can report the real error


def get_trending_topics_for_niche(niche: str, api_key: str = "") -> list[dict]:
    """Return trending news items for the configured niche."""
    return get_trending_topics(niche=niche, api_key=api_key)


def _collect_evidence_titles(validation_result: dict) -> list[str]:
    titles = []
    for ev in validation_result.get("direct_evidence", [])[:3]:
        if ev.get("title"):
            titles.append(ev["title"])
    for ev in validation_result.get("market_evidence", [])[:3]:
        if ev.get("title"):
            titles.append(ev["title"])
    return titles


_KW_STOP = {
    # generic adjectives/adverbs that match everything
    "high", "best", "good", "only", "just", "most", "more", "less", "very",
    "great", "real", "true", "well", "same", "last", "long", "full", "even",
    "ever", "find", "know", "need", "make", "take", "give", "come", "back",
    "work", "help", "time", "ways", "does", "gets", "like", "will", "that",
    # generic stop words
    "this", "with", "from", "have", "been", "your", "their", "what",
    "which", "about", "also", "after", "other", "into", "than", "them",
    "then", "some", "such", "when", "each", "over", "many", "much",
}


def _find_matching_competitor_videos(db: Session, topic: str, angle: str = "", max_videos: int = 8) -> list:
    """Find competitor videos in DB that match the topic keywords.
    Requires at least 2 significant keyword matches to avoid generic false positives."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import desc

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    # Filter out generic words that cause false matches (e.g. "high" matching gym videos)
    sig_keywords = [
        w for w in (topic + " " + angle).lower().split()
        if len(w) > 3 and w not in _KW_STOP
    ]
    if not sig_keywords:
        return []

    # Always require at least 2 matches when there are 2+ meaningful keywords
    min_matches = min(2, len(sig_keywords))

    candidates = (
        db.query(Video)
        .join(Channel, Video.channel_id == Channel.id)
        .filter(Channel.competitor_tier.in_(["direct", "market"]))
        .filter(Video.published_at >= cutoff)
        .order_by(desc(Video.view_count))
        .limit(500)
        .all()
    )

    matching = []
    for v in candidates:
        text = f"{v.title or ''} {v.description or ''}".lower()
        if sum(1 for kw in sig_keywords if kw in text) >= min_matches:
            matching.append(v)
        if len(matching) >= max_videos:
            break
    return matching


def analyze_competitor_videos_for_topic(
    db: Session,
    topic: str,
    angle: str = "",
    gemini_analyzer=None,
    max_videos: int = 5,
) -> list:
    """
    On-demand: find top competitor videos for the topic, run Gemini 5-angle analysis
    on any that haven't been analyzed yet, cache results in DB.
    Returns list of (video, angle_analysis) tuples.
    """
    import time as _time

    if not gemini_analyzer:
        return []

    matching = _find_matching_competitor_videos(db, topic, angle, max_videos=max_videos)
    if not matching:
        logger.info(f"No matching competitor videos found for topic: {topic}")
        return []

    results = []
    for v in matching:
        # Use cached analysis if available
        existing = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
        if existing:
            results.append((v, existing))
            continue

        # Run fresh Gemini analysis
        try:
            is_short = (v.duration_seconds or 0) <= 150
            analysis_data = gemini_analyzer.analyze_angles(
                title=v.title or "",
                description=v.description or "",
                transcript=v.transcript,
                channel_name=v.channel_name or "",
                view_count=v.view_count or 0,
                is_short=is_short,
            )
            if not analysis_data:
                continue

            # Re-check inside transaction — another request may have inserted it between our check and now
            existing_now = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
            if existing_now:
                results.append((v, existing_now))
                continue

            row = VideoAngleAnalysis(
                video_id=v.id,
                villain_present=analysis_data.get("villain", {}).get("present", False),
                villain_description=analysis_data.get("villain", {}).get("description", ""),
                villain_exact_lines=analysis_data.get("villain", {}).get("exact_lines", []),
                hero_present=analysis_data.get("hero", {}).get("present", False),
                hero_description=analysis_data.get("hero", {}).get("description", ""),
                hero_exact_lines=analysis_data.get("hero", {}).get("exact_lines", []),
                virality_present=analysis_data.get("virality", {}).get("present", False),
                virality_description=analysis_data.get("virality", {}).get("description", ""),
                virality_exact_lines=analysis_data.get("virality", {}).get("exact_lines", []),
                credibility_present=analysis_data.get("credibility", {}).get("present", False),
                credibility_description=analysis_data.get("credibility", {}).get("description", ""),
                credibility_exact_lines=analysis_data.get("credibility", {}).get("exact_lines", []),
                moral_ground_present=analysis_data.get("moral_ground", {}).get("present", False),
                moral_ground_description=analysis_data.get("moral_ground", {}).get("description", ""),
                moral_ground_exact_lines=analysis_data.get("moral_ground", {}).get("exact_lines", []),
                format_point_mapping=analysis_data.get("format_point_mapping", {}),
                overall_strength=analysis_data.get("overall_strength"),
                model_used="gemini-on-demand",
            )
            try:
                db.add(row)
                db.commit()
                db.refresh(row)
                results.append((v, row))
                logger.info(f"On-demand analyzed competitor video: {v.title[:60]}")
            except Exception as insert_err:
                db.rollback()
                # Another process beat us to it — fetch and use the existing row
                fallback = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
                if fallback:
                    results.append((v, fallback))
                else:
                    logger.warning(f"Could not save analysis for video {v.id}: {insert_err}")
            _time.sleep(0.3)  # avoid rate limiting
        except Exception as e:
            db.rollback()
            logger.warning(f"On-demand analysis failed for video {v.id}: {e}")

    return results


def _extract_transcript_patterns(analyzed_videos: list) -> str:
    """Layer 2: Extract exact hook sentences, power stats, and audience questions from top video transcripts."""
    import re

    with_transcripts = [(v, ad) for v, ad in analyzed_videos if v.transcript and len(v.transcript) > 200]
    with_transcripts.sort(key=lambda x: x[0].view_count or 0, reverse=True)
    top = with_transcripts[:3]

    if not top:
        return ""

    lines = ["\nTRANSCRIPT PATTERN ANALYSIS — Exact language from top competitor videos:\n"]

    stat_pattern = re.compile(
        r'[^.!?\n]*\b\d[\d,\.]*\s*(%|percent|crore|lakh|million|billion|mg|mcg|mmhg|kg|years?|months?|weeks?|study|studies|patients?|research)[^.!?\n]*[.!?]',
        re.IGNORECASE,
    )

    for v, ad in top:
        views_k = f"{v.view_count // 1000}K" if v.view_count and v.view_count >= 1000 else str(v.view_count or 0)
        lines.append(f"▶ [{views_k} views] \"{v.title}\"")

        transcript = v.transcript.strip()

        # Opening hook — first complete sentences up to ~350 chars
        hook_raw = transcript[:400]
        last_break = max(hook_raw.rfind('.'), hook_raw.rfind('?'), hook_raw.rfind('!'))
        hook_text = hook_raw[:last_break + 1].strip() if last_break > 80 else hook_raw.strip()
        lines.append(f"  OPENING HOOK: \"{hook_text}\"")

        # Questions the creator asks the audience
        sentences = re.split(r'(?<=[.!?])\s+', transcript)
        questions = [s.strip() for s in sentences if s.strip().endswith('?') and 20 < len(s.strip()) < 150][:2]
        if questions:
            lines.append(f"  AUDIENCE QUESTIONS: {' | '.join(questions)}")

        # Power stats — lines with numbers + health units
        stats = stat_pattern.findall(transcript)
        if stats:
            lines.append(f"  POWER STAT: \"{stats[0].strip()[:140]}\"")

        lines.append("")

    return "\n".join(lines)


def _collect_cross_topic_intel(db: Session, topic: str, angle: str = "") -> str:
    """Layer 3: Find proven villain/hero framings from related health topics already in the DB."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import desc

    stop_words = {"this", "that", "with", "from", "have", "been", "will", "your", "their",
                  "what", "which", "about", "more", "also", "just", "after", "other", "into"}
    topic_keywords = [w for w in (topic + " " + angle).lower().split() if len(w) > 3 and w not in stop_words]
    if not topic_keywords:
        return ""

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    # Health topic adjacency map — used to find related-but-different topics
    health_adjacent = {
        "blood":       ["heart", "pressure", "cholesterol", "circulation", "anemia"],
        "heart":       ["blood", "pressure", "cholesterol", "cardiac", "cardiovascular"],
        "pressure":    ["heart", "salt", "sodium", "stress", "kidney"],
        "sugar":       ["diabetes", "insulin", "glucose", "carb", "weight"],
        "diabetes":    ["sugar", "insulin", "glucose", "obesity", "blood"],
        "insulin":     ["sugar", "diabetes", "glucose", "weight", "resistance"],
        "weight":      ["fat", "obesity", "metabolism", "diet", "exercise"],
        "vitamin":     ["deficiency", "supplement", "nutrient", "iron", "calcium"],
        "iron":        ["anemia", "vitamin", "deficiency", "blood", "fatigue"],
        "calcium":     ["bone", "vitamin", "osteoporosis", "dairy", "supplement"],
        "inflammation":["pain", "arthritis", "immune", "chronic", "diet"],
        "liver":       ["fatty", "cholesterol", "detox", "alcohol", "diet"],
        "kidney":      ["pressure", "protein", "water", "stone", "dialysis"],
        "thyroid":     ["hormone", "weight", "fatigue", "metabolism", "iodine"],
        "cholesterol": ["heart", "lipid", "statin", "blood", "fat"],
        "sleep":       ["cortisol", "stress", "hormone", "fatigue", "brain"],
        "stress":      ["cortisol", "sleep", "blood", "pressure", "anxiety"],
        "gut":         ["probiotic", "digestion", "microbiome", "bloating", "immune"],
        "protein":     ["muscle", "kidney", "amino", "weight", "diet"],
        "immune":      ["vitamin", "zinc", "gut", "infection", "inflammation"],
    }

    related_terms: set[str] = set()
    for kw in topic_keywords:
        if kw in health_adjacent:
            related_terms.update(health_adjacent[kw])
        for key, vals in health_adjacent.items():
            if kw in vals:
                related_terms.add(key)

    if not related_terms:
        return ""

    strong_analyses = (
        db.query(VideoAngleAnalysis, Video)
        .join(Video, VideoAngleAnalysis.video_id == Video.id)
        .join(Channel, Video.channel_id == Channel.id)
        .filter(Channel.competitor_tier.in_(["direct", "market"]))
        .filter(Video.published_at >= cutoff)
        .filter(VideoAngleAnalysis.overall_strength >= 7)
        .order_by(desc(Video.view_count))
        .limit(200)
        .all()
    )

    cross_matches = []
    for ad, v in strong_analyses:
        title_lower = (v.title or "").lower()
        # Must contain a related term
        if not any(rt in title_lower for rt in related_terms):
            continue
        # Must NOT be about the exact same topic (avoid duplicating main intel block)
        overlap = sum(1 for kw in topic_keywords if kw in title_lower)
        if overlap >= max(1, len(topic_keywords) // 2):
            continue
        cross_matches.append((v, ad))
        if len(cross_matches) >= 5:
            break

    if not cross_matches:
        return ""

    lines = ["\nCROSS-TOPIC PROVEN ANGLES — High-performing framings from related health topics to adapt:\n"]
    for v, ad in cross_matches:
        views_k = f"{v.view_count // 1000}K" if v.view_count and v.view_count >= 1000 else str(v.view_count or 0)
        lines.append(f"▶ [{views_k} views] \"{v.title}\" (related topic)")
        if ad.villain_present and ad.villain_description:
            lines.append(f"  VILLAIN TO ADAPT: {ad.villain_description[:150]}")
        if ad.hero_present and ad.hero_description:
            lines.append(f"  HERO TO ADAPT: {ad.hero_description[:120]}")
        if ad.virality_present and ad.virality_exact_lines:
            lines.append(f"  VIRAL MOMENT: \"{ad.virality_exact_lines[0][:100]}\"")
        lines.append("")

    lines.append("INSTRUCTION: Adapt these proven villain/hero framings to your specific topic — same structure, new context.")
    return "\n".join(lines)


def _collect_competitor_intelligence(db: Session, topic: str, angle: str = "", analyzed_videos: list | None = None) -> str:
    """
    Build competitor intelligence block for the script prompt.
    Uses pre-analyzed video data if provided, otherwise falls back to title/description matching.
    """
    if analyzed_videos:
        lines = [f"COMPETITOR INTELLIGENCE — {len(analyzed_videos)} competitor videos analyzed for this topic:\n"]
        for i, (v, ad) in enumerate(analyzed_videos, 1):
            views_k = f"{v.view_count // 1000}K" if v.view_count and v.view_count >= 1000 else str(v.view_count or 0)
            lines.append(f"{i}. [{views_k} views] \"{v.title}\" — {v.channel_name}")
            if ad.villain_present and ad.villain_description:
                lines.append(f"   VILLAIN THEY USED: {ad.villain_description[:150]}")
            if ad.virality_present and ad.virality_description:
                lines.append(f"   VIRAL HOOK: {ad.virality_description[:150]}")
            if ad.hero_description:
                lines.append(f"   HERO/SOLUTION: {ad.hero_description[:120]}")
            if ad.villain_exact_lines:
                lines.append(f"   EXACT HOOK LINE: \"{ad.villain_exact_lines[0][:100]}\"")
            if ad.overall_strength:
                lines.append(f"   CONTENT STRENGTH: {ad.overall_strength}/10")
            lines.append("")
    else:
        # Fallback: use raw title/description matching (no analysis)
        matching = _find_matching_competitor_videos(db, topic, angle)
        if not matching:
            return "No competitor videos found for this topic. Write based on general best practices."
        lines = [f"COMPETITOR VIDEOS ON THIS TOPIC (titles only — not yet angle-analyzed):\n"]
        for v in matching:
            views_k = f"{v.view_count // 1000}K" if v.view_count and v.view_count >= 1000 else str(v.view_count or 0)
            lines.append(f"- [{views_k} views] \"{v.title}\" — {v.channel_name}")

    # Gap analysis
    all_titles = " ".join(
        (v.title or "") for (v, _) in (analyzed_videos or [])
        if isinstance(v, Video)
    ).lower() if analyzed_videos else ""

    if not all_titles:
        all_titles = " ".join(
            v.title or "" for v in _find_matching_competitor_videos(db, topic, angle)
        ).lower()

    gap_checks = [
        ("Indian-context / Desi angle", ["india", "indian", "desi"]),
        ("root cause explanation", ["root cause", "why does", "reason behind"]),
        ("myth busting", ["myth", "wrong", "mistake", "misunderstood", "actually"]),
        ("research / study-backed claims", ["study", "research", "trial", "evidence", "pubmed"]),
        ("practical daily-life steps", ["steps", "daily", "practical", "actionable", "routine"]),
    ]
    gaps = [name for name, words in gap_checks if not any(w in all_titles for w in words)]
    if gaps:
        lines.append("GAPS COMPETITORS ARE MISSING (your differentiation opportunity):")
        for g in gaps[:3]:
            lines.append(f"  ✦ {g}")

    lines.append("\nINSTRUCTION: Use competitor villain/hook angles as inspiration — but write your own stronger, more differentiated version that fills the gaps above.")

    # Layer 2: transcript-level hook/stat/question patterns from top videos
    if analyzed_videos:
        transcript_block = _extract_transcript_patterns(analyzed_videos)
        if transcript_block:
            lines.append(transcript_block)

    # Layer 3: cross-topic proven angles from related health topics
    cross_block = _collect_cross_topic_intel(db, topic, angle)
    if cross_block:
        lines.append(cross_block)

    return "\n".join(lines)


def _get_own_channel_style(db: Session) -> dict | None:
    """Fetch the style profile of the creator's own channel if it exists."""
    profile = (
        db.query(ChannelStyleProfile)
        .join(Channel, ChannelStyleProfile.channel_id == Channel.id)
        .filter(Channel.competitor_tier == "own")
        .first()
    )
    if profile and profile.raw_profile:
        return profile.raw_profile
    return None


def generate_script(
    db: Session,
    analyzer: ClaudeAnalyzer,
    topic: str,
    format_type: str,  # "shorts" | "longform"
    angle: str = "",
    niche: str = "doctor / pharmaceutical",
    longform_target_words: int = 2000,
    force: bool = False,
    groq_api_key: str = "",
    groq_model: str = "compound-beta",
    gemini_analyzer=None,
    gemini_script_model: str = "gemini-2.5-pro",
    language: str = "hinglish",
) -> dict:
    """
    Full pipeline: validate → generate → persist.

    Returns the generated script dict (same shape as GeneratedScript row).
    Raises ValueError if validation fails and force=False.
    """
    # Step 1 — validate angle
    validation = validate_content_angle(db, topic, angle)

    if not validation["go"] and not force:
        return {
            "validated": False,
            "validation_result": validation,
            "full_script": None,
            "outline": None,
            "message": validation["message"],
        }

    # Step 2 — on-demand competitor analysis + own channel style
    evidence_titles = _collect_evidence_titles(validation)
    channel_style = _get_own_channel_style(db)
    if channel_style:
        logger.info("Injecting own channel style profile into script prompt")

    # Run on-demand Gemini 5-angle analysis on top matching competitor videos
    analyzed_videos = []
    if gemini_analyzer:
        logger.info(f"Running on-demand competitor analysis for topic: {topic}")
        analyzed_videos = analyze_competitor_videos_for_topic(
            db, topic, angle, gemini_analyzer=gemini_analyzer, max_videos=5
        )
        logger.info(f"On-demand analysis complete: {len(analyzed_videos)} competitor videos analyzed")

    competitor_intel = _collect_competitor_intelligence(db, topic, angle, analyzed_videos=analyzed_videos or None)

    # Step 3 — build prompt
    if format_type == "shorts":
        prompt = build_shorts_script_prompt(topic, angle, niche, evidence_titles, channel_style, language, competitor_intel=competitor_intel)
        max_tokens = 2000
    else:
        prompt = build_longform_script_prompt(topic, angle, niche, evidence_titles, longform_target_words, channel_style, language, competitor_intel=competitor_intel)
        max_tokens = 10000

    result = None
    gemini_error_message = None

    # Gemini 2.5 Pro — only LLM used for script generation (3 attempts on 503)
    if gemini_analyzer:
        retry_delays = [0, 5, 10]  # immediate, then 5s, then 10s
        for attempt, delay in enumerate(retry_delays, 1):
            if delay:
                logger.info(f"Retrying Gemini script generation in {delay}s (attempt {attempt}/3)...")
                time.sleep(delay)
            logger.info(f"Generating script with Gemini ({gemini_script_model}), attempt {attempt}/3")
            try:
                result = gemini_analyzer.generate_script(prompt, script_model=gemini_script_model)
                if result:
                    break  # success
            except Exception as e:
                err_str = str(e)
                is_overloaded = "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower()
                logger.warning(f"Gemini attempt {attempt} failed: {err_str[:120]}")
                if is_overloaded and attempt < len(retry_delays):
                    continue  # retry
                # Non-retryable error or final attempt — set error message
                if is_overloaded:
                    gemini_error_message = "Gemini is experiencing high demand right now. Please try again in a minute."
                elif "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                    gemini_error_message = "Gemini rate limit reached. Please wait a moment and try again."
                elif "400" in err_str or "invalid" in err_str.lower():
                    gemini_error_message = "Script generation failed due to an invalid request. Please try again."
                else:
                    gemini_error_message = f"Script generation failed: {err_str[:200]}"
                result = None
                break

    if not result:
        return {
            "validated": validation["go"],
            "validation_result": validation,
            "full_script": None,
            "outline": None,
            "message": gemini_error_message or "Gemini is not configured. Please add a Gemini API key in config.yaml.",
        }

    # Step 4 — fetch citations via Gemini Google Search grounding
    citations = []
    full_script = result.get("full_script", "")
    cite_topics = result.get("cite_topics", [])

    if gemini_analyzer and (cite_topics or full_script):
        try:
            search_text = full_script if full_script else topic
            citations = gemini_analyzer.find_citations(search_text, topic)
            logger.info(f"Found {len(citations)} citations via Gemini")
        except Exception as e:
            logger.warning(f"Citation fetch failed (non-fatal): {e}")

    # Step 5 — persist to DB
    import json
    outline_obj = result.get("outline", {})
    outline_text = json.dumps(outline_obj) if isinstance(outline_obj, dict) else str(outline_obj)

    script_row = GeneratedScript(
        topic=topic,
        angle=angle,
        format_type=format_type,
        validated=validation["go"],
        validation_result=validation,
        trending_sources=["youtube_data", "google_news"],
        full_script=full_script,
        outline=outline_text,
        citations=citations,
        language=language,
    )
    db.add(script_row)
    db.commit()
    db.refresh(script_row)

    # Build competitor video links list from analyzed videos
    competitor_links = []
    for v, _ in (analyzed_videos or []):
        competitor_links.append({
            "title": v.title or "",
            "channel_name": v.channel_name or "",
            "view_count": v.view_count or 0,
            "youtube_url": f"https://www.youtube.com/watch?v={v.video_id}",
        })

    return {
        "id": script_row.id,
        "topic": topic,
        "angle": angle,
        "format_type": format_type,
        "validated": validation["go"],
        "validation_result": validation,
        "full_script": full_script,
        "outline": outline_obj,
        "suggested_title": result.get("suggested_title", ""),
        "hook_line": result.get("hook_line", ""),
        "thumbnail_text": result.get("thumbnail_text", ""),
        "citations": citations,
        "competitor_links": competitor_links,
        "created_at": script_row.created_at.isoformat(),
        "message": "Script generated successfully.",
    }


def list_generated_scripts(db: Session, limit: int = 20, offset: int = 0) -> list[dict]:
    import json
    rows = (
        db.query(GeneratedScript)
        .order_by(GeneratedScript.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = []
    for row in rows:
        try:
            outline = json.loads(row.outline) if row.outline else {}
        except Exception:
            outline = {}
        result.append({
            "id": row.id,
            "topic": row.topic,
            "angle": row.angle,
            "format_type": row.format_type,
            "validated": row.validated,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "hook_line": outline.get("hook", "")[:120] if outline else "",
        })
    return result


def get_generated_script(db: Session, script_id: int) -> dict | None:
    import json
    row = db.query(GeneratedScript).filter_by(id=script_id).first()
    if not row:
        return None
    try:
        outline = json.loads(row.outline) if row.outline else {}
    except Exception:
        outline = {}
    return {
        "id": row.id,
        "topic": row.topic,
        "angle": row.angle,
        "format_type": row.format_type,
        "validated": row.validated,
        "validation_result": row.validation_result,
        "full_script": row.full_script,
        "outline": outline,
        "citations": row.citations or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
