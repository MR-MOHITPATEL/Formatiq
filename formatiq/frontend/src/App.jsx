import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar.jsx'
import Overview from './pages/Overview.jsx'
import FormatPoints from './pages/FormatPoints.jsx'
import VideoDetail from './pages/VideoDetail.jsx'
import Recommendations from './pages/Recommendations.jsx'
import Controls from './pages/Controls.jsx'
import ScriptGenerator from './pages/ScriptGenerator.jsx'

export default function App() {
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true'
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    localStorage.setItem('darkMode', darkMode)
  }, [darkMode])

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navbar darkMode={darkMode} onToggleDark={() => setDarkMode(d => !d)} />
        <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/format-points" element={<FormatPoints />} />
            <Route path="/format-points/:fpId" element={<FormatPoints />} />
            <Route path="/video/:videoId" element={<VideoDetail />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/controls" element={<Controls />} />
            <Route path="/script-generator" element={<ScriptGenerator />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
