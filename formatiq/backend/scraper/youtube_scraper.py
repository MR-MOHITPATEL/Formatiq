"""
YouTube Data API v3 scraper for FormatIQ.
Searches by keywords and pulls from competitor channels.
"""
import re
import logging
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from database import Video, Channel, FormatPoint
from scraper.transcript import get_transcript
from scraper.keyword_gen import get_keywords_for_format

logger = logging.getLogger(__name__)

QUOTA_COST = {
    "search": 100,
    "videos": 1,
    "channels": 1,
}


class QuotaTracker:
    def __init__(self, daily_limit: int = 9500):
        self.used = 0
        self.daily_limit = daily_limit

    def check(self, cost: int) -> bool:
        return self.used + cost <= self.daily_limit

    def consume(self, cost: int):
        self.used += cost

    @property
    def remaining(self) -> int:
        return self.daily_limit - self.used


quota = QuotaTracker()


def build_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def parse_duration(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, iso_duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    return h * 3600 + mins * 60 + secs


def extract_channel_id(url_or_id: str, youtube) -> str | None:
    """Resolve a channel URL or handle to a channel ID."""
    # Strip query params and fragments (e.g. ?si=..., #anchor)
    url_or_id = url_or_id.split("?")[0].split("#")[0].strip()

    if re.match(r"^UC[a-zA-Z0-9_-]{22}$", url_or_id):
        return url_or_id

    # Try to extract from URL patterns
    patterns = [
        r"youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})",
        r"youtube\.com/@([a-zA-Z0-9_.-]+)",
        r"youtube\.com/c/([a-zA-Z0-9_.-]+)",
        r"youtube\.com/user/([a-zA-Z0-9_.-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            handle_or_id = m.group(1)
            if handle_or_id.startswith("UC"):
                return handle_or_id
            # Try forHandle with and without @ prefix
            for handle_variant in [handle_or_id, f"@{handle_or_id}"]:
                try:
                    resp = youtube.channels().list(
                        part="id", forHandle=handle_variant
                    ).execute()
                    items = resp.get("items", [])
                    if items:
                        return items[0]["id"]
                except Exception:
                    pass
            # Fallback: forUsername
            try:
                resp = youtube.channels().list(
                    part="id", forUsername=handle_or_id
                ).execute()
                items = resp.get("items", [])
                if items:
                    return items[0]["id"]
            except Exception:
                pass
            # Last resort: search by channel name
            try:
                resp = youtube.search().list(
                    part="snippet", q=handle_or_id, type="channel", maxResults=1
                ).execute()
                items = resp.get("items", [])
                if items:
                    return items[0]["snippet"]["channelId"]
            except Exception:
                pass
            # Final fallback: scrape channel page HTML for embedded channel ID
            try:
                import urllib.request
                page_url = f"https://www.youtube.com/@{handle_or_id}"
                req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp_html:
                    html = resp_html.read().decode("utf-8", errors="ignore")
                for pattern in [r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                                 r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                                 r'channel/(UC[a-zA-Z0-9_-]{22})']:
                    m2 = re.search(pattern, html)
                    if m2:
                        return m2.group(1)
            except Exception:
                pass
    return None


def get_or_create_channel(db: Session, channel_id: str, channel_data: dict) -> Channel:
    ch = db.query(Channel).filter_by(channel_id=channel_id).first()
    if ch:
        return ch
    ch = Channel(
        channel_id=channel_id,
        channel_name=channel_data.get("title", ""),
        channel_url=f"https://www.youtube.com/channel/{channel_id}",
        subscriber_count=int(channel_data.get("subscriberCount", 0) or 0),
        is_competitor=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def fetch_video_details(youtube, video_ids: list[str]) -> list[dict]:
    """Batch fetch video statistics and content details."""
    if not video_ids:
        return []
    results = []
    # YouTube API accepts max 50 per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            ).execute()
            quota.consume(QUOTA_COST["videos"] * len(batch))
            results.extend(resp.get("items", []))
        except HttpError as e:
            logger.error(f"Error fetching video details: {e}")
        time.sleep(0.2)
    return results


ONE_YEAR_AGO_RFC3339 = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")


def search_videos(youtube, query: str, max_results: int = 20) -> list[str]:
    """Search YouTube and return video IDs. Only fetches videos from the past 12 months."""
    if not quota.check(QUOTA_COST["search"]):
        logger.warning("YouTube quota near limit, skipping search")
        return []

    video_ids = []
    try:
        resp = youtube.search().list(
            part="id",
            q=query,
            type="video",
            maxResults=min(max_results, 50),
            relevanceLanguage="en",
            videoDuration="medium",  # 4-20 min, skip shorts
            publishedAfter=ONE_YEAR_AGO_RFC3339,
        ).execute()
        quota.consume(QUOTA_COST["search"])
        for item in resp.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                video_ids.append(item["id"]["videoId"])

        # Handle pagination if we need more
        next_page = resp.get("nextPageToken")
        while next_page and len(video_ids) < max_results:
            if not quota.check(QUOTA_COST["search"]):
                break
            resp = youtube.search().list(
                part="id",
                q=query,
                type="video",
                maxResults=min(50, max_results - len(video_ids)),
                pageToken=next_page,
                relevanceLanguage="en",
            ).execute()
            quota.consume(QUOTA_COST["search"])
            for item in resp.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    video_ids.append(item["id"]["videoId"])
            next_page = resp.get("nextPageToken")

    except HttpError as e:
        if e.resp.status == 403:
            logger.error("YouTube API quota exceeded!")
        else:
            logger.error(f"Search error: {e}")

    return video_ids[:max_results]


def get_channel_videos(youtube, channel_id: str, max_results: int = 50) -> list[str]:
    """Get recent videos from a specific channel."""
    video_ids = []
    try:
        # Get uploads playlist ID
        resp = youtube.channels().list(
            part="contentDetails,snippet,statistics",
            id=channel_id,
        ).execute()
        quota.consume(QUOTA_COST["channels"])

        if not resp.get("items"):
            return []

        ch_data = resp["items"][0]
        uploads_playlist = ch_data["contentDetails"]["relatedPlaylists"]["uploads"]

        # Fetch playlist items
        next_page = None
        while len(video_ids) < max_results:
            params = dict(
                part="contentDetails",
                playlistId=uploads_playlist,
                maxResults=min(50, max_results - len(video_ids)),
            )
            if next_page:
                params["pageToken"] = next_page

            pl_resp = youtube.playlistItems().list(**params).execute()
            quota.consume(1)

            for item in pl_resp.get("items", []):
                video_ids.append(item["contentDetails"]["videoId"])

            next_page = pl_resp.get("nextPageToken")
            if not next_page:
                break

        return video_ids, ch_data["snippet"], ch_data.get("statistics", {})

    except HttpError as e:
        logger.error(f"Error fetching channel videos for {channel_id}: {e}")
        return [], {}, {}


def save_video(
    db: Session,
    video_data: dict,
    channel_obj: Channel,
    transcript_text: str | None,
    transcript_available: bool,
    format_point: FormatPoint | None = None,
) -> Video | None:
    """Save a video to the database, skip if already exists."""
    vid_id = video_data["id"]

    existing = db.query(Video).filter_by(video_id=vid_id).first()
    if existing:
        return existing

    snippet = video_data.get("snippet", {})
    stats = video_data.get("statistics", {})
    content = video_data.get("contentDetails", {})

    pub_at = None
    if snippet.get("publishedAt"):
        try:
            pub_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
        except Exception:
            pass

    # Skip videos older than 1 year
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    if pub_at and pub_at.replace(tzinfo=timezone.utc) < cutoff:
        return None

    duration_iso = content.get("duration", "PT0S")
    dur_seconds = parse_duration(duration_iso)

    SHORT_THRESHOLD = 150  # 2:30 minutes in seconds

    video = Video(
        video_id=vid_id,
        title=snippet.get("title", ""),
        description=(snippet.get("description", "") or "")[:5000],
        thumbnail_url=(
            snippet.get("thumbnails", {}).get("high", {}).get("url")
            or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
        ),
        channel_id=channel_obj.id,
        channel_name=snippet.get("channelTitle", ""),
        view_count=int(stats.get("viewCount", 0) or 0),
        like_count=int(stats.get("likeCount", 0) or 0),
        comment_count=int(stats.get("commentCount", 0) or 0),
        published_at=pub_at,
        duration=duration_iso,
        duration_seconds=dur_seconds,
        transcript=transcript_text,
        transcript_available=transcript_available,
        format_point_id=format_point.id if format_point else None,
        analysis_status="pending",
        video_type="short" if dur_seconds > 0 and dur_seconds <= SHORT_THRESHOLD else "longform",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def scrape_format_point(
    db: Session,
    youtube,
    format_point: FormatPoint,
    target_count: int = 50,
    custom_keywords: list[str] | None = None,
    progress_callback=None,
) -> int:
    """Scrape videos for a single format point. Returns count of new videos saved."""
    keywords = get_keywords_for_format(format_point.number, custom_keywords)
    all_video_ids = set()

    # Collect video IDs via keyword search
    per_keyword = max(10, target_count // len(keywords))
    for kw in keywords:
        if len(all_video_ids) >= target_count * 1.5:
            break
        ids = search_videos(youtube, kw, max_results=per_keyword)
        all_video_ids.update(ids)
        time.sleep(0.5)

    # Fetch details in batches
    id_list = list(all_video_ids)[:target_count + 20]
    video_details = fetch_video_details(youtube, id_list)

    saved = 0
    for i, vd in enumerate(video_details[:target_count]):
        try:
            ch_id = vd["snippet"]["channelId"]
            ch_snip = {"title": vd["snippet"].get("channelTitle", "")}
            channel_obj = get_or_create_channel(db, ch_id, ch_snip)

            transcript_text, transcript_available = get_transcript(vd["id"])

            save_video(db, vd, channel_obj, transcript_text, transcript_available, format_point)
            saved += 1

            if progress_callback:
                progress_callback(i + 1, len(video_details[:target_count]))
        except Exception as e:
            logger.error(f"Error saving video {vd.get('id')}: {e}")

        time.sleep(0.1)

    return saved


def scrape_channel(
    db: Session,
    youtube,
    channel_url_or_id: str,
    max_videos: int = 200,
    progress_callback=None,
) -> dict:
    """Scrape all videos from a channel without format point assignment."""
    ch_id = extract_channel_id(channel_url_or_id, youtube)
    if not ch_id:
        return {"saved": 0, "error": f"Could not resolve channel: {channel_url_or_id}"}

    video_ids, ch_snippet, ch_stats = get_channel_videos(youtube, ch_id, max_results=max_videos)
    if not video_ids:
        return {"saved": 0, "channel_name": ch_snippet.get("title", ch_id)}

    ch_data = {**ch_snippet, **ch_stats}
    channel_obj = get_or_create_channel(db, ch_id, ch_data)

    video_details = fetch_video_details(youtube, list(video_ids)[:max_videos])
    saved = 0
    for i, vd in enumerate(video_details):
        try:
            transcript_text, transcript_available = get_transcript(vd["id"])
            result = save_video(db, vd, channel_obj, transcript_text, transcript_available)
            if result:
                saved += 1
            if progress_callback:
                progress_callback(i + 1, len(video_details))
        except Exception as e:
            logger.error(f"Error saving channel video {vd.get('id')}: {e}")
        time.sleep(0.1)

    return {"saved": saved, "channel_name": ch_snippet.get("title", ch_id), "channel_id": ch_id}


def scrape_competitor_channel(
    db: Session,
    youtube,
    channel_url_or_id: str,
    format_point: FormatPoint,
    max_videos: int = 50,
) -> int:
    """Pull videos from a competitor channel and tag them to a format point."""
    ch_id = extract_channel_id(channel_url_or_id, youtube)
    if not ch_id:
        logger.warning(f"Could not resolve channel ID for: {channel_url_or_id}")
        return 0

    video_ids, ch_snippet, ch_stats = get_channel_videos(youtube, ch_id, max_results=max_videos)
    if not video_ids:
        return 0

    ch_data = {**ch_snippet, **ch_stats}
    channel_obj = get_or_create_channel(db, ch_id, ch_data)

    video_details = fetch_video_details(youtube, video_ids[:max_videos])
    saved = 0
    for vd in video_details:
        try:
            transcript_text, transcript_available = get_transcript(vd["id"])
            save_video(db, vd, channel_obj, transcript_text, transcript_available, format_point)
            saved += 1
        except Exception as e:
            logger.error(f"Error saving competitor video {vd.get('id')}: {e}")
        time.sleep(0.1)

    return saved
