# FormatIQ — CLAUDE.md

## What This Project Is

**FormatIQ** is a YouTube competitor analysis and script generation tool built for a doctor/pharmaceutical health content creator. It scrapes competitor YouTube videos, analyzes them using AI, scores them on 24 "Format Points" (content patterns), and helps generate optimized scripts.

**Working directory:** `c:\Users\mahar\Documents\Projects\ZenJeevani\Youtube Analyzer\formatiq\`

---

## How to Run

**Backend** (Terminal 1):
```
cd formatiq\backend
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (Terminal 2):
```
cd formatiq\frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The `run.bat` file exists but is slow on first run (runs pip install every time).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | React + Vite + Tailwind CSS |
| Video Scraping | YouTube Data API v3 + youtube-transcript-api |
| Format Analysis | Anthropic Claude (claude-sonnet-4-20250514) |
| 5-Angle Analysis | Google Gemini 2.5 Flash |
| Script Generation | Gemini 2.5 Pro → Groq fallback → Claude fallback |
| Channel Style Analysis | Gemini 2.5 Flash |
| Citations | Gemini 2.5 Flash + Google Search grounding |
| Transcripts | youtube-transcript-api (tries hi, en, en-US, en-GB) |

---

## API Keys (in `backend/config.yaml`)

- `youtube_api_key` — YouTube Data API v3
- `gemini_api_key` — Google Gemini (used for everything: 5-angle analysis, style profiling, citations, script generation)
- `gemini_model` — `gemini-2.5-flash` (for 5-angle analysis + style profiling + citations)
- `gemini_script_model` — `gemini-2.5-pro` (for script generation — higher quality)
- `groq_api_key` — Groq (fallback for script generation)
- `groq_model` — `compound-beta`
- `anthropic_api_key` — Claude (last-resort fallback for script generation)
- `claude_model` — `claude-sonnet-4-20250514`

---

## Project Structure

```
formatiq/
├── backend/
│   ├── main.py                        # All FastAPI endpoints
│   ├── database.py                    # SQLAlchemy models + migrations
│   ├── config.yaml                    # API keys + settings
│   ├── config.py                      # Config loader
│   ├── requirements.txt               # Pinned deps (no ranges — avoids backtracking)
│   ├── analyzer/
│   │   ├── claude_analyzer.py         # Claude API wrapper for format analysis
│   │   ├── gemini_analyzer.py         # Gemini: 5-angle analysis + style profiling + citations + script generation
│   │   ├── prompts.py                 # ALL prompts (Claude + Gemini + Groq)
│   │   └── batch_processor.py        # Batch analysis queue
│   ├── scraper/
│   │   ├── youtube_scraper.py         # YouTube Data API scraping (1-year filter applied)
│   │   ├── transcript.py              # youtube-transcript-api wrapper
│   │   ├── keyword_gen.py             # Keyword generation for scraping
│   │   └── news_fetcher.py            # Google News RSS for trending topics
│   ├── recommender/
│   │   ├── recommendation.py          # Next video recommendations
│   │   ├── content_validator.py       # Two-tier competitor validation (1-year filter)
│   │   ├── script_generator.py        # Script generation pipeline (Gemini→Groq→Claude)
│   │   └── gap_analysis.py            # Format gap analysis
│   └── exporters/
│       ├── csv_export.py
│       └── pdf_export.py
├── frontend/
│   └── src/
│       ├── App.jsx                    # Routes
│       ├── components/
│       │   ├── Navbar.jsx             # Nav with: Overview, Format Points, Recommendations, Script Generator, Controls
│       │   ├── VideoCard.jsx          # Video card with "5-Angle" analyze button
│       │   ├── ScoreBar.jsx
│       │   └── RadarChart.jsx
│       └── pages/
│           ├── Overview.jsx           # Dashboard
│           ├── FormatPoints.jsx       # 24 format points list + video grid (1-year filter)
│           ├── VideoDetail.jsx        # Full video analysis + 5-angle display + "Generate Script" button
│           ├── Recommendations.jsx    # AI recommendations
│           ├── ScriptGenerator.jsx    # 3-step script wizard with language toggle
│           └── Controls.jsx          # Channel management, tier settings, own channel style analysis
└── requirements.txt                   # Pinned versions (root level)
```

---

## Database Models (`backend/database.py`)

### Key Tables

**`channels`**
- `id`, `channel_id`, `channel_name`, `subscriber_count`
- `competitor_tier` — `"direct"` | `"market"` | `"own"`
  - `direct` = 2-3 primary pharma/doctor competitor channels (manually tagged in Controls)
  - `market` = broader pool of health channels (default for all auto-created channels)
  - `own` = user's own channel (excluded from competitor analysis, used for style profiling)

**`videos`**
- Standard YouTube metadata + `analysis_status` (`pending`/`analyzing`/`done`/`failed`)
- `transcript_available`, `transcript` (full text, no truncation)
- `published_at` — used for 1-year date filters everywhere
- `duration_seconds` — integer seconds
- `video_type` — `"short"` if `duration_seconds <= 150` (2:30 min), else `"longform"`
- Linked to `format_points` via `format_point_id`

**`video_analyses`**
- `format_point_scores` (JSON dict: `{"1": 7, "2": 3, ...}`)
- `format_point_flags` (JSON dict: `{"1": true, ...}` for scores >= 4)
- `concept_summary`, `script_analysis`, `health_niche_angle`
- `best_moments`, `what_works`, `what_doesnt_work` (JSON arrays)

**`video_angle_analyses`**
- 5-angle analysis results from Gemini 2.5 Flash
- Per angle (villain/hero/virality/credibility/moral_ground): `_present`, `_description`, `_exact_lines`
- `format_point_mapping`, `overall_strength` (1-10)
- `model_used` — set to `"gemini-on-demand"` when auto-analyzed during script generation

**`channel_style_profiles`**
- One row per own-channel — stores the creator's writing style
- `tone_description`, `vocabulary_notes`, `script_structure`, `credibility_signals`
- `topics_covered` (JSON list)
- `raw_profile` (full Gemini JSON including `language_pattern` and `shorts_style`)
- `language_pattern` inside raw_profile: `{detected_language, mixing_style, hindi_script_used, sample_sentence}`
- `shorts_style` inside raw_profile: `{hook_style, cta_pattern, pacing, top_topics, sample_hook}`
- `videos_analyzed` — number of transcripts used

**`generated_scripts`**
- `topic`, `angle`, `format_type` (`shorts`|`longform`)
- `full_script`, `outline` (JSON), `validation_result` (JSON)
- `citations` (JSON list of `{claim, source_name, title, url, year}`)
- `language` — `"english"` | `"hinglish"` | `"hindi"`
- `validated` (bool)

**`format_points`** — 24 fixed format patterns (seeded at startup)

### DB Migration Pattern
`create_all()` only creates NEW tables — it does NOT alter existing ones.
New columns on existing tables need explicit `ALTER TABLE` in `_run_migrations()` in `database.py`.

Current migrations applied:
```python
"ALTER TABLE channels ADD COLUMN competitor_tier VARCHAR(20) DEFAULT 'market'"
"ALTER TABLE generated_scripts ADD COLUMN citations TEXT"
"ALTER TABLE generated_scripts ADD COLUMN language VARCHAR(20) DEFAULT 'hinglish'"
"ALTER TABLE videos ADD COLUMN video_type VARCHAR(10) DEFAULT 'longform'"
```

---

## 24 Format Points

The core scoring system. Each video is scored 0-10 on these patterns:
1. A vs B (comparison), 2. Underdog to Hero, 3. DYK Fact, 4. Tips/Listicle,
5. Is this You?, 6. Myth-busting, 7. Patient Problem Opener, 8. Secret Mix,
9. DYK Villain (habits), 10. Villain (ingredient), 11. Natural Ingredient,
12. DIY Goal-based, 13. Current Affair + DIY, 14. Ingredient Rating,
15. IG Reels Tips/DOs DONTs, 16. How-to + DIY, 17. Product Ratings,
18. Supplement Recommendations, 19. Diagnosis, 20. CGM Format,
21. Podcast Split, 22. Reversal, 23. Reaction Videos, 24. Invite to Contact

---

## 5-Angle Analysis System

Gemini 2.5 Flash analyzes each video's **full transcript** for:
1. **Villain** — what the audience should be angry at/worried about
2. **Hero** — what helps defeat the villain, leaves viewer empowered
3. **Virality** — "wait... what?" moment, broken assumption, surprising fact
4. **Credibility** — numbers, studies, mechanisms, nuanced balance
5. **Moral Ground** — protecting viewers from bad info, not scoring points

**Flow (manual):**
- VideoCard → "5-Angle" button → `POST /api/videos/{id}/analyze-angles`
- Gemini analyzes full transcript → stored in `video_angle_analyses`
- VideoDetail page shows angle cards with present/missing badge + exact quotes
- "Generate Script from this video" button → navigates to `/script-generator?from_video=...&villain=...&hero=...`

**Flow (on-demand during script generation):**
- When user clicks "Generate Script", the system automatically finds 6 matching competitor videos
- Runs Gemini 5-angle analysis on any not yet analyzed → saves to `video_angle_analyses` with `model_used="gemini-on-demand"`
- Results are CACHED — same video won't be re-analyzed on future script generations
- Cost: ~$0.002 per script generation (6 Gemini Flash calls)

---

## Own Channel Style Profiling

Located in: Controls page → "My Channel Style Profile" card

**Flow:**
1. User pastes their YouTube channel URL in the card and clicks Add
2. Channel is added and automatically set to `competitor_tier = "own"`
3. User clicks "Analyze My Channel"
4. Backend re-fetches transcripts for up to 25 videos (clears rate-limit flag first)
5. Fetches top 12 longform + top 8 shorts by view count
6. **Falls back to title+description if no transcripts available** (no longer errors out)
7. Gemini 2.5 Flash reads all text and extracts style profile
8. Profile stored in `channel_style_profiles` table
9. Every future script generation automatically reads this profile and injects it

**Re-analyze:** "Re-analyze" button runs the same flow again. Run it 2-3 times with a few minutes gap to accumulate more transcripts (YouTube rate-limits ~9 fetches per session).

**Language detection:** Profile detects that the creator speaks Hinglish. `hindi_script_used` is set to `"roman"` — Hindi words written in English/Roman alphabet (no Devanagari).

---

## Script Generation Pipeline

**Endpoint:** `POST /api/script/generate`

**Request fields:** `topic`, `angle`, `format_type`, `force`, `language`

**Language options:** `"hinglish"` (default) | `"english"` | `"hindi"`

**Full flow:**
1. `content_validator.py` — validates angle against direct + market tier channels (1-year filter, requires ≥2 keyword matches)
2. `analyze_competitor_videos_for_topic()` — on-demand Gemini analysis of top 6 matching competitor videos
3. `_collect_competitor_intelligence()` — builds rich competitor context block (villains, hooks, gaps)
4. `_get_own_channel_style()` — fetches stored style profile from DB
5. `_build_language_block()` — builds language instructions based on selected language + detected style
6. Builds prompt with: topic + angle + competitor intelligence + style guide + language rules
7. Calls LLM: **Gemini 2.5 Pro** → Groq fallback → Claude fallback
8. `gemini.find_citations()` — Gemini + Google Search grounding finds real PubMed/WHO/CDC links
9. Saves everything to `generated_scripts` table

**Formats:**
- `shorts` — 130-170 words, 60-90 seconds, hook/problem/insight/CTA structure
- `longform` — MINIMUM 2000 words, 8-12 minutes, full narrative with retention hooks

**Token limits:**
- Shorts: 2000 max tokens
- Longform: 10000 max tokens
- Groq: capped at 8000 (raised from 4096)

**Hinglish rules (Roman script — no Devanagari):**
- 50-50 Hindi-English mix, ALL written in Roman/English alphabet
- Hindi words written as: "aaj hum baat karenge", "yaar", "dekho", "bilkul"
- Do NOT use Devanagari anywhere
- Medical/scientific terms always stay in English

**Competitor intelligence block injected into prompt:**
- Exact villain framings competitors used
- Viral hook lines from high-performing videos
- Hero/solution angles they used
- Gaps competitors are NOT covering (differentiation opportunity)

---

## Competitor Validation Logic (`content_validator.py`)

- Queries videos from `direct` and `market` tier channels, last 12 months
- Does NOT require Claude analysis (`analysis_status = "done"`) — title/description matching is enough
- Keyword matching: requires **≥2 significant keywords** to match (stops generic high-view videos from polluting results)
- Stop words filtered out before keyword matching
- If a tier has no channels, it auto-passes (doesn't block the user)

**Important:** All 462 channels from format-point scraping default to `"market"` tier. Tag your 2-3 closest pharma/doctor competitors as `"direct"` in Controls for better validation.

---

## Key API Endpoints

```
GET  /api/overview                          → dashboard stats
GET  /api/format-points                     → list all 24 format points
GET  /api/format-points/{id}/videos         → videos for a format point (1-year filter)
GET  /api/videos/{video_id}                → full video detail
POST /api/videos/{video_id}/analyze-angles  → run 5-angle Gemini analysis
GET  /api/videos/{video_id}/angles          → get stored angle analysis
GET  /api/channels                          → list channels (paginated: ?page=1&page_size=15&search=&tier=)
POST /api/channels                          → add channel
PATCH /api/channels/{id}/tier               → update competitor tier
POST /api/channels/own/analyze-style        → analyze own channel style with Gemini
GET  /api/channels/own/style-profile        → get stored style profile
GET  /api/script/trending-topics            → trending health topics (Google News RSS)
POST /api/script/validate-angle             → {topic, angle} → validation result
POST /api/script/generate                   → {topic, angle, format_type, language} → script + citations
GET  /api/script/history                    → list generated scripts
GET  /api/script/{id}                       → single generated script
POST /api/analyze/start                     → start batch analysis
GET  /api/config                            → current config status
```

---

## Frontend Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Overview | Stats dashboard |
| `/format-points` | FormatPoints | Browse 24 format points, video grid (1-year filter) |
| `/video/:id` | VideoDetail | Full analysis + 5-angle display + "Generate Script" button |
| `/recommendations` | Recommendations | AI-generated video ideas |
| `/script-generator` | ScriptGenerator | 3-step wizard: topic → validate → script |
| `/controls` | Controls | Channels (search + pagination), own channel style, scraping |

---

## Script Generator UI (ScriptGenerator.jsx)

**Step 1 — Choose Topic:**
- Language toggle: `Hinglish | English | Hindi` (default: Hinglish)
- Format toggle: Shorts / Long-form
- Trending Topics tab (Google News RSS) or Enter My Own
- Pre-fill banner if navigated from VideoDetail 5-angle analysis

**Step 2 — Validate Angle:**
- Two-tier validation: Direct competitors + Market pool (both last 12 months only)
- Evidence cards with YouTube links and view counts

**Step 3 — Generated Script:**
- Full Script tab (with [PAUSE], *emphasis*, [CITE] markers)
- Outline tab (section-by-section breakdown)
- Sources tab (real citations from Gemini Google Search grounding, with clickable links)

---

## Controls Page Features

- **Channel list:** Search box + tier filter + pagination (15 per page) — handles 400+ channels
- **My Channel Style Profile card:** Paste own channel URL → Add → "Analyze My Channel" button
- **API config status:** Shows YouTube, Groq, Anthropic key status

---

## 1-Year Date Filter (Applied Everywhere)

- **Scraping:** `publishedAfter` param in YouTube search API; `save_video()` skips videos older than 365 days
- **Validation:** `content_validator.py` only queries videos with `published_at >= now - 365 days`
- **Format Points video grid:** Query filtered to last 12 months
- **On-demand competitor analysis:** Only analyzes videos from last 12 months

---

## Video Type Classification

- `video_type = "short"` if `duration_seconds <= 150` (2 min 30 sec)
- `video_type = "longform"` otherwise
- Set automatically in `save_video()` during scraping
- Style profiling fetches top 12 longform + top 8 shorts separately
- Script prompts inject `shorts_style` from profile when `format_type="shorts"`

---

## Transcript Fetching

- Language order: `["hi", "en", "en-US", "en-GB"]` — Hindi first since creator speaks Hinglish
- Falls back: manual transcript → auto-generated → any available + translate
- Rate limiting (429): sets `_rate_limited` flag, skips all remaining in session
- `analyze-style` endpoint clears `_rate_limited` flag before re-fetching missing transcripts
- Style analysis falls back to title+description if no transcripts available (doesn't error out)

---

## Performance Optimizations Applied

### Backend
- **Overview endpoint** — replaced 24 N+1 queries (one per format point loading all videos) with a single `GROUP BY` SQL query. Was loading 9000+ rows per request.
- **Channels list endpoint** — replaced lazy-loading `len(ch.videos)` (loaded 27,000+ rows) with a subquery join. Now server-side paginated/filtered/searched — returns only 15 rows per request.
- **Trending topics** — 30-minute in-memory cache (`_trending_cache`). First fetch hits Google News RSS; subsequent calls within 30 min return instantly from memory.
- **Recommendations page** — disabled auto-load on mount. Was calling 2 slow AI endpoints every time user navigated to the page.
- **Script Generator page** — default tab changed from "Trending Topics" (triggers Google News fetch) to "Enter My Own" (no API call). Trending only fetches when user explicitly clicks the tab.

### Frontend
- **Channels list** (`ChannelList` component) — now server-side with debounced search (300ms). Previously filtered 463 channels × their videos in the browser.
- **Recommendations** — shows "Generate Recommendations" button instead of auto-loading; only calls API on explicit click.
- **Script Generator Step 1** — opens instantly, no API calls on mount.

---

## Known Issues & Fixes Applied

1. **`competitor_tier` column missing** — Fixed via `_run_migrations()` in `database.py`
2. **`TypeError: Client.__init__() got unexpected keyword argument 'proxies'`** — Fixed by upgrading `anthropic` to `>=0.40.0`
3. **Groq returns JSON in markdown fences** — Fixed by `_parse_llm_json()` that strips fences before parsing
4. **`fastapi==0.104.1` conflicts with `google-genai>=2.0.0`** — Fixed by upgrading fastapi to `0.115.12`
5. **pip dependency resolver extremely slow** — Fixed by pinning exact versions in `requirements.txt`
6. **`youtube_transcript_api` not found** — Install via `pip install youtube-transcript-api`
7. **"No videos with transcripts found" on Analyze My Channel** — Fixed: now re-fetches transcripts on-demand + falls back to descriptions
8. **Validation shows "No competitor data found"** — Fixed: removed `analysis_status == "done"` filter; scraped (pending) videos now count
9. **Wrong channels in validation evidence** — Fixed: requires ≥2 keyword matches, stop words filtered
10. **`UNIQUE constraint failed: video_angle_analyses.video_id`** — Fixed: double-check before insert + rollback+fetch fallback on IntegrityError
11. **Script too short (8-11 lines)** — Fixed: hard minimum word count in prompt, Groq token cap raised 4096→8000, max_tokens raised to 10000
12. **Devanagari in Hinglish scripts** — Fixed: all Hindi now written in Roman script (no Devanagari anywhere)
13. **Channel URL with `?si=` param fails** — Fixed: strip query params before processing
14. **Adding channel was slow (5+ minutes)** — Fixed: add endpoint only fetches channel metadata, not videos
15. **Controls page slow to load** — Fixed: channels API now server-side paginated; no more loading all 463 channels + their videos upfront
16. **Script Generator slow to open** — Fixed: default to "Enter My Own" tab; trending topics only fetch on explicit click + 30-min cache

---

## Requirements (Pinned Versions)

```
fastapi==0.115.12
uvicorn[standard]==0.34.3
sqlalchemy==2.0.23
pydantic==2.5.0
pyyaml==6.0.1
google-api-python-client==2.108.0
youtube-transcript-api==0.6.2
anthropic==0.104.1
groq==1.2.0
google-genai==2.6.0
reportlab==4.0.7
pandas==2.1.3
python-multipart==0.0.6
tqdm==4.66.1
```

---

## Niche & Content Focus

- Target niche: **Health / Nutrition / Wellness** (doctor/pharmaceutical content)
- Content creator is a **doctor** (Dr. Paramjeet Singh) making YouTube videos in Hinglish
- Channels: `@dreducation` and `@dreducationfitness` (own channels, `competitor_tier = "own"`)
- Primary competitors should be tagged as `direct` tier in Controls (currently all are `market`)
- Script language: **Hinglish by default** — Roman script only, no Devanagari
- Script style: conversational, "doctor talking to a friend", NOT robotic/corporate
- Citations must be from: PubMed, WHO, CDC, Mayo Clinic, NEJM, Lancet, NIH, BMJ, Harvard Health
- Credibility signals: references US Medical Library, meta-analysis, research studies
- Unique voice: "Explained in Simple language by a Professional Doctor with Reference from US Medical Library & Latest Research meta analysis"
