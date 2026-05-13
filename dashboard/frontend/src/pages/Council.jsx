import { useState, useEffect } from "react";
import { API_URL } from "../config";

export default function Council() {
  const [councils, setCouncils] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/council`)
      .then((r) => r.json())
      .then((d) => {
        setCouncils(d.councils || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const badge = (verdict) => {
    const base = "inline-block px-2 py-0.5 rounded text-xs font-bold";
    if (verdict.includes("STRONG")) return `${base} bg-emerald-500/20 text-emerald-400 border border-emerald-500/30`;
    if (verdict.includes("MILD")) return `${base} bg-amber-500/20 text-amber-400 border border-amber-500/30`;
    return `${base} bg-red-500/20 text-red-400 border border-red-500/30`;
  };

  if (loading) return <div className="text-center py-20 text-slate-400">Loading War Room...</div>;
  if (!councils.length) return <div className="text-center py-20 text-slate-400">No council meetings yet.</div>;

  const active = selected || councils[0];

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-1">War Room</h2>
      <p className="text-sm text-slate-400 mb-6">Council meetings where all bots vote and debate each recommendation.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* List */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Meetings</h3>
          {councils.map((c) => (
            <button
              key={c.ticker + c.date}
              onClick={() => setSelected(c)}
              className={`w-full text-left px-3 py-2 rounded border text-sm ${
                active?.ticker === c.ticker && active?.date === c.date
                  ? "bg-slate-700 border-slate-500 text-slate-200"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-100">{c.ticker}</span>
                <span className={badge(c.consensus?.verdict || "")}>{c.consensus?.recommendation}</span>
              </div>
              <div className="flex justify-between text-xs mt-1">
                <span className="text-slate-500">{c.date}</span>
                <span className="text-slate-500">{c.consensus?.confidence || 0}% agreement</span>
              </div>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2 space-y-4">
          {active && (
            <>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h3 className="text-xl font-bold text-slate-100">{active.ticker}</h3>
                    <p className="text-xs text-slate-500">{active.date} · {active.timestamp?.slice(11, 16) || ""}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-extrabold text-slate-100">{active.consensus?.recommendation}</span>
                    <div className={`text-sm font-semibold ${active.consensus?.verdict?.includes("STRONG") ? "text-emerald-400" : active.consensus?.verdict?.includes("MILD") ? "text-amber-400" : "text-red-400"}`}>
                      {active.consensus?.confidence}% {active.consensus?.verdict}
                    </div>
                    {active.consensus?.position_size_boost_pct > 0 && (
                      <div className="text-xs text-emerald-400 mt-1">+{Math.round(active.consensus.position_size_boost_pct * 100)}% size boost</div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Vote Breakdown</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 border-b border-slate-700">
                      <th className="text-left py-1">Bot</th>
                      <th className="text-left py-1">Vote</th>
                      <th className="text-left py-1">Confidence</th>
                      <th className="text-left py-1">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(active.votes || []).map((v) => (
                      <tr key={v.bot} className="border-b border-slate-700/50">
                        <td className="py-2 text-slate-200">{v.bot}</td>
                        <td className="py-2">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-bold ${
                            v.recommendation === "BUY" ? "bg-emerald-500/20 text-emerald-400" :
                            v.recommendation === "ACCUMULATE" ? "bg-teal-500/20 text-teal-400" :
                            v.recommendation === "SELL" ? "bg-red-500/20 text-red-400" :
                            v.recommendation === "WATCH" ? "bg-amber-500/20 text-amber-400" :
                            "bg-slate-600/30 text-slate-300"
                          }`}>
                            {v.recommendation}
                          </span>
                        </td>
                        <td className="py-2 text-slate-300">{v.confidence}%</td>
                        <td className="py-2 text-slate-400">{v.weight}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {active.memo_path && (
                <div className="bg-red-900/10 rounded-lg p-4 border border-red-500/20">
                  <h3 className="text-sm font-bold text-red-400 uppercase tracking-wider mb-1">Disagreement Memo</h3>
                  <p className="text-xs text-slate-400">Consensus was below 60%. A memo was written at:</p>
                  <p className="text-xs text-slate-500 mt-1 font-mono">{active.memo_path}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
