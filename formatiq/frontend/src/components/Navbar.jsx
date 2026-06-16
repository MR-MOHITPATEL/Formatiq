import { Link, useLocation } from 'react-router-dom'
import { Moon, Sun, BarChart2, Grid, Video, Lightbulb, Settings, Sparkles } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/overview', label: 'Overview', Icon: BarChart2 },
  { to: '/format-points', label: 'Format Points', Icon: Grid },
  { to: '/recommendations', label: 'Recommendations', Icon: Lightbulb },
  { to: '/script-generator', label: 'Script Generator', Icon: Sparkles },
  { to: '/controls', label: 'Controls', Icon: Settings },
]

export default function Navbar({ darkMode, onToggleDark }) {
  const location = useLocation()

  return (
    <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center h-14 gap-1">
          {/* Logo */}
          <Link to="/overview" className="flex items-center gap-2 mr-4">
            <div className="w-7 h-7 bg-brand-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xs">FQ</span>
            </div>
            <span className="font-bold text-slate-900 dark:text-white text-sm hidden sm:block">FormatIQ</span>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1 flex-1">
            {NAV_ITEMS.map(({ to, label, Icon }) => {
              const active = location.pathname.startsWith(to)
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? 'bg-brand-50 dark:bg-brand-700/30 text-brand-600 dark:text-brand-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                  }`}
                >
                  <Icon size={15} />
                  <span className="hidden md:block">{label}</span>
                </Link>
              )
            })}
          </div>

          {/* Dark mode toggle */}
          <button
            onClick={onToggleDark}
            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    </nav>
  )
}
