import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ExternalLink, ArrowLeft, Eye, ThumbsUp, MessageSquare, CheckCircle, XCircle, Swords, Shield, Zap, BadgeCheck, Heart, RefreshCw, Sparkles, AlertCircle } from 'lucide-react'
import RadarChart from '../components/RadarChart.jsx'
import ScoreBar from '../components/ScoreBar.jsx'

const FORMAT_POINT_NAMES = {
  1: 'A vs B', 2: 'Underdog to Hero', 3: 'DYK - Fact', 4: 'Tips',
  5: 'Is this You?', 6: "You're Wrong", 7: 'Patient Problem', 8: 'Concoction',
  9: 'DYK Villain', 10: 'Villain Based', 11: 'Natural Ingredient', 12: 'DIY Goal',
  13: 'Current Affair+DIY', 14: 'Ingredient Rating', 15: 'Reels/Tips', 16: 'How To+DIY',
  17: 'Product Rating', 18: 'Supplement Rec', 19: 'Diagnosis', 20: 'CGM Format',
  21: 'Podcast Split', 22: 'Reversal', 23: 'Reaction', 24: 'Invite to Contact'
}

function fmtViews(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return String(n)
}

const ANGLE_CONFIG = {
  villain:      { label: 'Villain',      Icon: Swords,     color: 'text-red-500',    bg: 'bg-red-50 dark:bg-red-900/20',    border: 'border-red-200 dark:border-red-800' },
  hero:         { label: 'Hero',         Icon: Shield,     color: 'text-green-500',  bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800' },
  virality:     { label: 'Virality',     Icon: Zap,        color: 'text-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800' },
  credibility:  { label: 'Credibility', Icon: BadgeCheck, color: 'text-blue-500',   bg: 'bg-blue-50 dark:bg-blue-900/20',   border: 'border-blue-200 dark:border-blue-800' },
  moral_ground: { label: 'Moral Ground', Icon: Heart,      color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800' },
}

function AngleCard({ angleKey, data }) {
  const cfg = ANGLE_CONFIG[angleKey]
  const { Icon } = cfg
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={15} className={cfg.color} />
          <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{cfg.label}</span>
        </div>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${data.present ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
          {data.present ? 'Present ✓' : 'Missing'}
        </span>
      </div>
      {data.description && (
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{data.description}</p>
      )}
      {(data.exact_lines || []).length > 0 && (
        <div className="space-y-1 pt-1">
          {data.exact_lines.map((line, i) => (
            <p key={i} className="text-xs italic text-slate-700 dark:text-slate-300 bg-white/60 dark:bg-black/20 px-2 py-1 rounded border-l-2 border-current">
              "{line}"
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default function VideoDetail() {
  const { videoId } = useParams()
  const navigate = useNavigate()
  const [video, setVideo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showTranscript, setShowTranscript] = useState(false)
  const [angles, setAngles] = useState(null)
  const [analyzingAngles, setAnalyzingAngles] = useState(false)
  const [angleError, setAngleError] = useState(null)

  useEffect(() => {
    axios.get(`/api/videos/${videoId}`).then(r => { setVideo(r.data); setLoading(false) }).catch(() => setLoading(false))
    axios.get(`/api/videos/${videoId}/angles`).then(r => { if (r.data) setAngles(r.data) }).catch(() => {})
  }, [videoId])

  const runAngleAnalysis = async () => {
    setAnalyzingAngles(true)
    setAngleError(null)
    try {
      const { data } = await axios.post(`/api/videos/${videoId}/analyze-angles`)
      setAngles(data)
    } catch (e) {
      setAngleError(e?.response?.data?.detail || 'Analysis failed. Check your Gemini API key.')
    } finally {
      setAnalyzingAngles(false)
    }
  }

  const goToScriptGenerator = () => {
    if (!angles) return
    const params = new URLSearchParams({
      from_video: videoId,
      title: video?.title || '',
      villain: angles.villain?.description || '',
      hero: angles.hero?.description || '',
      virality: angles.virality?.description || '',
    })
    navigate(`/script-generator?${params.toString()}`)
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>
  if (!video) return <div className="text-red-500 p-4">Video not found.</div>

  const an = video.analysis
  const scores = an?.format_point_scores || {}
  const allScores = Object.entries(scores)
    .map(([k, v]) => ({ num: Number(k), score: v, name: FORMAT_POINT_NAMES[Number(k)] || `FP${k}` }))
    .sort((a, b) => b.score - a.score)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link to={video.format_point_id ? `/format-points/${video.format_point_id}` : '/format-points'} className="btn-secondary flex items-center gap-1 text-sm mt-1">
          <ArrowLeft size={14} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">{video.title}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{video.channel_name}</p>
        </div>
        <a href={video.youtube_url} target="_blank" rel="noopener noreferrer"
          className="btn-secondary flex items-center gap-1 text-sm shrink-0">
          <ExternalLink size={13} /> Watch
        </a>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        {/* Left col */}
        <div className="space-y-4">
          {/* Thumbnail */}
          <img
            src={video.thumbnail_url || `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`}
            alt={video.title}
            className="w-full aspect-video object-cover rounded-xl"
          />

          {/* Stats */}
          <div className="card p-4 grid grid-cols-3 gap-3 text-center">
            {[
              { Icon: Eye, val: fmtViews(video.view_count), label: 'Views' },
              { Icon: ThumbsUp, val: fmtViews(video.like_count), label: 'Likes' },
              { Icon: MessageSquare, val: fmtViews(video.comment_count), label: 'Comments' },
            ].map(({ Icon, val, label }) => (
              <div key={label}>
                <Icon size={16} className="mx-auto text-slate-400 mb-1" />
                <p className="font-bold text-slate-900 dark:text-white text-sm">{val}</p>
                <p className="text-xs text-slate-400">{label}</p>
              </div>
            ))}
          </div>

          {/* Format point badge */}
          {video.format_point && (
            <div className="card p-3">
              <p className="text-xs text-slate-400 mb-1">Scraped for format point</p>
              <span className="badge bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-sm">
                #{video.format_point.number} — {video.format_point.name}
              </span>
            </div>
          )}

          {/* Radar chart */}
          {an && (
            <div className="card p-4">
              <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm">Format Scores (top 12)</h2>
              <RadarChart scores={scores} />
            </div>
          )}
        </div>

        {/* Right col */}
        <div className="space-y-4">
          {/* Analysis status */}
          {!an && (
            <div className="card p-5 text-center">
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                Analysis status: <strong>{video.analysis_status}</strong>
              </p>
              {video.analysis_status === 'pending' && (
                <p className="text-xs text-slate-400 mt-1">Run the analyzer from Controls to analyze this video.</p>
              )}
            </div>
          )}

          {an && (
            <>
              {/* Concept summary */}
              <div className="card p-4">
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm">Concept Summary</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">{an.concept_summary}</p>
                {an.health_niche_angle && (
                  <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Health Angle: </span>
                    <span className="text-xs text-slate-700 dark:text-slate-300">{an.health_niche_angle}</span>
                  </div>
                )}
              </div>

              {/* Script analysis */}
              <div className="card p-4">
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm">Script Analysis</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">{an.script_analysis}</p>
              </div>

              {/* What works / doesn't */}
              <div className="grid grid-cols-2 gap-3">
                <div className="card p-3">
                  <h3 className="text-xs font-semibold text-green-600 dark:text-green-400 mb-2 flex items-center gap-1">
                    <CheckCircle size={12} /> What Works
                  </h3>
                  <ul className="space-y-1">
                    {(an.what_works || []).map((w, i) => (
                      <li key={i} className="text-xs text-slate-600 dark:text-slate-400">• {w}</li>
                    ))}
                  </ul>
                </div>
                <div className="card p-3">
                  <h3 className="text-xs font-semibold text-red-500 dark:text-red-400 mb-2 flex items-center gap-1">
                    <XCircle size={12} /> Weaknesses
                  </h3>
                  <ul className="space-y-1">
                    {(an.what_doesnt_work || []).map((w, i) => (
                      <li key={i} className="text-xs text-slate-600 dark:text-slate-400">• {w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Best moments */}
              {(an.best_moments || []).length > 0 && (
                <div className="card p-4">
                  <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-2 text-sm">Best Moments</h2>
                  <div className="space-y-3">
                    {an.best_moments.map((m, i) => (
                      <div key={i} className="border-l-2 border-brand-400 pl-3">
                        <p className="text-xs font-medium text-brand-600 dark:text-brand-400">{m.timestamp}</p>
                        <p className="text-xs text-slate-700 dark:text-slate-300 italic">"{m.excerpt}"</p>
                        {m.note && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">→ {m.note}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All scores */}
              <div className="card p-4">
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 text-sm">All Format Point Scores</h2>
                <div className="space-y-1.5">
                  {allScores.filter(s => s.score > 0).map(({ num, score, name }) => (
                    <ScoreBar key={num} score={score} label={`#${num} ${name}`} />
                  ))}
                  {allScores.filter(s => s.score === 0).length > 0 && (
                    <p className="text-xs text-slate-400 pt-1">
                      {allScores.filter(s => s.score === 0).length} format points scored 0 (not used)
                    </p>
                  )}
                </div>
              </div>
            </>
          )}

          {/* 5-Angle Analysis */}
          <div className="card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">5-Angle Analysis</h2>
              <button
                onClick={runAngleAnalysis}
                disabled={analyzingAngles}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                {analyzingAngles ? <RefreshCw size={11} className="animate-spin" /> : <Swords size={11} />}
                {analyzingAngles ? 'Analyzing...' : angles ? 'Re-analyze' : 'Analyze 5 Angles'}
              </button>
            </div>

            {angleError && (
              <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-xs">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                {angleError}
              </div>
            )}

            {analyzingAngles && (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-20 bg-slate-100 dark:bg-slate-700 rounded-xl animate-pulse" />
                ))}
              </div>
            )}

            {!analyzingAngles && !angles && !angleError && (
              <p className="text-xs text-slate-400 text-center py-4">
                Click "Analyze 5 Angles" to extract villain, hero, virality, credibility & moral ground from this video using Gemini.
              </p>
            )}

            {angles && !analyzingAngles && (
              <div className="space-y-3">
                {/* Overall strength */}
                {angles.overall_strength && (
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Overall angle strength</span>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-0.5">
                        {[...Array(10)].map((_, i) => (
                          <div key={i} className={`w-2 h-4 rounded-sm ${i < angles.overall_strength ? 'bg-brand-500' : 'bg-slate-200 dark:bg-slate-600'}`} />
                        ))}
                      </div>
                      <span className="text-xs font-bold text-brand-600 dark:text-brand-400">{angles.overall_strength}/10</span>
                    </div>
                  </div>
                )}

                {/* Angle cards */}
                {Object.keys(ANGLE_CONFIG).map(key => (
                  <AngleCard key={key} angleKey={key} data={angles[key] || { present: false, description: '', exact_lines: [] }} />
                ))}

                {/* Script inspiration */}
                {angles.script_inspiration && (
                  <div className="px-3 py-2 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
                    <p className="text-xs font-medium text-brand-700 dark:text-brand-300 mb-0.5">Script inspiration</p>
                    <p className="text-xs text-slate-700 dark:text-slate-300 italic">{angles.script_inspiration}</p>
                  </div>
                )}

                {/* Generate Script button */}
                <button
                  onClick={goToScriptGenerator}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-brand-500 to-purple-500 hover:from-brand-600 hover:to-purple-600 text-white font-medium rounded-xl transition-all text-sm shadow-sm"
                >
                  <Sparkles size={14} />
                  Generate Script from this Video
                </button>

                <p className="text-xs text-slate-400 text-center">
                  Analyzed {angles.analyzed_at?.split('T')[0]} · {angles.model_used}
                </p>
              </div>
            )}
          </div>

          {/* Transcript */}
          {video.transcript && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">Transcript</h2>
                <button onClick={() => setShowTranscript(s => !s)} className="text-xs text-brand-600 dark:text-brand-400">
                  {showTranscript ? 'Hide' : 'Show'}
                </button>
              </div>
              {showTranscript && (
                <div className="max-h-64 overflow-y-auto text-xs text-slate-600 dark:text-slate-400 font-mono whitespace-pre-line leading-relaxed">
                  {video.transcript}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
