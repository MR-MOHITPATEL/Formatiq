export default function ScoreBar({ score, max = 10, label, showValue = true }) {
  const pct = Math.min(100, (score / max) * 100)
  const color =
    score >= 7 ? 'bg-green-500' :
    score >= 4 ? 'bg-yellow-400' :
    score >= 1 ? 'bg-orange-400' :
    'bg-slate-200 dark:bg-slate-600'

  return (
    <div className="flex items-center gap-2 w-full">
      {label && <span className="text-xs text-slate-600 dark:text-slate-400 w-32 shrink-0 truncate">{label}</span>}
      <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showValue && (
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300 w-8 text-right">
          {score}/10
        </span>
      )}
    </div>
  )
}
