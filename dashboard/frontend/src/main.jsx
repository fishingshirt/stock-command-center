import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Archive from './pages/Archive'
import Whiteboard from './pages/Whiteboard'
import Settings from './pages/Settings'
import Advisor from './pages/Advisor'
import Council from './pages/Council'
import './css/index.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-900 text-slate-50 font-sans">
        <nav className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-xl font-bold tracking-tight">Stock Command Center</span>
            <span className="text-xs bg-green-600 text-white px-2 py-1 rounded-full">Active</span>
          </div>
          <div className="flex gap-6 text-sm">
            <Link to="/" className="hover:text-violet-400 transition">Home</Link>
            <Link to="/advisor" className="hover:text-violet-400 transition">Advisor</Link>
            <Link to="/council" className="hover:text-violet-400 transition">Council</Link>
            <Link to="/archive" className="hover:text-violet-400 transition">Archive</Link>
            <Link to="/whiteboard" className="hover:text-violet-400 transition">Whiteboard</Link>
            <Link to="/settings" className="hover:text-violet-400 transition">Settings</Link>
          </div>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/advisor" element={<Advisor />} />
            <Route path="/council" element={<Council />} />
            <Route path="/archive" element={<Archive />} />
            <Route path="/whiteboard" element={<Whiteboard />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
