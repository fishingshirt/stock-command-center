import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Holdings() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/holdings`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/holdings`).then(r => r.json()).then(setData).catch(() => {})
    }, 30000)
    return () => clearInterval(iv)
  }, [])

  if (loading) return <div className="text-center py-20 text-slate-400">Loading Holdings...</div>
  if (!data) return <div className="text-center py-20 text-slate-400">No holdings data.</div>

  const holdings = data.holdings || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">My Holdings</h2>
          <p className="text-sm text-slate-400">Real portfolio symbols tracked by SCC</p>
        </div>
        <div className="px-3 py-1 rounded text-xs font-bold bg-violet-600 text-white">
          {holdings.length} Symbols
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {holdings.map(h => (
          <div key={h.ticker} className="bg-slate-800 border border-slate-700 rounded-xl p-4 hover:border-violet-500 transition">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xl font-bold">{h.ticker}</span>
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{h.note}</span>
            </div>
            <div className="flex items-end gap-2">
              {h.shares && <div className="text-2xl font-mono">{h.shares} <span className="text-sm text-slate-400">shares</span></div>}
              {h.value_usd && <div className="text-2xl font-mono">${h.value_usd.toFixed(2)}</div>}
            </div>
            <div className="mt-2 text-xs text-slate-400">Click for research →</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Holdings
