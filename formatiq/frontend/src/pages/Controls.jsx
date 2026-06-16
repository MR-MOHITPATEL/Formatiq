import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import { Play, Plus, RefreshCw, AlertCircle, CheckCircle, Clock, Zap, Target, Globe, User, Trash2, ChevronDown, Sparkles, BookOpen, Search, ChevronLeft, ChevronRight } from 'lucide-react'

const PAGE_SIZE = 15

function ChannelList({ onTierChange, totalCounts }) {
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ total: 0, channels: [] })
  const [loading, setLoading] = useState(true)

  // Debounce search input 300ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Fetch from server whenever search/tier/page changes
  useEffect(() => {
    setLoading(true)
    const params = { page, page_size: PAGE_SIZE }
    if (debouncedSearch) params.search = debouncedSearch
    if (tierFilter !== 'all') params.tier = tierFilter
    axios.get('/api/channels', { params })
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [debouncedSearch, tierFilter, page])

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  const handleSearch = (v) => { setSearch(v); setPage(1) }
  const handleFilter = (v) => { setTierFilter(v); setPage(1) }

  return (
    <div className="space-y-2">
      {/* Search + filter row */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search channels..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
        </div>
        <select
          value={tierFilter}
          onChange={e => handleFilter(e.target.value)}
          className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-400"
        >
          <option value="all">All tiers</option>
          <option value="direct">Direct</option>
          <option value="market">Market</option>
          <option value="own">Own</option>
        </select>
      </div>

      {/* Count */}
      <p className="text-xs text-slate-400">
        {loading ? 'Loading...' : `Showing ${data.channels.length} of ${data.total}${debouncedSearch || tierFilter !== 'all' ? ` (filtered from ${totalCounts || data.total})` : ''}`}
      </p>

      {/* List */}
      <div className="space-y-1">
        {data.channels.map(ch => (
          <div key={ch.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/40 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
            <div className={`w-2 h-2 rounded-full shrink-0 ${TIER_CONFIG[ch.competitor_tier]?.dot || 'bg-slate-400'}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{ch.channel_name || ch.channel_id}</p>
              <p className="text-xs text-slate-400">{(ch.subscriber_count || 0).toLocaleString()} subs · {ch.video_count} videos scraped</p>
            </div>
            <TierDropdown
              channelId={ch.id}
              currentTier={ch.competitor_tier || 'market'}
              onChange={(tier) => onTierChange(ch.id, tier)}
            />
          </div>
        ))}
        {!loading && data.channels.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-3">No channels match your search.</p>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <ChevronLeft size={12} /> Prev
          </button>
          <span className="text-xs text-slate-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Next <ChevronRight size={12} />
          </button>
        </div>
      )}
    </div>
  )
}

function OwnChannelStyleCard() {
  const [profile, setProfile] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkResult, setBulkResult] = useState(null)
  const [error, setError] = useState('')
  const [channelUrl, setChannelUrl] = useState('')
  const [adding, setAdding] = useState(false)
  const [addMsg, setAddMsg] = useState('')

  useEffect(() => {
    axios.get('/api/channels/own/style-profile')
      .then(r => setProfile(r.data))
      .catch(() => {})
  }, [])

  const addOwnChannel = async () => {
    if (!channelUrl.trim()) return
    setAdding(true)
    setAddMsg('')
    setError('')
    try {
      const { data: newCh } = await axios.post('/api/channels', { channel_url_or_id: channelUrl.trim() })
      await axios.patch(`/api/channels/${newCh.id}/tier`, { competitor_tier: 'own' })
      setAddMsg(`✓ "${newCh.channel_name || channelUrl}" added. Now click Analyze My Channel.`)
      setChannelUrl('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to add channel')
    } finally {
      setAdding(false)
    }
  }

  const runAnalysis = async () => {
    setAnalyzing(true)
    setError('')
    setAddMsg('')
    try {
      const { data } = await axios.post('/api/channels/own/analyze-style')
      setProfile({ profile: data.profile, channel_name: data.channel_name, videos_analyzed: data.videos_analyzed, analyzed_at: new Date().toISOString() })
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const runBulkAngleAnalysis = async () => {
    setBulkAnalyzing(true)
    setBulkResult(null)
    setError('')
    try {
      const { data } = await axios.post('/api/channels/own/bulk-analyze-angles')
      setBulkResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Bulk analysis failed')
    } finally {
      setBulkAnalyzing(false)
    }
  }

  const p = profile?.profile

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-2">
          <Sparkles size={14} className="text-purple-500" /> My Channel Style Profile
        </h2>
        <div className="flex gap-2">
          <button
            onClick={runBulkAngleAnalysis}
            disabled={bulkAnalyzing}
            title="Run 5-angle analysis on all your videos at once"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {bulkAnalyzing ? <RefreshCw size={11} className="animate-spin" /> : <Sparkles size={11} />}
            {bulkAnalyzing ? 'Analyzing videos...' : 'Analyze All Videos (5-Angle)'}
          </button>
          <button
            onClick={runAnalysis}
            disabled={analyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {analyzing ? <RefreshCw size={11} className="animate-spin" /> : <Sparkles size={11} />}
            {analyzing ? 'Analyzing...' : p ? 'Re-analyze Style' : 'Analyze My Channel'}
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Add your own YouTube channel below, then click Analyze. Scripts will be generated to match your voice and style.
      </p>

      {/* Add own channel input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={channelUrl}
          onChange={e => setChannelUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && channelUrl && addOwnChannel()}
          placeholder="Your channel URL  (e.g. https://youtube.com/@YourChannel)"
          className="flex-1 text-sm border border-purple-200 dark:border-purple-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-400"
        />
        <button
          onClick={addOwnChannel}
          disabled={adding || !channelUrl.trim()}
          className="flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/60 disabled:opacity-50 transition-colors font-medium"
        >
          {adding ? <RefreshCw size={11} className="animate-spin" /> : <Plus size={11} />}
          {adding ? 'Adding...' : 'Add'}
        </button>
      </div>

      {addMsg && <p className="text-xs text-green-600 dark:text-green-400">{addMsg}</p>}
      {error && <p className="text-xs text-red-500">{error}</p>}
      {bulkResult && (
        <div className="text-xs px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
          ✓ {bulkResult.message} — Go to Script Generator to see your Angle Intelligence recommendations.
        </div>
      )}

      {!p && !analyzing && !addMsg && (
        <p className="text-xs text-slate-400 italic">No style profile yet. Add your channel above and click Analyze.</p>
      )}

      {p && (
        <div className="space-y-2 pt-1 border-t border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
            <CheckCircle size={11} /> Style profile active · {profile.videos_analyzed} videos analyzed · Scripts will match your voice
          </div>
          {p.tone_description && (
            <div className="bg-slate-50 dark:bg-slate-700/40 rounded-lg p-3">
              <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 flex items-center gap-1"><BookOpen size={10} /> Tone</p>
              <p className="text-xs text-slate-600 dark:text-slate-400">{p.tone_description}</p>
            </div>
          )}
          {p.vocabulary?.common_phrases?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {p.vocabulary.common_phrases.map((phrase, i) => (
                <span key={i} className="text-xs px-2 py-0.5 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">{phrase}</span>
              ))}
            </div>
          )}
          {p.what_makes_them_unique && (
            <p className="text-xs text-slate-500 dark:text-slate-400 italic">"{p.what_makes_them_unique}"</p>
          )}
        </div>
      )}
    </div>
  )
}

function JobProgress({ jobId }) {
  const [job, setJob] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!jobId) return
    const poll = () => {
      axios.get(`/api/jobs/${jobId}`).then(r => {
        setJob(r.data)
        if (r.data.status === 'done' || r.data.status === 'error') {
          clearInterval(intervalRef.current)
        }
      }).catch(() => clearInterval(intervalRef.current))
    }
    poll()
    intervalRef.current = setInterval(poll, 800)
    return () => clearInterval(intervalRef.current)
  }, [jobId])

  if (!job) return null

  const pct = job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0

  return (
    <div className={`card p-4 ${job.status === 'error' ? 'border-red-200 dark:border-red-800' : ''}`}>
      <div className="flex items-center gap-2 mb-2">
        {job.status === 'done' && <CheckCircle size={15} className="text-green-500" />}
        {job.status === 'error' && <AlertCircle size={15} className="text-red-500" />}
        {job.status === 'running' && <RefreshCw size={15} className="text-brand-500 animate-spin" />}
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{job.message}</span>
      </div>
      {job.total > 0 && (
        <div className="space-y-1">
          <div className="bg-slate-100 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-brand-500 rounded-full transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-slate-400">{job.progress} / {job.total} ({pct}%)</p>
        </div>
      )}
      {job.result && (
        <div className="mt-2 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-3 gap-2">
          <span>Analyzed: <strong>{job.result.analyzed}</strong></span>
          <span>Failed: <strong>{job.result.failed}</strong></span>
          <span>Tokens: <strong>{job.result.tokens_used?.toLocaleString()}</strong></span>
        </div>
      )}
    </div>
  )
}

const TIER_CONFIG = {
  direct: {
    label: 'Direct Competitor',
    short: 'Direct',
    icon: Target,
    color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    dot: 'bg-purple-500',
    desc: 'Primary benchmark channels used for validation',
  },
  market: {
    label: 'Market',
    short: 'Market',
    icon: Globe,
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    dot: 'bg-blue-400',
    desc: 'Broader market pool',
  },
  own: {
    label: 'Own Channel',
    short: 'Own',
    icon: User,
    color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    dot: 'bg-slate-400',
    desc: 'Your own channel (excluded from analysis)',
  },
}

function TierDropdown({ channelId, currentTier, onChange }) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const ref = useRef(null)
  const tier = TIER_CONFIG[currentTier] || TIER_CONFIG.market

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const select = async (newTier) => {
    setOpen(false)
    if (newTier === currentTier) return
    setSaving(true)
    try {
      await axios.patch(`/api/channels/${channelId}/tier`, { competitor_tier: newTier })
      onChange(newTier)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        disabled={saving}
        className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${tier.color} hover:opacity-80`}
      >
        {saving ? <RefreshCw size={10} className="animate-spin" /> : <tier.icon size={10} />}
        {tier.short}
        <ChevronDown size={9} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 z-20 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl shadow-lg py-1 w-52">
          {Object.entries(TIER_CONFIG).map(([key, t]) => (
            <button
              key={key}
              onClick={() => select(key)}
              className={`w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${key === currentTier ? 'bg-slate-50 dark:bg-slate-700/60' : ''}`}
            >
              <t.icon size={12} className="mt-0.5 text-slate-500" />
              <div>
                <p className="text-xs font-medium text-slate-800 dark:text-slate-200">{t.label}</p>
                <p className="text-xs text-slate-400">{t.desc}</p>
              </div>
              {key === currentTier && <CheckCircle size={11} className="ml-auto text-brand-500 mt-0.5" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Controls() {
  const [cfg, setCfg] = useState(null)
  const [formatPoints, setFormatPoints] = useState([])
  const [totalChannels, setTotalChannels] = useState(0)

  const [scrapeJobId, setScrapeJobId] = useState(null)
  const [analyzeJobId, setAnalyzeJobId] = useState(null)
  const [channelScrapeJobId, setChannelScrapeJobId] = useState(null)
  const [estimate, setEstimate] = useState(null)

  const [selectedFps, setSelectedFps] = useState([])
  const [videosPerFp, setVideosPerFp] = useState(50)
  const [batchSize, setBatchSize] = useState(10)
  const [selectedFpAnalyze, setSelectedFpAnalyze] = useState('')
  const [newChannel, setNewChannel] = useState('')
  const [newChannelTier, setNewChannelTier] = useState('market')
  const [addingChannel, setAddingChannel] = useState(false)
  const [channelError, setChannelError] = useState('')
  const [channelScrapeUrl, setChannelScrapeUrl] = useState('')
  const [channelScrapeMax, setChannelScrapeMax] = useState(200)

  useEffect(() => {
    axios.get('/api/config').then(r => setCfg(r.data))
    axios.get('/api/format-points').then(r => setFormatPoints(r.data))
    axios.get('/api/channels', { params: { page: 1, page_size: 1 } }).then(r => setTotalChannels(r.data.total))
  }, [])

  useEffect(() => {
    axios.get('/api/analyze/estimate', {
      params: selectedFpAnalyze ? { format_point_id: selectedFpAnalyze } : {}
    }).then(r => setEstimate(r.data)).catch(() => {})
  }, [selectedFpAnalyze])

  const startScrape = () => {
    axios.post('/api/scrape/start', {
      format_point_ids: selectedFps,
      videos_per_format: videosPerFp,
      competitor_channels: [],
    }).then(r => setScrapeJobId(r.data.job_id))
  }

  const startAnalysis = () => {
    axios.post('/api/analyze/start', {
      format_point_id: selectedFpAnalyze ? Number(selectedFpAnalyze) : null,
      batch_size: batchSize,
    }).then(r => setAnalyzeJobId(r.data.job_id))
  }

  const addChannel = async () => {
    setAddingChannel(true)
    setChannelError('')
    try {
      const { data: newCh } = await axios.post('/api/channels', { channel_url_or_id: newChannel })
      // Set the tier right away if not default
      if (newChannelTier !== 'market') {
        await axios.patch(`/api/channels/${newCh.id}/tier`, { competitor_tier: newChannelTier })
        newCh.competitor_tier = newChannelTier
      } else {
        newCh.competitor_tier = 'market'
      }
      setChannels(c => [...c, newCh])
      setNewChannel('')
    } catch (e) {
      setChannelError(e.response?.data?.detail || 'Failed to add channel')
    } finally {
      setAddingChannel(false)
    }
  }

  const updateChannelTier = (channelId, newTier) => {
    setChannels(prev => prev.map(ch => ch.id === channelId ? { ...ch, competitor_tier: newTier } : ch))
  }

  const scrapeChannel = () => {
    if (!channelScrapeUrl) return
    axios.post('/api/scrape/channel', {
      channel_url_or_id: channelScrapeUrl,
      max_videos: channelScrapeMax,
    }).then(r => {
      setChannelScrapeJobId(r.data.job_id)
      setChannelScrapeUrl('')
    })
  }

  const toggleFp = (id) => {
    setSelectedFps(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const [tierCounts, setTierCounts] = useState({ direct: 0, market: 0 })
  useEffect(() => {
    Promise.all([
      axios.get('/api/channels', { params: { tier: 'direct', page: 1, page_size: 1 } }),
      axios.get('/api/channels', { params: { tier: 'market', page: 1, page_size: 1 } }),
    ]).then(([d, m]) => setTierCounts({ direct: d.data.total, market: m.data.total })).catch(() => {})
  }, [])
  const directCount = tierCounts.direct
  const marketCount = tierCounts.market

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Scrape & Analyze Controls</h1>

      {/* API status */}
      {cfg && (
        <div className="card p-4">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 text-sm">API Configuration</h2>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'YouTube API', ok: cfg.youtube_api_configured },
              { label: 'Groq API', ok: cfg.groq_api_configured, model: cfg.groq_model, primary: true },
              { label: 'Anthropic API', ok: cfg.anthropic_api_configured, note: 'fallback' },
            ].map(({ label, ok, model, note, primary }) => (
              <div key={label} className={`flex items-center gap-2 p-3 rounded-lg ${ok ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                {ok ? <CheckCircle size={14} className="text-green-500 shrink-0" /> : <AlertCircle size={14} className="text-red-500 shrink-0" />}
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                    {label}
                    {primary && ok && <span className="text-xs text-purple-500 font-semibold">★</span>}
                    {note && <span className="text-xs text-slate-400">({note})</span>}
                  </p>
                  <p className={`text-xs truncate ${ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    {ok ? (model ? model : 'Configured') : 'Not configured'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitor Channels */}
      <div className="card p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">Competitor Channels ({totalChannels})</h2>
          <div className="flex gap-2">
            {directCount > 0 && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                <Target size={10} /> {directCount} direct
              </span>
            )}
            {marketCount > 0 && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                <Globe size={10} /> {marketCount} market
              </span>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex gap-4 text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/40 rounded-lg px-3 py-2">
          <span className="flex items-center gap-1"><Target size={10} className="text-purple-500" /> <strong className="text-purple-600 dark:text-purple-400">Direct</strong> = your primary benchmark (2-3 channels)</span>
          <span className="flex items-center gap-1"><Globe size={10} className="text-blue-500" /> <strong className="text-blue-600 dark:text-blue-400">Market</strong> = broader pool</span>
        </div>

        {/* Search + filter */}
        <ChannelList onTierChange={updateChannelTier} totalCounts={totalChannels} />

        {totalChannels === 0 && (
          <p className="text-sm text-slate-400 text-center py-3">No channels added yet. Add a competitor channel below.</p>
        )}

        {/* Add channel */}
        <div className="space-y-2 pt-1 border-t border-slate-100 dark:border-slate-700">
          <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Add a competitor channel</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={newChannel}
              onChange={e => setNewChannel(e.target.value)}
              placeholder="Channel URL or ID  (e.g. https://youtube.com/@DoctorMike)"
              className="flex-1 text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400"
              onKeyDown={e => e.key === 'Enter' && newChannel && addChannel()}
            />
            <select
              value={newChannelTier}
              onChange={e => setNewChannelTier(e.target.value)}
              className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-2 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="direct">Direct</option>
              <option value="market">Market</option>
              <option value="own">Own</option>
            </select>
            <button
              onClick={addChannel}
              disabled={addingChannel || !newChannel}
              className="btn-primary flex items-center gap-1 text-sm disabled:opacity-50"
            >
              {addingChannel ? <RefreshCw size={13} className="animate-spin" /> : <Plus size={13} />}
              Add
            </button>
          </div>
          {channelError && <p className="text-xs text-red-500">{channelError}</p>}
        </div>
      </div>

      {/* Analyze Own Channel Style */}
      <OwnChannelStyleCard />

      {/* Scrape Channel */}
      <div className="card p-4 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-2">
          <Play size={14} className="text-brand-500" /> Scrape a YouTube Channel
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Enter a channel URL or ID to scrape all its videos directly (no keyword search needed).
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={channelScrapeUrl}
            onChange={e => setChannelScrapeUrl(e.target.value)}
            placeholder="https://www.youtube.com/@ChannelName  or  UCxxxxxxx"
            className="flex-1 text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400"
            onKeyDown={e => e.key === 'Enter' && channelScrapeUrl && scrapeChannel()}
          />
          <div className="flex flex-col">
            <label className="text-xs text-slate-400 mb-1">Max videos</label>
            <input
              type="number" min={10} max={500} value={channelScrapeMax}
              onChange={e => setChannelScrapeMax(Number(e.target.value))}
              className="w-24 text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
            />
          </div>
          <button
            onClick={scrapeChannel}
            disabled={!channelScrapeUrl}
            className="btn-primary flex items-center gap-1 text-sm self-end disabled:opacity-50 pb-2 pt-2 px-3"
          >
            <Play size={14} /> Scrape
          </button>
        </div>
        {channelScrapeJobId && <JobProgress jobId={channelScrapeJobId} />}
      </div>

      {/* Scraper */}
      <div className="card p-4 space-y-4">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-2">
          <Play size={14} className="text-brand-500" /> Run Scraper
        </h2>

        <div>
          <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-2">
            Format Points to scrape (leave empty = all 24)
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5 max-h-48 overflow-y-auto">
            {formatPoints.map(fp => (
              <button
                key={fp.id}
                onClick={() => toggleFp(fp.id)}
                className={`text-xs px-2 py-1.5 rounded-lg border text-left transition-colors ${
                  selectedFps.includes(fp.id)
                    ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
                    : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                }`}
              >
                #{fp.number} {fp.name.slice(0, 16)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">Videos per format</label>
            <input
              type="number" min={10} max={200} value={videosPerFp}
              onChange={e => setVideosPerFp(Number(e.target.value))}
              className="w-24 text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
            />
          </div>
        </div>

        <button onClick={startScrape} className="btn-primary flex items-center gap-2 text-sm">
          <Play size={14} /> Start Scraping {selectedFps.length > 0 ? `(${selectedFps.length} FPs)` : '(All 24)'}
        </button>
        {scrapeJobId && <JobProgress jobId={scrapeJobId} />}
      </div>

      {/* Analyzer */}
      <div className="card p-4 space-y-4">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-2">
          <Zap size={14} className="text-brand-500" /> Run AI Analysis
        </h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">Format Point (optional)</label>
            <select
              value={selectedFpAnalyze}
              onChange={e => setSelectedFpAnalyze(e.target.value)}
              className="w-full text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
            >
              <option value="">All pending videos</option>
              {formatPoints.map(fp => (
                <option key={fp.id} value={fp.id}>#{fp.number} {fp.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">Batch size</label>
            <input
              type="number" min={1} max={50} value={batchSize}
              onChange={e => setBatchSize(Number(e.target.value))}
              className="w-full text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200"
            />
          </div>
        </div>

        {estimate && (
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 text-xs text-slate-600 dark:text-slate-400 grid grid-cols-3 gap-2">
            <span><Clock size={10} className="inline mr-1" />{estimate.videos} pending</span>
            <span>~{estimate.estimated_input_tokens?.toLocaleString()} tokens</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">~${estimate.estimated_cost_usd} USD</span>
          </div>
        )}

        <button onClick={startAnalysis} className="btn-primary flex items-center gap-2 text-sm">
          <Zap size={14} /> Start Analysis
        </button>
        {analyzeJobId && <JobProgress jobId={analyzeJobId} />}
      </div>
    </div>
  )
}
