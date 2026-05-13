/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Advisor() {
  const [pitchbooks, setPitchbooks] = useState([])
  const [strategies, setStrategies] = useState({})
  const [portfolioTarget, setPortfolioTarget] = useState(null)
  const [selectedPitch, setSelectedPitch] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/pitchbooks`)
      .then(r => r.json())
      .then(d => setPitchbooks(d.pitchbooks || []))
      .catch(() => setPitchbooks([]))

    fetch(`${API_URL}/api/strategies`)
      .then(r => r.json())
      .then(d => setStrategies(d.strategy_stats || {}))
      .catch(() => setStrategies({}))

    setLoading(false)

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/pitchbooks`).then(r => r.json()).then(d => setPitchbooks(d.pitchbooks || [])).catch(() => {})
      fetch(`${API_URL}/api/strategies`).then(r => r.json()).then(d => setStrategies(d.strategy_stats || {})).catch(() => {})
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

  const strategyBadge = (s) => {
    switch (s) {
      case 'MOMENTUM': return 'text-pink-400'
      case 'VALUE': return 'text-emerald-400'
      case 'GROWTH': return 'text-blue-400'
      case 'QUALITY': return 'text-amber-400'
      default: return 'text-slate-400'
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Smart Financial Advisor</h2>

      {/* Strategy Performance */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Strategy Performance</h3>
        {Object.keys(strategies).length === 0 ? (
          <p className="text-sm text-slate-500">No closed trades yet. Strategies will appear after positions close.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(strategies).map(([name, stats]) => (
              <div key={name} className="bg-slate-900 rounded-lg p-3 border border-slate-700">
                <div className={`text-xs font-bold ${strategyBadge(name)} mb-1`}>{name}</div>
                <div className="text-lg font-bold">{stats.trades}</div>
                <div className="text-xs text-slate-400">trades</div>
                <div className="text-sm text-slate-200 mt-1">Win {stats.win_rate}%</div>
                <div className="text-sm text-slate-200">Avg {stats.avg_return_pct}%</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pitchbook Cards */}
      {loading ? (
        <p className="text-slate-400">Loading pitchbooks...</p>
      ) : pitchbooks.length === 0 ? (
        <p className="text-slate-400">No pitchbooks generated yet. Complete a research task to see investment memos.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pitchbooks.map((pb, idx) => (
            <div key={idx} className="bg-slate-800 rounded-xl border border-slate-700 p-5 hover:border-violet-500/50 transition cursor-pointer"
                 onClick={() => setSelectedPitch(pb)}>
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-bold">{pb.ticker}</h3>
                <span className={`text-xs px-2 py-1 rounded ${badgeColor(pb.recommendation)}`}>{pb.recommendation}</span>
              </div>
              <p className="text-sm text-slate-300 mb-2 line-clamp-2">{pb.summary}</p>
              <div className="flex justify-between text-xs text-slate-400">
                <span className={strategyBadge(pb.strategy)}>Strategy: {pb.strategy}</span>
                <span>Confidence {pb.confidence}%</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">
                MoS: {pb.margin_of_safety}% | Target: ${pb.model_target}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pitchbook Modal */}
      {selectedPitch && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-6" onClick={() => setSelectedPitch(null)}>
          <div className="bg-slate-800 rounded-xl border border-slate-600 max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6"
               onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold">Investment Memo: {selectedPitch.ticker}</h2>
              <span className={`text-sm px-3 py-1 rounded ${badgeColor(selectedPitch.recommendation)}`}>
                {selectedPitch.recommendation} ({selectedPitch.confidence}%)
              </span>
            </div>
            <div className="text-sm text-slate-400 mb-4">Strategy: <span className={strategyBadge(selectedPitch.strategy)}>{selectedPitch.strategy}</span></div>
            <div className="prose prose-invert max-w-none text-sm text-slate-300 whitespace-pre-wrap">
              {selectedPitch.content}
            </div>
            <div className="mt-4 bg-slate-900 rounded-lg p-3 text-xs text-slate-400 space-y-1">
              <div><span className="text-violet-400">DCF Target:</span> ${selectedPitch.dcf_target}</div>
              <div><span className="text-violet-400">Comps Target:</span> ${selectedPitch.comps_target}</div>
              <div><span className="text-violet-400">Blended Target:</span> ${selectedPitch.model_target}</div>
              <div><span className="text-violet-400">Margin of Safety:</span> {selectedPitch.margin_of_safety}%</div>
              <div><span className="text-violet-400">Compliance:</span> {selectedPitch.kyc_risk} ({selectedPitch.compliance_score}/100)</div>
            </div>
            <button onClick={() => setSelectedPitch(null)} className="mt-4 bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded text-sm">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Advisor
