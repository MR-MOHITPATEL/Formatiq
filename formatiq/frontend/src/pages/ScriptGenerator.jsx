import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import {
  Sparkles, CheckCircle, XCircle, AlertTriangle, Copy, RefreshCw,
  ChevronRight, ChevronLeft, Newspaper, PenLine, Zap, Clock, Check,
  ExternalLink, List, FileText, Swords, Brain, TrendingUp,
} from 'lucide-react'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api'

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

function ValidationBadge({ validated, label }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
      validated
        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
        : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
    }`}>
      {validated ? <CheckCircle size={14} /> : <XCircle size={14} />}
      {label}
    </div>
  )
}

function EvidenceCard({ title, viewCount, channelName, url }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
    >
      <ExternalLink size={12} className="text-slate-400 mt-0.5 shrink-0 group-hover:text-brand-500" />
      <div className="min-w-0">
        <p className="text-xs text-slate-700 dark:text-slate-300 truncate">{title}</p>
        <p className="text-xs text-slate-400">{channelName} · {(viewCount || 0).toLocaleString()} views</p>
      </div>
    </a>
  )
}

const ANGLE_COLORS = {
  villain:      'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  hero:         'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  credibility:  'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  virality:     'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  moral_ground: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
}

function AngleIntelligenceCard({ topic = '' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const timer = setTimeout(() => {
      const url = topic.trim().length >= 3
        ? `${API}/channels/own/angle-performance?topic=${encodeURIComponent(topic.trim())}`
        : `${API}/channels/own/angle-performance`
      axios.get(url)
        .then(r => setData(r.data))
        .catch(() => setData(null))
        .finally(() => setLoading(false))
    }, 500) // debounce 500ms
    return () => clearTimeout(timer)
  }, [topic])

  if (loading) return (
    <div className="h-24 bg-slate-100 dark:bg-slate-700 rounded-xl animate-pulse" />
  )
  if (!data) return null

  if (!data.has_data) return (
    <div className="flex items-start gap-2 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl text-xs text-indigo-700 dark:text-indigo-300">
      <Brain size={13} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold">Angle Intelligence not ready yet</p>
        <p className="mt-0.5 opacity-80">Go to Controls → click "Analyze All Videos (5-Angle)" to unlock angle recommendations.</p>
      </div>
    </div>
  )

  const angles = ['villain', 'hero', 'credibility', 'virality', 'moral_ground']
  const maxScore = Math.max(...angles.map(a => data.scores[a] || 0), 1)

  return (
    <div className="border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/10 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
          <Brain size={14} className="text-indigo-500" /> Angle Intelligence
        </h3>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {data.is_topic_filtered
            ? <span className="px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300">{data.filtered_video_count} topic videos</span>
            : <span>{data.video_count} videos</span>
          }
          <span className="opacity-60">· by {data.score_basis === 'view_count' ? 'views' : 'quality score'}</span>
        </div>
      </div>

      {/* Recommended combo */}
      {data.best_combo_labels?.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 flex items-center gap-1">
            <TrendingUp size={11} /> Recommended today:
          </span>
          {data.best_combo_labels.map((label, i) => (
            <span key={i} className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-600 text-white">{label}</span>
          ))}
        </div>
      )}

      {/* Score bars */}
      <div className="space-y-1.5">
        {angles.map(a => {
          const score = data.scores[a] || 0
          const pct = Math.round((score / maxScore) * 100)
          const isBest = data.best_combo?.includes(a)
          return (
            <div key={a} className="flex items-center gap-2">
              <span className={`text-xs w-36 shrink-0 font-medium truncate ${isBest ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'}`}>
                {data.angle_labels[a]}
              </span>
              <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isBest ? 'bg-indigo-500' : 'bg-slate-400 dark:bg-slate-500'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className={`text-xs w-12 text-right font-mono shrink-0 ${isBest ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-400'}`}>
                {score}/25
              </span>
            </div>
          )
        })}
      </div>

      {/* AI insight */}
      {data.insight && (
        <div className="flex items-start gap-2 pt-2 border-t border-indigo-200 dark:border-indigo-800">
          <Sparkles size={11} className="text-indigo-500 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-600 dark:text-slate-300 italic">{data.insight}</p>
        </div>
      )}
    </div>
  )
}

// Step 1 — Topic selection
function Step1({ onNext, prefill = {} }) {
  const [mode, setMode] = useState('custom')
  const [customTopic, setCustomTopic] = useState(prefill.title || '')
  const [customAngle, setCustomAngle] = useState(
    [prefill.villain && `Villain: ${prefill.villain}`, prefill.hero && `Hero: ${prefill.hero}`].filter(Boolean).join(' | ') || ''
  )
  const [formatType, setFormatType] = useState('longform')
  const [language, setLanguage] = useState('hinglish')
  const [trending, setTrending] = useState([])
  const [loadingTrending, setLoadingTrending] = useState(false)
  const [selectedTrending, setSelectedTrending] = useState(null)

  const loadTrending = async () => {
    setLoadingTrending(true)
    try {
      const { data } = await axios.get(`${API}/script/trending-topics`)
      setTrending(data.topics || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingTrending(false)
    }
  }

  useEffect(() => {
    if (mode === 'trending') loadTrending()
  }, [mode])

  const handleNext = () => {
    if (mode === 'trending' && selectedTrending) {
      onNext({ topic: selectedTrending.title, angle: '', formatType, language })
    } else if (mode === 'custom' && customTopic.trim()) {
      onNext({ topic: customTopic.trim(), angle: customAngle.trim(), formatType, language })
    }
  }

  const canProceed = mode === 'trending' ? !!selectedTrending : !!customTopic.trim()

  return (
    <div className="space-y-6">
      {/* Angle Intelligence — recommended combo based on own channel analysis */}
      <AngleIntelligenceCard topic={mode === 'custom' ? customTopic : (selectedTrending?.title || '')} />

      {/* Pre-fill banner from video analysis */}
      {prefill.hasPreFill && (
        <div className="flex items-start gap-2 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-xl text-xs text-purple-700 dark:text-purple-300">
          <Swords size={13} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Pre-filled from 5-angle analysis</p>
            {prefill.villain && <p className="mt-0.5 opacity-80">Villain: {prefill.villain.slice(0, 80)}{prefill.villain.length > 80 ? '…' : ''}</p>}
            {prefill.hero && <p className="opacity-80">Hero: {prefill.hero.slice(0, 80)}{prefill.hero.length > 80 ? '…' : ''}</p>}
          </div>
        </div>
      )}

      {/* Format toggle */}
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Content format</p>
        <div className="flex gap-2">
          {[
            { value: 'shorts', label: 'Shorts / Reels', icon: Zap, desc: '60-90 seconds' },
            { value: 'longform', label: 'Long-form YouTube', icon: Clock, desc: '8-12 minutes' },
          ].map(({ value, label, icon: Icon, desc }) => (
            <button
              key={value}
              onClick={() => setFormatType(value)}
              className={`flex-1 flex items-center gap-2 px-4 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                formatType === value
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300'
                  : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500'
              }`}
            >
              <Icon size={15} />
              <div className="text-left">
                <div>{label}</div>
                <div className="text-xs opacity-70">{desc}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Language toggle */}
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Script language</p>
        <div className="flex gap-1 bg-slate-100 dark:bg-slate-700 p-1 rounded-lg">
          {[
            { value: 'hinglish', label: 'Hinglish', flag: '🇮🇳', desc: 'हिंदी + English mix' },
            { value: 'english', label: 'English', flag: '🇬🇧', desc: 'English only' },
            { value: 'hindi', label: 'हिंदी', flag: '🇮🇳', desc: 'Pure Hindi' },
          ].map(({ value, label, flag, desc }) => (
            <button
              key={value}
              onClick={() => setLanguage(value)}
              className={`flex-1 flex flex-col items-center py-2 px-3 rounded text-xs font-medium transition-colors ${
                language === value
                  ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <span>{flag} {label}</span>
              <span className="text-xs opacity-60 mt-0.5">{desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Topic source tabs */}
      <div>
        <div className="flex gap-1 mb-4 bg-slate-100 dark:bg-slate-700 p-1 rounded-lg">
          {[
            { value: 'trending', label: 'Trending Topics', icon: Newspaper },
            { value: 'custom', label: 'Enter My Own', icon: PenLine },
          ].map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded text-sm font-medium transition-colors ${
                mode === value
                  ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400'
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>

        {mode === 'trending' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Latest health & pharma news from Google News</p>
              <button
                onClick={loadTrending}
                className="flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 hover:underline"
              >
                <RefreshCw size={11} className={loadingTrending ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
            {loadingTrending ? (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-14 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : trending.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">No trending topics found. Check your internet connection.</p>
            ) : (
              <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                {trending.map((item, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedTrending(item)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                      selectedTrending?.title === item.title
                        ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
                        : 'border-slate-100 dark:border-slate-700 hover:border-slate-200 dark:hover:border-slate-600 bg-white dark:bg-slate-800'
                    }`}
                  >
                    <p className="text-sm text-slate-800 dark:text-slate-200 leading-snug">{item.title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{item.source} · {item.published_at}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {mode === 'custom' && (
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300 block mb-1">Topic *</label>
              <input
                type="text"
                value={customTopic}
                onChange={e => setCustomTopic(e.target.value)}
                placeholder="e.g. High blood pressure in young adults"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300 block mb-1">Angle / Angle <span className="font-normal text-slate-400">(optional)</span></label>
              <input
                type="text"
                value={customAngle}
                onChange={e => setCustomAngle(e.target.value)}
                placeholder="e.g. Root causes that doctors rarely mention"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>
          </div>
        )}
      </div>

      <button
        onClick={handleNext}
        disabled={!canProceed}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors text-sm"
      >
        Validate This Angle
        <ChevronRight size={15} />
      </button>
    </div>
  )
}

// Step 2 — Validation results
function Step2({ params, onNext, onBack }) {
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const validate = async () => {
      setLoading(true)
      try {
        const { data } = await axios.post(`${API}/script/validate-angle`, {
          topic: params.topic,
          angle: params.angle,
        })
        setResult(data)
      } catch (e) {
        setError('Validation failed. You can still proceed.')
      } finally {
        setLoading(false)
      }
    }
    validate()
  }, [params.topic, params.angle])

  const handleProceed = (force = false) => {
    onNext({ ...params, force, validation: result })
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Checking angle for:</p>
        <p className="font-semibold text-slate-900 dark:text-white">{params.topic}</p>
        {params.angle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Angle: {params.angle}</p>}
      </div>

      {loading && (
        <div className="space-y-3">
          <div className="h-16 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
          <div className="h-16 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-yellow-700 dark:text-yellow-400 text-sm">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      {result && !loading && (
        <div className="space-y-4">
          {/* Go / No-go banner */}
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-sm ${
            result.go
              ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800'
              : 'bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
          }`}>
            {result.go ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
            {result.message}
          </div>

          {/* Two-tier badges */}
          <div className="grid grid-cols-2 gap-2">
            <ValidationBadge validated={result.direct_validated} label={`Direct Competitors ${result.direct_video_count > 0 ? `(${result.direct_video_count} videos)` : '(no data)'}`} />
            <ValidationBadge validated={result.market_validated} label={`Broader Market ${result.market_video_count > 0 ? `(${result.market_video_count} videos)` : '(no data)'}`} />
          </div>

          {/* Evidence */}
          {(result.direct_evidence?.length > 0 || result.market_evidence?.length > 0) && (
            <div className="grid grid-cols-2 gap-3">
              {result.direct_evidence?.length > 0 && (
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Direct competitor evidence</p>
                  {result.direct_evidence.map((ev, i) => (
                    <EvidenceCard key={i} title={ev.title} viewCount={ev.view_count} channelName={ev.channel_name} url={ev.youtube_url} />
                  ))}
                </div>
              )}
              {result.market_evidence?.length > 0 && (
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Market evidence</p>
                  {result.market_evidence.map((ev, i) => (
                    <EvidenceCard key={i} title={ev.title} viewCount={ev.view_count} channelName={ev.channel_name} url={ev.youtube_url} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200">
          <ChevronLeft size={14} /> Back
        </button>
        <div className="flex-1 flex gap-2 justify-end">
          {result && !result.go && (
            <button
              onClick={() => handleProceed(true)}
              disabled={loading}
              className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Generate anyway
            </button>
          )}
          <button
            onClick={() => handleProceed(false)}
            disabled={loading || (!result && !error)}
            className="flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Sparkles size={13} />
            Generate Script
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

// Step 3 — Generated script display
function Step3({ params, onBack, onReset }) {
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('full') // 'full' | 'outline' | 'links'

  useEffect(() => {
    const generate = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await axios.post(`${API}/script/generate`, {
          topic: params.topic,
          angle: params.angle || '',
          format_type: params.formatType,
          force: params.force || false,
          language: params.language || 'hinglish',
        })
        if (!data.full_script) {
          setError(data.message || 'Script generation failed. Please try again.')
        } else {
          setResult(data)
        }
      } catch (e) {
        const detail = e?.response?.data?.detail
        setError(detail ? `Error: ${detail}` : 'Script generation failed. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    generate()
  }, [])

  const outlineSections = result?.outline ? Object.entries(result.outline) : []

  return (
    <div className="space-y-5">
      {loading && (
        <div className="text-center py-12">
          <div className="inline-flex items-center gap-2 text-slate-500 dark:text-slate-400">
            <Sparkles size={18} className="animate-spin text-brand-500" />
            <span className="text-sm">Writing your script{params.formatType === 'longform' ? ' (this takes ~20 seconds)' : ''}…</span>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-700 dark:text-red-400 text-sm">
          <XCircle size={14} className="mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      {result && !loading && (
        <>
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              {result.suggested_title && (
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">{result.suggested_title}</h2>
              )}
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className={`badge ${params.formatType === 'shorts' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}`}>
                  {params.formatType === 'shorts' ? 'Shorts / Reels' : 'Long-form YouTube'}
                </span>
                {result.validated ? (
                  <span className="badge bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">Validated ✓</span>
                ) : (
                  <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">Generated (unvalidated)</span>
                )}
                {result.thumbnail_text && (
                  <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300">Thumbnail: "{result.thumbnail_text}"</span>
                )}
              </div>
              {result.hook_line && (
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 italic">Hook: "{result.hook_line}"</p>
              )}
            </div>
            {result.full_script && (
              <CopyButton text={result.full_script} label="Copy full script" />
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 bg-slate-100 dark:bg-slate-700 p-1 rounded-lg">
            {[
              { value: 'full', label: 'Full Script', icon: FileText },
              { value: 'outline', label: 'Outline', icon: List },
              ...(result.citations?.length ? [{ value: 'citations', label: `Sources (${result.citations.length})`, icon: ExternalLink }] : []),
              ...(result.competitor_links?.length ? [{ value: 'links', label: `Competitor Videos (${result.competitor_links.length})`, icon: ExternalLink }] : []),
            ].map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setActiveTab(value)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded text-sm font-medium transition-colors ${
                  activeTab === value
                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>

          {/* Full script */}
          {activeTab === 'full' && result.full_script && (
            <div className="relative">
              <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 max-h-[480px] overflow-y-auto text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                {result.full_script}
              </div>
            </div>
          )}

          {/* Citations */}
          {activeTab === 'citations' && result.citations?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-slate-500 dark:text-slate-400">These sources were found via Google Search to support the claims in your script. Always verify before publishing.</p>
              {result.citations.map((cite, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 italic">"{cite.claim}"</p>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{cite.title}</p>
                      <p className="text-xs text-brand-600 dark:text-brand-400">{cite.source_name} {cite.year && `· ${cite.year}`}</p>
                    </div>
                    {cite.url && (
                      <a href={cite.url} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 shrink-0 text-xs px-2 py-1 bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 rounded hover:bg-brand-100 dark:hover:bg-brand-900/50 transition-colors">
                        <ExternalLink size={11} /> Open
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Competitor Links */}
          {activeTab === 'links' && result.competitor_links?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-slate-500 dark:text-slate-400">These competitor videos were analyzed to build the script's angles, hooks, and gaps.</p>
              {result.competitor_links.map((v, i) => (
                <a
                  key={i}
                  href={v.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-3 p-3 bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg hover:border-brand-300 dark:hover:border-brand-600 transition-colors group"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate group-hover:text-brand-600 dark:group-hover:text-brand-400">{v.title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{v.channel_name} · {(v.view_count || 0).toLocaleString()} views</p>
                  </div>
                  <ExternalLink size={14} className="shrink-0 text-slate-400 group-hover:text-brand-500" />
                </a>
              ))}
            </div>
          )}

          {/* Outline */}
          {activeTab === 'outline' && outlineSections.length > 0 && (
            <div className="space-y-2">
              {outlineSections.map(([key, value]) => (
                <div key={key} className="bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">
                      {key.replace(/_/g, ' ')}
                    </p>
                    <CopyButton text={String(value)} />
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-300">{String(value)}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200">
          <ChevronLeft size={14} /> Back
        </button>
        <button
          onClick={onReset}
          className="flex items-center gap-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ml-auto"
        >
          <RefreshCw size={13} />
          New Script
        </button>
      </div>
    </div>
  )
}

// History panel
function ScriptHistory() {
  const [scripts, setScripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await axios.get(`${API}/script/history`)
        setScripts(data.scripts || [])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const loadDetail = async (id) => {
    const { data } = await axios.get(`${API}/script/${id}`)
    setSelected(data)
  }

  if (loading) return <div className="h-32 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
  if (scripts.length === 0) return <p className="text-sm text-slate-400 text-center py-4">No scripts generated yet.</p>

  return (
    <div className="space-y-2">
      {scripts.map(s => (
        <button
          key={s.id}
          onClick={() => loadDetail(s.id)}
          className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
            selected?.id === s.id
              ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
              : 'border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-200'
          }`}
        >
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`badge ${s.format_type === 'shorts' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
              {s.format_type}
            </span>
            {s.validated && <span className="badge bg-green-100 text-green-700">✓</span>}
            <span className="text-xs text-slate-400">{s.created_at?.split('T')[0]}</span>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 truncate">{s.topic}</p>
          {s.hook_line && <p className="text-xs text-slate-400 truncate mt-0.5 italic">{s.hook_line}</p>}
        </button>
      ))}

      {selected && (
        <div className="mt-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-900 dark:text-white">{selected.topic}</p>
            {selected.full_script && <CopyButton text={selected.full_script} />}
          </div>
          <pre className="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
            {selected.full_script}
          </pre>
        </div>
      )}
    </div>
  )
}

// Main page
const STEPS = ['Choose Topic', 'Validate Angle', 'Generated Script']

export default function ScriptGenerator() {
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState(0)
  const [params, setParams] = useState({})
  const [showHistory, setShowHistory] = useState(false)

  // Pre-fill from video angle analysis (coming from VideoDetail "Generate Script" button)
  const fromVideo = searchParams.get('from_video')
  const prefillTitle = searchParams.get('title') || ''
  const prefillVillain = searchParams.get('villain') || ''
  const prefillHero = searchParams.get('hero') || ''
  const prefillVirality = searchParams.get('virality') || ''

  const hasPreFill = !!(fromVideo && (prefillVillain || prefillHero || prefillTitle))

  const handleStep1Next = (data) => {
    setParams(prev => ({ ...prev, ...data }))
    setStep(1)
  }

  const handleStep2Next = (data) => {
    setParams(prev => ({ ...prev, ...data }))
    setStep(2)
  }

  const reset = () => {
    setParams({})
    setStep(0)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Script Generator</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Validate your angle against competitors, then generate a humanized script for Shorts or Long-form YouTube.
          </p>
        </div>
        <button
          onClick={() => setShowHistory(h => !h)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
            showHistory
              ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400'
              : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
          }`}
        >
          <Clock size={13} />
          History
        </button>
      </div>

      {showHistory ? (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Previously Generated Scripts</h2>
          <ScriptHistory />
        </div>
      ) : (
        <div className="card p-6">
          {/* Step indicator */}
          <div className="flex items-center gap-0 mb-6">
            {STEPS.map((label, i) => (
              <div key={i} className="flex items-center gap-0 flex-1 last:flex-none">
                <div className="flex items-center gap-2">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    i < step ? 'bg-brand-500 text-white'
                    : i === step ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 border-2 border-brand-400'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-400'
                  }`}>
                    {i < step ? <Check size={12} /> : i + 1}
                  </div>
                  <span className={`text-xs font-medium hidden sm:block ${i === step ? 'text-slate-900 dark:text-white' : 'text-slate-400'}`}>
                    {label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-px mx-3 ${i < step ? 'bg-brand-400' : 'bg-slate-200 dark:bg-slate-700'}`} />
                )}
              </div>
            ))}
          </div>

          {step === 0 && <Step1 onNext={handleStep1Next} prefill={{ title: prefillTitle, villain: prefillVillain, hero: prefillHero, virality: prefillVirality, hasPreFill }} />}
          {step === 1 && <Step2 params={params} onNext={handleStep2Next} onBack={() => setStep(0)} />}
          {step === 2 && <Step3 params={params} onBack={() => setStep(1)} onReset={reset} />}
        </div>
      )}
    </div>
  )
}
