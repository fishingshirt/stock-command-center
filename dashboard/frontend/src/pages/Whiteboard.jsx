import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Whiteboard() {
  const [board, setBoard] = useState(null)

  useEffect(() => {
    fetch(`${API_URL}/api/whiteboard`)
      .then(r => r.json())
      .then(setBoard)
      .catch(() => setBoard(null))

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/whiteboard`).then(r => r.json()).then(setBoard).catch(() => {})
    }, 60000)
    return () => clearInterval(iv)
  }, [])

  const renderColumn = (title, tasks, colorClass) => (
    <div className={`flex-1 min-w-[260px] bg-slate-800/60 rounded-xl border border-slate-700 p-4`}>
      <div className={`text-xs uppercase tracking-wide font-bold mb-3 ${colorClass}`}>{title} ({tasks.length})</div>
      <div className="space-y-3">
        {tasks.map((t, i) => (
          <div key={i} className="bg-slate-900 rounded-lg p-3 border border-slate-700">
            <div className="text-xs text-violet-400 font-mono mb-1">{t.task_id}</div>
            <div className="text-sm font-semibold mb-1">{t.subject || '(no subject)'}</div>
            <div className="text-xs text-slate-400">Bot: {t.assigned_bot || 'unknown'}</div>
            {t.priority && <div className={`text-xs mt-1 inline-block px-2 py-0.5 rounded ${t.priority === 'high' ? 'bg-red-900/50 text-red-300' : t.priority === 'medium' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-green-900/50 text-green-300'}`}>{t.priority}</div>}
            {t.summary && <div className="text-xs text-slate-300 mt-2 border-t border-slate-700 pt-1">{t.summary}</div>}
          </div>
        ))}
      </div>
    </div>
  )

  if (!board) return <div className="text-slate-400">Loading whiteboard...</div>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Live Whiteboard</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {renderColumn('To Do', board['To Do'] || [], 'text-slate-300')}
        {renderColumn('In Progress', board['In Progress'] || [], 'text-yellow-400')}
        {renderColumn('Done', board['Done'] || [], 'text-green-400')}
      </div>
    </div>
  )
}

export default Whiteboard
