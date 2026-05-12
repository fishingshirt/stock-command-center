import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Home() {
  const [recs, setRecs] = useState([])
  const [sectors, setSectors] = useState({})
  const [feed, setFeed] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetch(`${API_URL}/api/recommendations`)
      .then(r => r.json())
      .then(setRecs)
      .catch(() => setRecs([]))
    fetch(`${API_URL}/api/sectors`)
      .then(r => r.json())
      .then(d => setSectors(d.sectors || {}))
      .catch(() => setSectors({}))
    fetch(`${API_URL}/api/feed`)
      .then(r => r.json())
      .then(d => setFeed(d.entries || []))
      .catch(() => setFeed([]))
    setLoading(false)

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/recommendations`).then(r => r.json()).then(setRecs).catch(() => {})
      fetch(`${API_URL}/api/feed`).then(r => r.json()).then(d => setFeed(d.entries || [])).catch(() => {})
    }, 60000)
    return () => clearInterval(iv)
  }, [])

  const badgeColor = (r) => {
    switch (r) {
      case 'BUY': return 'bg-green-600'
      case 'HOLD': return 'bg-yellow-500'
      case 'SELL': return 'bg-red-600'
      case 'ACCUMULATE': return 'bg-blue-600'
      default: return 'bg-slate-500'
    }
  }

  return (
    <div className="space-y-6">
      {/* Top stats */}
      <div className="flex gap-4">
        {Object.entries(sectors).map(([k,v]) => (
          <div key={k} className="bg-slate-800 px-4 py-3 rounded-lg border border-slate-700">
            <div className="text-xs uppercase text-slate-400">{k}</div>
            <div className="text-2xl font-bold">{v}</div>
          </div>
        ))}
      </div>

      {/* Cards grid */}
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {recs.map((rec, idx) => (
            <div key={idx} className="bg-slate-800 rounded-xl border border-slate-700 p-5 hover:border-violet-500/50 transition cursor-pointer"
                 onClick={() => setSelected(rec)}>
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-bold">{rec.task_id}</h3>
                <span className={`text-xs px-2 py-1 rounded ${badgeColor(rec.recommendation)}`}>
                  {rec.recommendation}
                </span>
              </div>
              <p className="text-sm text-slate-300 mb-3 line-clamp-2">{rec.summary}</p>
              <div className="w-full bg-slate-700 rounded-full h-2 mb-2">
                <div className="bg-violet-500 h-2 rounded-full" style={{width: `${rec.confidence}%`}} />
              </div>
              <div className="flex justify-between text-xs text-slate-400">
                <span>Confidence {rec.confidence}%</span>
                <span className="uppercase">{rec.asset_type}</span>
              </div>
              {rec.key_metrics && Object.keys(rec.key_metrics).length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(rec.key_metrics).slice(0,4).map(([kk,vv]) => (
                    <div key={kk} className="bg-slate-900/50 rounded px-2 py-1">
                      <span className="text-slate-400">{kk.replace(/_/g,' ')}:</span>{' '}
                      <span className="text-slate-100">{typeof vv === 'number' ? vv.toLocaleString(undefined, {maximumFractionDigits:2}) : vv}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-6" onClick={() => setSelected(null)}>
          <div className="bg-slate-800 rounded-xl border border-slate-600 max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6"
               onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold">{selected.subject || selected.task_id}</h2>
              <span className={`text-sm px-3 py-1 rounded ${badgeColor(selected.recommendation)}`}>
                {selected.recommendation} ({selected.confidence}%)
              </span>
            </div>
            <p className="text-slate-300 mb-4">{selected.summary}</p>
            <div className="bg-slate-900/60 rounded-lg p-4 text-sm space-y-2">
              {selected.key_metrics && Object.entries(selected.key_metrics).map(([kk,vv]) => (
                <div key={kk} className="flex justify-between border-b border-slate-700 pb-1">
                  <span className="text-slate-400">{kk.replace(/_/g,' ')}</span>
                  <span className="text-slate-100">{typeof vv === 'number' ? vv.toLocaleString(undefined, {maximumFractionDigits:4}) : vv}</span>
                </div>
              ))}
            </div>
            {selected.full_text && (
              <div className="mt-4 text-sm text-slate-300 prose prose-invert max-w-none whitespace-pre-wrap">
                {selected.full_text}
              </div>
            )}
            <button onClick={() => setSelected(null)} className="mt-6 bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded text-sm">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Pipeline feed */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Pipeline Feed</h3>
        {feed.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <div className="space-y-2 max-h-40 overflow-y-auto text-sm">
            {feed.map((entry, i) => (
              <div key={i} className="text-slate-300 font-mono text-xs border-b border-slate-700/50 pb-1">{entry}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Home
