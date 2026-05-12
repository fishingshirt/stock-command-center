import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Archive() {
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/api/archive?page=${page}`)
      .then(r => r.json())
      .then(d => { setItems(d.items || []); setTotal(d.total || 0) })
      .catch(() => { setItems([]); setTotal(0) })
  }, [page])

  const filtered = items.filter(it =>
    (it.subject || '').toLowerCase().includes(search.toLowerCase()) ||
    (it.task_id || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Historical Archive</h2>
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search ticker or subject..."
        className="w-full max-w-md bg-slate-800 border border-slate-700 rounded px-4 py-2 text-sm text-slate-50 placeholder-slate-500 focus:outline-none focus:border-violet-500"
      />
      <div className="space-y-2">
        {filtered.map((it, idx) => (
          <div key={idx} className="bg-slate-800 border border-slate-700 rounded-lg p-4">
            <div className="flex justify-between">
              <span className="font-bold">{it.task_id}</span>
              <span className={`text-xs px-2 py-1 rounded ${it.recommendation === 'BUY' ? 'bg-green-600' : it.recommendation === 'SELL' ? 'bg-red-600' : 'bg-yellow-500'}`}>
                {it.recommendation}
              </span>
            </div>
            <p className="text-sm text-slate-300 mt-1">{it.subject}</p>
            <div className="text-xs text-slate-500 mt-2">
              {it.timestamp ? new Date(it.timestamp).toLocaleString() : ''}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-slate-500">No archived results found.</p>
        )}
      </div>
      {total > 10 && (
        <div className="flex gap-3 text-sm">
          <button className="px-3 py-1 rounded bg-slate-800 border border-slate-700 disabled:opacity-50" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Prev</button>
          <span className="text-slate-400">Page {page}</span>
          <button className="px-3 py-1 rounded bg-slate-800 border border-slate-700 disabled:opacity-50" disabled={page*10>=total} onClick={()=>setPage(p=>p+1)}>Next</button>
        </div>
      )}
    </div>
  )
}

export default Archive
