"""
FormatIQ — FastAPI backend
"""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer

sys.path.insert(0, os.path.dirname(__file__))

from database import (
    get_db, init_db, Video, VideoAnalysis, FormatPoint,
    Channel, Recommendation, GeneratedScript, VideoAngleAnalysis, ChannelStyleProfile, SessionLocal
)
from config import config
from scraper.youtube_scraper import build_youtube_client, scrape_format_point, scrape_competitor_channel, scrape_channel
from analyzer.claude_analyzer import ClaudeAnalyzer
from analyzer.batch_processor import process_batch
from recommender.recommendation import get_format_point_report, get_next_video_recommendations
from recommender.gap_analysis import compute_gap_analysis
from recommender.content_validator import validate_content_angle
from recommender.script_generator import (
    generate_script, get_trending_topics_for_niche,
    list_generated_scripts, get_generated_script,
)
from recommender.angle_intelligence import get_angle_performance
from exporters.csv_export import export_all_videos_csv, export_format_point_csv
from exporters.pdf_export import generate_format_point_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory progress tracking
_job_progress: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FormatIQ API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_analyzer() -> ClaudeAnalyzer:
    return ClaudeAnalyzer(
        api_key=config["anthropic_api_key"],
        model=config.get("claude_model", "claude-sonnet-4-20250514"),
        max_retries=config.get("max_retries", 3),
    )


def get_youtube():
    return build_youtube_client(config["youtube_api_key"])


# ─── Overview ───────────────────────────────────────────────────────────────

@app.get("/api/overview")
def get_overview(db: Session = Depends(get_db)):
    total_videos = db.query(func.count(Video.id)).scalar()
    analyzed = db.query(func.count(Video.id)).filter(Video.analysis_status == "done").scalar()
    pending = db.query(func.count(Video.id)).filter(Video.analysis_status == "pending").scalar()
    total_channels = db.query(func.count(Channel.id)).scalar()

    # Top format points by avg view count — single aggregated query (no N+1)
    fp_rows = (
        db.query(
            FormatPoint.id,
            FormatPoint.number,
            FormatPoint.name,
            func.count(Video.id).label("video_count"),
            func.avg(Video.view_count).label("avg_views"),
            func.sum(func.cast(Video.analysis_status == "done", Integer)).label("analyzed_count"),
        )
        .outerjoin(Video, Video.format_point_id == FormatPoint.id)
        .group_by(FormatPoint.id)
        .all()
    )
    fp_stats = [
        {
            "id": row.id,
            "number": row.number,
            "name": row.name,
            "video_count": row.video_count or 0,
            "avg_views": round(row.avg_views or 0),
            "analyzed_count": int(row.analyzed_count or 0),
        }
        for row in fp_rows
        if (row.video_count or 0) > 0
    ]
    fp_stats.sort(key=lambda x: x["avg_views"], reverse=True)

    # Recent analyses
    recent = (
        db.query(Video)
        .filter(Video.analysis_status == "done")
        .order_by(desc(Video.scraped_at))
        .limit(10)
        .all()
    )

    return {
        "total_videos": total_videos,
        "analyzed_videos": analyzed,
        "pending_videos": pending,
        "total_channels": total_channels,
        "format_point_stats": fp_stats,
        "recent_analyses": [_video_card(v) for v in recent],
    }


# ─── Format Points ───────────────────────────────────────────────────────────

@app.get("/api/format-points")
def list_format_points(db: Session = Depends(get_db)):
    fps = db.query(FormatPoint).order_by(FormatPoint.number).all()
    result = []
    for fp in fps:
        count = db.query(func.count(Video.id)).filter(Video.format_point_id == fp.id).scalar()
        analyzed = db.query(func.count(Video.id)).filter(
            Video.format_point_id == fp.id, Video.analysis_status == "done"
        ).scalar()
        avg_views = db.query(func.avg(Video.view_count)).filter(
            Video.format_point_id == fp.id
        ).scalar()
        result.append({
            "id": fp.id,
            "number": fp.number,
            "name": fp.name,
            "description": fp.description,
            "video_count": count,
            "analyzed_count": analyzed,
            "avg_views": round(avg_views or 0),
            "keywords": fp.keywords or [],
        })
    return result


@app.get("/api/format-points/{fp_id}/videos")
def get_format_point_videos(
    fp_id: int,
    sort_by: str = "view_count",
    min_views: int = 0,
    channel_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    query = db.query(Video).filter(Video.format_point_id == fp_id).filter(Video.published_at >= one_year_ago)
    if min_views:
        query = query.filter(Video.view_count >= min_views)
    if channel_id:
        query = query.filter(Video.channel_id == channel_id)

    total = query.count()

    if sort_by == "view_count":
        query = query.order_by(desc(Video.view_count))
    elif sort_by == "published_at":
        query = query.order_by(desc(Video.published_at))
    elif sort_by == "score":
        query = query.order_by(desc(Video.view_count))  # fallback

    videos = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "videos": [_video_card(v) for v in videos],
    }


# ─── Videos ─────────────────────────────────────────────────────────────────

@app.get("/api/videos/{video_id}")
def get_video_detail(video_id: str, db: Session = Depends(get_db)):
    v = db.query(Video).filter_by(video_id=video_id).first()
    if not v:
        raise HTTPException(404, "Video not found")

    result = _video_card(v)
    result["description"] = v.description
    result["transcript"] = v.transcript
    result["duration"] = v.duration
    result["format_point"] = {
        "id": v.format_point.id,
        "name": v.format_point.name,
        "number": v.format_point.number,
    } if v.format_point else None

    if v.analysis:
        an = v.analysis
        result["analysis"] = {
            "concept_summary": an.concept_summary,
            "script_analysis": an.script_analysis,
            "format_point_scores": an.format_point_scores,
            "format_point_flags": an.format_point_flags,
            "best_moments": an.best_moments,
            "what_works": an.what_works,
            "what_doesnt_work": an.what_doesnt_work,
            "health_niche_angle": an.health_niche_angle,
            "analyzed_at": an.analyzed_at.isoformat() if an.analyzed_at else None,
        }
    else:
        result["analysis"] = None

    return result


# ─── Recommendations ─────────────────────────────────────────────────────────

@app.get("/api/recommendations/next-video")
def next_video_recommendations(regenerate: bool = False, db: Session = Depends(get_db)):
    analyzer = get_analyzer()
    return get_next_video_recommendations(db, analyzer, regenerate=regenerate)


@app.get("/api/recommendations/gap-analysis")
def gap_analysis(db: Session = Depends(get_db)):
    return compute_gap_analysis(db)


@app.get("/api/recommendations/format-report/{fp_id}")
def format_report(fp_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
    analyzer = get_analyzer()
    return get_format_point_report(db, analyzer, fp_id, regenerate=regenerate)


# ─── 5-Angle Analysis ───────────────────────────────────────────────────────

def get_gemini():
    from analyzer.gemini_analyzer import GeminiAnalyzer
    key = config.get("gemini_api_key", "")
    if not key or key == "YOUR_GEMINI_API_KEY_HERE":
        raise HTTPException(400, "Gemini API key not configured — add gemini_api_key to config.yaml")
    return GeminiAnalyzer(api_key=key, model=config.get("gemini_model", "gemini-2.0-flash"))


@app.post("/api/videos/{video_id}/analyze-angles")
def analyze_video_angles(video_id: str, db: Session = Depends(get_db)):
    v = db.query(Video).filter_by(video_id=video_id).first()
    if not v:
        raise HTTPException(404, "Video not found")

    gemini = get_gemini()
    is_short = (v.duration_seconds or 0) > 0 and (v.duration_seconds or 0) <= 150
    try:
        result = gemini.analyze_angles(
            title=v.title or "",
            description=v.description or "",
            transcript=v.transcript,
            channel_name=v.channel_name or "",
            view_count=v.view_count or 0,
            is_short=is_short,
        )
    except Exception as e:
        logger.error(f"Gemini angle analysis failed for {video_id}: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))

    if not result:
        raise HTTPException(500, "Gemini returned an unparseable response. Please try again.")

    # Upsert angle analysis row
    existing = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
    if existing:
        row = existing
    else:
        row = VideoAngleAnalysis(video_id=v.id)
        db.add(row)

    def _angle(key):
        a = result.get(key, {})
        return a.get("present", False), a.get("description", ""), a.get("exact_lines", [])

    row.villain_present, row.villain_description, row.villain_exact_lines = _angle("villain")
    row.hero_present, row.hero_description, row.hero_exact_lines = _angle("hero")
    row.virality_present, row.virality_description, row.virality_exact_lines = _angle("virality")
    row.credibility_present, row.credibility_description, row.credibility_exact_lines = _angle("credibility")
    row.moral_ground_present, row.moral_ground_description, row.moral_ground_exact_lines = _angle("moral_ground")
    row.format_point_mapping = result.get("format_point_mapping", {})
    row.overall_strength = result.get("overall_strength")
    row.model_used = config.get("gemini_model", "gemini-2.0-flash")

    db.commit()
    db.refresh(row)

    return _angle_analysis_dict(row, result.get("script_inspiration", ""))


@app.get("/api/videos/{video_id}/angles")
def get_video_angles(video_id: str, db: Session = Depends(get_db)):
    v = db.query(Video).filter_by(video_id=video_id).first()
    if not v:
        raise HTTPException(404, "Video not found")
    row = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
    if not row:
        return None
    return _angle_analysis_dict(row)


def _angle_analysis_dict(row: VideoAngleAnalysis, script_inspiration: str = "") -> dict:
    return {
        "villain":      {"present": row.villain_present,      "description": row.villain_description,      "exact_lines": row.villain_exact_lines      or []},
        "hero":         {"present": row.hero_present,         "description": row.hero_description,         "exact_lines": row.hero_exact_lines         or []},
        "virality":     {"present": row.virality_present,     "description": row.virality_description,     "exact_lines": row.virality_exact_lines     or []},
        "credibility":  {"present": row.credibility_present,  "description": row.credibility_description,  "exact_lines": row.credibility_exact_lines  or []},
        "moral_ground": {"present": row.moral_ground_present, "description": row.moral_ground_description, "exact_lines": row.moral_ground_exact_lines or []},
        "format_point_mapping": row.format_point_mapping or {},
        "overall_strength": row.overall_strength,
        "script_inspiration": script_inspiration,
        "analyzed_at": row.analyzed_at.isoformat() if row.analyzed_at else None,
        "model_used": row.model_used,
    }


# ─── Script Generation ──────────────────────────────────────────────────────

class ValidateAngleRequest(BaseModel):
    topic: str
    angle: str = ""


class GenerateScriptRequest(BaseModel):
    topic: str
    angle: str = ""
    format_type: str = "longform"  # "shorts" | "longform"
    force: bool = False
    language: str = "hinglish"  # "english" | "hinglish" | "hindi"


_trending_cache: dict = {"topics": [], "fetched_at": 0}
_TRENDING_TTL = 1800  # 30 minutes

@app.get("/api/script/trending-topics")
def script_trending_topics():
    import time as _time
    now = _time.time()
    if _trending_cache["topics"] and now - _trending_cache["fetched_at"] < _TRENDING_TTL:
        return {"topics": _trending_cache["topics"], "cached": True}
    niche = config.get("script", {}).get("niche", "doctor pharmaceutical health")
    api_key = config.get("news_search_api_key", "")
    topics = get_trending_topics_for_niche(niche=niche, api_key=api_key)
    _trending_cache["topics"] = topics
    _trending_cache["fetched_at"] = now
    return {"topics": topics, "cached": False}


@app.post("/api/script/validate-angle")
def script_validate_angle(req: ValidateAngleRequest, db: Session = Depends(get_db)):
    return validate_content_angle(db, req.topic, req.angle)


@app.post("/api/script/generate")
def script_generate(req: GenerateScriptRequest, db: Session = Depends(get_db)):
    if req.format_type not in ("shorts", "longform"):
        raise HTTPException(400, "format_type must be 'shorts' or 'longform'")
    analyzer = get_analyzer()
    script_cfg = config.get("script", {})
    niche = script_cfg.get("niche", "doctor / pharmaceutical")
    longform_words = script_cfg.get("longform_target_words", 2000)
    try:
        result = generate_script(
            db, analyzer, req.topic, req.format_type,
            angle=req.angle, niche=niche,
            longform_target_words=longform_words,
            force=req.force,
            groq_api_key=config.get("groq_api_key", ""),
            groq_model=config.get("groq_model", "compound-beta"),
            gemini_analyzer=get_gemini(),
            gemini_script_model=config.get("gemini_script_model", "gemini-2.5-pro"),
            language=req.language,
        )
    except Exception as e:
        logger.error(f"Script generation error: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))
    return result


@app.get("/api/script/history")
def script_history(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    scripts = list_generated_scripts(db, limit=limit, offset=offset)
    total = db.query(GeneratedScript).count()
    return {"total": total, "scripts": scripts}


@app.get("/api/script/{script_id}")
def script_detail(script_id: int, db: Session = Depends(get_db)):
    result = get_generated_script(db, script_id)
    if not result:
        raise HTTPException(404, "Script not found")
    return result


# ─── Scraping Controls ───────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    format_point_ids: list[int] = []  # empty = all
    competitor_channels: list[str] = []
    videos_per_format: int = 50
    custom_keywords: dict[str, list[str]] = {}


class AnalyzeRequest(BaseModel):
    format_point_id: Optional[int] = None
    batch_size: int = 10


@app.post("/api/scrape/start")
async def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = f"scrape_{int(asyncio.get_event_loop().time())}"
    _job_progress[job_id] = {"status": "running", "progress": 0, "total": 0, "message": "Starting..."}
    background_tasks.add_task(_run_scrape, job_id, req)
    return {"job_id": job_id}


async def _run_scrape(job_id: str, req: ScrapeRequest):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_scrape_sync, job_id, req)


def _run_scrape_sync(job_id: str, req: ScrapeRequest):
    db = SessionLocal()
    try:
        youtube = get_youtube()
        fps = db.query(FormatPoint).all()
        if req.format_point_ids:
            fps = [fp for fp in fps if fp.id in req.format_point_ids]

        total_fps = len(fps)
        total_videos_target = total_fps * req.videos_per_format
        _job_progress[job_id]["total"] = total_videos_target
        videos_saved_so_far = [0]

        for i, fp in enumerate(fps):
            fp_label = f"({i+1}/{total_fps}) {fp.name}"
            _job_progress[job_id]["message"] = f"Scraping: {fp_label}"

            def video_cb(vid_num, vid_total, _fp_label=fp_label):
                _job_progress[job_id]["progress"] = videos_saved_so_far[0] + vid_num
                _job_progress[job_id]["message"] = f"Scraping: {_fp_label} — video {vid_num}/{vid_total}"

            custom_kws = req.custom_keywords.get(str(fp.number))
            count = scrape_format_point(db, youtube, fp, req.videos_per_format, custom_kws, progress_callback=video_cb)
            videos_saved_so_far[0] += count
            _job_progress[job_id]["progress"] = videos_saved_so_far[0]

            for ch_url in req.competitor_channels:
                scrape_competitor_channel(db, youtube, ch_url, fp, req.videos_per_format // 2)

        _job_progress[job_id]["status"] = "done"
        _job_progress[job_id]["message"] = f"Scraping complete — {videos_saved_so_far[0]} videos saved"
        _job_progress[job_id]["progress"] = videos_saved_so_far[0]
        _job_progress[job_id]["total"] = videos_saved_so_far[0]
    except Exception as e:
        _job_progress[job_id]["status"] = "error"
        _job_progress[job_id]["message"] = str(e)
        logger.error(f"Scrape job error: {e}")
    finally:
        db.close()


class ScrapeChannelRequest(BaseModel):
    channel_url_or_id: str
    max_videos: int = 200


@app.post("/api/scrape/channel")
async def scrape_channel_endpoint(req: ScrapeChannelRequest, background_tasks: BackgroundTasks):
    job_id = f"channel_{int(asyncio.get_event_loop().time())}"
    _job_progress[job_id] = {"status": "running", "progress": 0, "total": 0, "message": "Starting channel scrape..."}
    background_tasks.add_task(_run_channel_scrape, job_id, req)
    return {"job_id": job_id}


def _run_channel_scrape(job_id: str, req: ScrapeChannelRequest):
    db = SessionLocal()
    try:
        youtube = get_youtube()

        def progress_cb(current, total):
            _job_progress[job_id]["progress"] = current
            _job_progress[job_id]["total"] = total

        result = scrape_channel(db, youtube, req.channel_url_or_id, req.max_videos, progress_cb)
        if "error" in result:
            _job_progress[job_id]["status"] = "error"
            _job_progress[job_id]["message"] = result["error"]
        else:
            _job_progress[job_id]["status"] = "done"
            _job_progress[job_id]["message"] = f"Done — {result['saved']} videos saved from {result.get('channel_name', '')}"
            _job_progress[job_id]["result"] = result
    except Exception as e:
        _job_progress[job_id]["status"] = "error"
        _job_progress[job_id]["message"] = str(e)
        logger.error(f"Channel scrape error: {e}")
    finally:
        db.close()


@app.post("/api/analyze/start")
async def start_analysis(req: AnalyzeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    pending = db.query(func.count(Video.id)).filter(Video.analysis_status == "pending")
    if req.format_point_id:
        pending = pending.filter(Video.format_point_id == req.format_point_id)
    pending_count = pending.scalar()

    analyzer = get_analyzer()
    estimate = analyzer.estimate_cost(pending_count)

    job_id = f"analyze_{int(asyncio.get_event_loop().time())}"
    _job_progress[job_id] = {
        "status": "running", "progress": 0,
        "total": pending_count, "message": "Starting analysis...",
        "estimate": estimate,
    }
    background_tasks.add_task(_run_analysis, job_id, req)
    return {"job_id": job_id, "pending_count": pending_count, "estimate": estimate}


async def _run_analysis(job_id: str, req: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_analysis_sync, job_id, req)


def _run_analysis_sync(job_id: str, req: AnalyzeRequest):
    db = SessionLocal()
    try:
        analyzer = get_analyzer()

        def progress_cb(current, total, title):
            _job_progress[job_id]["progress"] = current
            _job_progress[job_id]["total"] = total
            _job_progress[job_id]["message"] = f"Analyzing: {title[:60]}"

        result = process_batch(
            db, analyzer, req.batch_size, req.format_point_id, progress_callback=progress_cb
        )
        _job_progress[job_id]["status"] = "done"
        _job_progress[job_id]["result"] = result
        _job_progress[job_id]["message"] = f"Done. {result['analyzed']} analyzed, {result['failed']} failed."
    except Exception as e:
        _job_progress[job_id]["status"] = "error"
        _job_progress[job_id]["message"] = str(e)
        logger.error(f"Analysis job error: {e}")
    finally:
        db.close()


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    if job_id not in _job_progress:
        raise HTTPException(404, "Job not found")
    return _job_progress[job_id]


# ─── Channels ────────────────────────────────────────────────────────────────

class AddChannelRequest(BaseModel):
    channel_url_or_id: str


@app.get("/api/channels")
def list_channels(
    db: Session = Depends(get_db),
    search: str = Query("", alias="search"),
    tier: str = Query("", alias="tier"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
):
    # Single query: channels + video count via subquery (no lazy loading)
    video_count_sq = (
        db.query(Video.channel_id, func.count(Video.id).label("video_count"))
        .group_by(Video.channel_id)
        .subquery()
    )

    q = (
        db.query(Channel, func.coalesce(video_count_sq.c.video_count, 0).label("video_count"))
        .outerjoin(video_count_sq, Channel.id == video_count_sq.c.channel_id)
    )

    if search:
        q = q.filter(Channel.channel_name.ilike(f"%{search}%"))
    if tier and tier != "all":
        q = q.filter(Channel.competitor_tier == tier)

    total = q.count()
    rows = q.order_by(Channel.channel_name).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "channels": [
            {
                "id": ch.id,
                "channel_id": ch.channel_id,
                "channel_name": ch.channel_name,
                "channel_url": ch.channel_url,
                "subscriber_count": ch.subscriber_count,
                "competitor_tier": ch.competitor_tier or "market",
                "video_count": vc,
                "added_at": ch.added_at.isoformat() if ch.added_at else None,
            }
            for ch, vc in rows
        ],
    }


class UpdateChannelTierRequest(BaseModel):
    competitor_tier: str  # "direct" | "market" | "own"


@app.post("/api/channels/own/analyze-style")
def analyze_own_channel_style(db: Session = Depends(get_db)):
    """
    Analyze all videos from the creator's own channel (tier='own') to extract
    tone, vocabulary, script structure, and credibility signals.
    Stores the result in channel_style_profiles table.
    """
    gemini = get_gemini()
    if not gemini:
        raise HTTPException(400, "Gemini API key not configured. Add gemini_api_key to config.yaml")

    own_channel = db.query(Channel).filter_by(competitor_tier="own").first()
    if not own_channel:
        raise HTTPException(400, "No channel marked as 'own' tier. Go to Controls and set your channel tier to 'own'.")

    SHORT_THRESHOLD = 150  # 2:30 minutes

    # Re-fetch missing transcripts for own channel videos (handles rate-limit skips from scraping)
    from scraper.transcript import get_transcript, _rate_limited
    _rate_limited.clear()  # reset rate-limit flag so we can retry
    missing_transcript_videos = (
        db.query(Video)
        .filter(Video.channel_id == own_channel.id)
        .filter((Video.transcript_available == False) | (Video.transcript == None))
        .order_by(desc(Video.view_count))
        .limit(25)
        .all()
    )
    import time as _time
    for mv in missing_transcript_videos:
        if _rate_limited.is_set():
            break
        try:
            txt, avail = get_transcript(mv.video_id, languages=["hi", "en", "en-US", "en-GB"])
            if avail and txt:
                mv.transcript = txt
                mv.transcript_available = True
                db.commit()
            _time.sleep(0.5)
        except Exception:
            pass

    def _best_text(v: Video) -> str | None:
        """Return transcript if available, otherwise fall back to title + description."""
        if v.transcript:
            return v.transcript
        if v.description and len(v.description) > 100:
            return f"[Title]: {v.title}\n[Description]: {v.description}"
        return None

    # Fetch long-form videos (top 12 by views) — prefer transcripts, fall back to descriptions
    longform_videos = (
        db.query(Video)
        .filter(Video.channel_id == own_channel.id)
        .filter(Video.duration_seconds > SHORT_THRESHOLD)
        .order_by(desc(Video.view_count))
        .limit(12)
        .all()
    )

    # Fetch shorts (top 8 by views)
    shorts_videos = (
        db.query(Video)
        .filter(Video.channel_id == own_channel.id)
        .filter(Video.duration_seconds <= SHORT_THRESHOLD)
        .filter(Video.duration_seconds > 0)
        .order_by(desc(Video.view_count))
        .limit(8)
        .all()
    )

    if not longform_videos and not shorts_videos:
        raise HTTPException(400, f"No videos found for '{own_channel.channel_name}'. Scrape the channel first.")

    longform_transcripts = [t for v in longform_videos if (t := _best_text(v))]
    shorts_transcripts = [t for v in shorts_videos if (t := _best_text(v))]

    if not longform_transcripts and not shorts_transcripts:
        raise HTTPException(400, f"No usable text found for '{own_channel.channel_name}'. Videos have no transcripts or descriptions.")

    try:
        profile_data = gemini.analyze_channel_style(
            longform_transcripts or shorts_transcripts,
            own_channel.channel_name,
            shorts_transcripts=shorts_transcripts if shorts_transcripts else None,
        )
    except Exception as e:
        raise HTTPException(500, f"Gemini analysis failed: {e}")

    if not profile_data:
        raise HTTPException(500, "Gemini returned empty style profile")

    total_analyzed = len(longform_transcripts) + len(shorts_transcripts)

    # Save or update the style profile
    existing = db.query(ChannelStyleProfile).filter_by(channel_id=own_channel.id).first()
    if existing:
        existing.tone_description = profile_data.get("tone_description", "")
        existing.vocabulary_notes = str(profile_data.get("vocabulary", {}))
        existing.script_structure = str(profile_data.get("script_structure", {}))
        existing.topics_covered = profile_data.get("topics_covered", [])
        existing.credibility_signals = profile_data.get("credibility_style", "")
        existing.raw_profile = profile_data
        existing.analyzed_at = __import__("datetime").datetime.utcnow()
        existing.model_used = config.get("gemini_model", "gemini-2.5-flash")
        existing.videos_analyzed = total_analyzed
    else:
        profile_row = ChannelStyleProfile(
            channel_id=own_channel.id,
            tone_description=profile_data.get("tone_description", ""),
            vocabulary_notes=str(profile_data.get("vocabulary", {})),
            script_structure=str(profile_data.get("script_structure", {})),
            topics_covered=profile_data.get("topics_covered", []),
            credibility_signals=profile_data.get("credibility_style", ""),
            raw_profile=profile_data,
            model_used=config.get("gemini_model", "gemini-2.5-flash"),
            videos_analyzed=total_analyzed,
        )
        db.add(profile_row)

    db.commit()
    return {
        "channel_name": own_channel.channel_name,
        "longform_analyzed": len(longform_transcripts),
        "shorts_analyzed": len(shorts_transcripts),
        "videos_analyzed": total_analyzed,
        "profile": profile_data,
    }


@app.get("/api/channels/own/style-profile")
def get_own_channel_style(db: Session = Depends(get_db)):
    """Get the stored style profile for the own channel."""
    own_channel = db.query(Channel).filter_by(competitor_tier="own").first()
    if not own_channel:
        return {"profile": None, "message": "No own channel configured"}
    profile = db.query(ChannelStyleProfile).filter_by(channel_id=own_channel.id).first()
    if not profile:
        return {"profile": None, "channel_name": own_channel.channel_name, "message": "Style not analyzed yet"}
    return {
        "channel_name": own_channel.channel_name,
        "videos_analyzed": profile.videos_analyzed,
        "analyzed_at": profile.analyzed_at.isoformat() if profile.analyzed_at else None,
        "profile": profile.raw_profile,
    }


@app.get("/api/channels/own/angle-performance")
def own_angle_performance(topic: str = "", db: Session = Depends(get_db)):
    """Return angle performance scores and AI recommendation for own channel videos.
    Pass ?topic=high+blood+pressure to get topic-specific recommendations."""
    try:
        gemini = get_gemini()
    except Exception:
        gemini = None
    return get_angle_performance(db, gemini_analyzer=gemini, topic=topic)


@app.post("/api/channels/own/bulk-analyze-angles")
def bulk_analyze_own_angles(db: Session = Depends(get_db)):
    """Run 5-angle Gemini analysis on all un-analyzed own-channel videos."""
    gemini = get_gemini()

    own_videos = (
        db.query(Video)
        .join(Channel, Video.channel_id == Channel.id)
        .filter(Channel.competitor_tier == "own")
        .all()
    )
    if not own_videos:
        raise HTTPException(404, "No own-channel videos found. Add your channel in Controls first.")

    analyzed_ids = {
        row.video_id for row in db.query(VideoAngleAnalysis).all()
    }
    to_analyze = [v for v in own_videos if v.id not in analyzed_ids]

    if not to_analyze:
        return {"message": "All own-channel videos are already analyzed.", "analyzed": 0, "total": len(own_videos)}

    success = 0
    failed = 0
    for v in to_analyze:
        if not v.transcript and not v.title:
            failed += 1
            continue
        try:
            is_short = (v.duration_seconds or 0) <= 150
            result = gemini.analyze_angles(
                title=v.title or "",
                description=v.description or "",
                transcript=v.transcript,
                channel_name=v.channel_name or "",
                view_count=v.view_count or 0,
                is_short=is_short,
            )
            if not result:
                failed += 1
                continue

            existing = db.query(VideoAngleAnalysis).filter_by(video_id=v.id).first()
            row = existing or VideoAngleAnalysis(video_id=v.id)
            if not existing:
                db.add(row)

            def _a(key):
                d = result.get(key, {})
                return d.get("present", False), d.get("description", ""), d.get("exact_lines", [])

            row.villain_present,     row.villain_description,     row.villain_exact_lines     = _a("villain")
            row.hero_present,        row.hero_description,        row.hero_exact_lines        = _a("hero")
            row.virality_present,    row.virality_description,    row.virality_exact_lines    = _a("virality")
            row.credibility_present, row.credibility_description, row.credibility_exact_lines = _a("credibility")
            row.moral_ground_present,row.moral_ground_description,row.moral_ground_exact_lines= _a("moral_ground")
            row.format_point_mapping = result.get("format_point_mapping", {})
            row.overall_strength = result.get("overall_strength")
            row.model_used = config.get("gemini_model", "gemini-2.0-flash")
            db.commit()
            success += 1
            logger.info(f"Bulk analyzed own video: {v.title[:60]}")
        except Exception as e:
            db.rollback()
            failed += 1
            logger.warning(f"Bulk analyze failed for video {v.id}: {e}")

    return {
        "message": f"Analyzed {success} videos successfully. {failed} failed or skipped.",
        "analyzed": success,
        "failed": failed,
        "total": len(own_videos),
        "already_done": len(own_videos) - len(to_analyze),
    }


@app.patch("/api/channels/{channel_id}/tier")
def update_channel_tier(channel_id: int, req: UpdateChannelTierRequest, db: Session = Depends(get_db)):
    if req.competitor_tier not in ("direct", "market", "own"):
        raise HTTPException(400, "competitor_tier must be 'direct', 'market', or 'own'")
    ch = db.query(Channel).filter_by(id=channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")
    ch.competitor_tier = req.competitor_tier
    db.commit()
    return {"id": ch.id, "channel_name": ch.channel_name, "competitor_tier": ch.competitor_tier}


@app.post("/api/channels")
def add_channel(req: AddChannelRequest, db: Session = Depends(get_db)):
    youtube = get_youtube()
    from scraper.youtube_scraper import extract_channel_id, get_or_create_channel
    ch_id = extract_channel_id(req.channel_url_or_id, youtube)
    if not ch_id:
        raise HTTPException(400, "Could not resolve channel ID")

    # Fetch only channel metadata — no video listing
    try:
        resp = youtube.channels().list(
            part="snippet,statistics",
            id=ch_id,
        ).execute()
        items = resp.get("items", [])
        if not items:
            raise HTTPException(400, "Channel not found on YouTube")
        snippet = items[0].get("snippet", {})
        stats = items[0].get("statistics", {})
        ch_data = {
            "title": snippet.get("title", ""),
            "subscriberCount": stats.get("subscriberCount", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"YouTube API error: {e}")

    ch = get_or_create_channel(db, ch_id, ch_data)
    return {"id": ch.id, "channel_id": ch.channel_id, "channel_name": ch.channel_name}


# ─── Exports ────────────────────────────────────────────────────────────────

@app.get("/api/export/csv")
def export_csv(db: Session = Depends(get_db)):
    data = export_all_videos_csv(db)
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=formatiq_all_videos.csv"},
    )


@app.get("/api/export/csv/{fp_id}")
def export_fp_csv(fp_id: int, db: Session = Depends(get_db)):
    data = export_format_point_csv(db, fp_id)
    fp = db.query(FormatPoint).filter_by(id=fp_id).first()
    name = fp.name.replace(" ", "_") if fp else str(fp_id)
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=formatiq_{name}.csv"},
    )


@app.get("/api/export/pdf/{fp_id}")
def export_pdf(fp_id: int, db: Session = Depends(get_db)):
    data = generate_format_point_pdf(db, fp_id)
    fp = db.query(FormatPoint).filter_by(id=fp_id).first()
    name = fp.name.replace(" ", "_") if fp else str(fp_id)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=formatiq_report_{name}.pdf"},
    )


# ─── Config ────────────────────────────────────────────────────────────────

@app.get("/api/config")
def get_config_info():
    groq_key = config.get("groq_api_key", "")
    return {
        "niche": config.get("niche"),
        "videos_per_format_point": config.get("videos_per_format_point", 50),
        "claude_model": config.get("claude_model"),
        "groq_model": config.get("groq_model", "compound-beta"),
        "youtube_api_configured": bool(config.get("youtube_api_key") and config["youtube_api_key"] != "YOUR_YOUTUBE_API_KEY_HERE"),
        "anthropic_api_configured": bool(config.get("anthropic_api_key") and config["anthropic_api_key"] != "YOUR_ANTHROPIC_API_KEY_HERE"),
        "groq_api_configured": bool(groq_key and groq_key != "YOUR_GROQ_API_KEY_HERE"),
        "gemini_api_configured": bool(config.get("gemini_api_key") and config.get("gemini_api_key") != "YOUR_GEMINI_API_KEY_HERE"),
        "gemini_model": config.get("gemini_model", "gemini-2.0-flash"),
        "competitor_channels": config.get("competitor_channels", []),
    }


@app.get("/api/analyze/estimate")
def estimate_analysis_cost(format_point_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(func.count(Video.id)).filter(Video.analysis_status == "pending")
    if format_point_id:
        query = query.filter(Video.format_point_id == format_point_id)
    count = query.scalar()
    analyzer = get_analyzer()
    return analyzer.estimate_cost(count)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _video_card(v: Video) -> dict:
    top_scores = {}
    if v.analysis and v.analysis.format_point_scores:
        sorted_scores = sorted(v.analysis.format_point_scores.items(), key=lambda x: x[1], reverse=True)
        top_scores = {k: val for k, val in sorted_scores[:3]}

    return {
        "id": v.id,
        "video_id": v.video_id,
        "title": v.title,
        "channel_name": v.channel_name,
        "view_count": v.view_count,
        "like_count": v.like_count,
        "comment_count": v.comment_count,
        "thumbnail_url": v.thumbnail_url,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "duration_seconds": v.duration_seconds,
        "transcript_available": v.transcript_available,
        "analysis_status": v.analysis_status,
        "top_format_scores": top_scores,
        "format_point_id": v.format_point_id,
        "youtube_url": f"https://www.youtube.com/watch?v={v.video_id}",
        "has_angle_analysis": v.angle_analysis is not None,
        "video_type": v.video_type or "longform",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
