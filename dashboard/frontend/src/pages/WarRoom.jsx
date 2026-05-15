import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function WarRoom() {
  const [botStatus, setBotStatus] = useState(null)
  const [recs, setRecs] = useState([])
  const [feed, setFeed] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/bots/status`)
      .then(r => r.json())
      .then(setBotStatus)
      .catch(() => {})
    fetch(`${API_URL}/api/recommendations`)
      .then(r => r.json())
      .then(d => setRecs(d.slice(0, 5)))
      .catch(() => {})
    fetch(`${API_URL}/api/feed`)
      .then(r => r.json())
      .then(d => setFeed(d.entries || []))
      .catch(() => {})
    setLoading(false)

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/bots/status`).then(r => r.json()).then(setBotStatus).catch(() => {})
      fetch(`${API_URL}/api/feed`).then(r => r.json()).then(d => setFeed(d.entries || [])).catch(() => {})
    }, 30000)
    return () => clearInterval(iv)
  }, [])

  if (loading) return <div className="text-center py-20 text-slate-400">Loading War Room...</div>

  const bots = botStatus?.bots || []
  const activeCount = botStatus?.active_bots || 0
  const totalCount = botStatus?.total_bots || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">War Room</h2>
          <p className="text-sm text-slate-400">Live worker status and battlefield intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-400">Last cycle: {botStatus?.orchestrator_last_cycle || 'never'}</div>
          <div className={`px-3 py-1 rounded text-xs font-bold ${activeCount > 0 ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
            {activeCount}/{totalCount} Bots Active
          </div>
        </div>
      </div>

      {/* Bot Status Grid */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Bot Workers</h3>
        {bots.length === 0 ? (
          <p className="text-sm text-slate-500">No bot data available.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bots.map(bot => (
              <div key={bot.name} className={`border rounded-lg p-4 ${bot.active ? 'border-green-500/30 bg-green-500/5' : 'border-slate-700 bg-slate-800'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold text-sm">{bot.name}</div>
                  <div className={`w-2 h-2 rounded-full ${bot.active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                </div>
                <div className="text-xs text-slate-400 mb-2">{bot.expertise}</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-slate-500">Accuracy</div>
                    <div className="font-bold">{bot.accuracy}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Predictions</div>
                    <div className="font-bold">{bot.predictions}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Confidence</div>
                    <div className="font-bold">{bot.avg_confidence}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Last Run</div>
                    <div className="font-bold text-slate-300">{bot.last_run ? new Date(bot.last_run).toLocaleTimeString() : 'never'}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top 5 Recommendations */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Latest Intelligence</h3>
        {recs.length === 0 ? (
          <p className="text-sm text-slate-500">No recommendations yet.</p>
        ) : (
          <div className="space-y-2">
            {recs.map(rec => {
              const badgeColor = () => {
                switch (rec.recommendation) {
                  case 'BUY': return 'bg-green-600'
                  case 'HOLD': return 'bg-yellow-500'
                  case 'SELL': return 'bg-red-600'
                  case 'ACCUMULATE': return 'bg-blue-600'
                  default: return 'bg-slate-500'
                }
              }
              return (
                <div key={rec.task_id} className="flex items-center gap-3 border-b border-slate-700/50 pb-2">
                  <span className={`text-xs px-2 py-0.5 rounded text-white font-bold ${badgeColor()}`}>
                    {rec.recommendation}
                  </span>
                  <span className="font-bold text-sm">{rec.key_metrics?.ticker || '?'}</span>
                  <span className="text-xs text-slate-400 flex-1 truncate">{rec.summary}</span>
                  <span className="text-xs text-slate-500">{rec.confidence}%</span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Live Feed */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Live Feed</h3>
        {feed.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {feed.map((entry, i) => (
              <div key={i} className="text-xs font-mono text-slate-300 border-b border-slate-700/30 pb-1">
                {entry}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default WarRoom
