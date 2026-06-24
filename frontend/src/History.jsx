import { useEffect, useState } from "react";

import { fetchHistory, fetchHistoryDetail } from "./api.js";
import { ScorePanel, SeveritySummary } from "./ui.jsx";
import { scoreTextColor } from "./theme.js";
import { FindingsPanel } from "./FindingCard.jsx";

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// Past submissions for the authenticated developer. The list and every detail
// load are scoped server-side to the caller's API key (IDOR-safe). The server
// never returns the original source, so "Reanalyze" is only possible when this
// browser session still holds the code (sessionCode), reinforcing that we don't
// persist proprietary code.
export function HistoryView({ apiKey, sessionCode, onReanalyze }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = async () => {
    if (!apiKey) {
      setError("Enter your API key on the Analyze tab first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setList(await fetchHistory(apiKey));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Load once when the tab is shown.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openDetail = async (id) => {
    setDetailLoading(true);
    setError("");
    try {
      setSelected(await fetchHistoryDetail(apiKey, id));
    } catch (e) {
      setError(e.message);
    } finally {
      setDetailLoading(false);
    }
  };

  if (selected) {
    const code = sessionCode[selected.id] ?? null;
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setSelected(null)}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800"
          >
            ← Back to history
          </button>
          <button
            onClick={() => code != null && onReanalyze(code, selected.language)}
            disabled={code == null}
            title={code == null
              ? "Original code isn’t stored on the server (privacy). Paste it on the Analyze tab to re-run."
              : "Re-run the analysis to verify a fix worked"}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ↻ Reanalyze
          </button>
        </div>
        <p className="text-sm text-slate-400">
          {selected.language} · {fmtTime(selected.created_at)} · {selected.finding_count} finding(s)
        </p>
        <ScorePanel score={selected.score} />
        <FindingsPanel result={selected.result} language={selected.language} originalCode={code} />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Analysis History</h2>
        <button
          onClick={load}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      {loading && <p className="text-slate-400">Loading…</p>}

      {list && list.length === 0 && !loading && (
        <p className="text-slate-500">No submissions yet. Analyze some code to get started.</p>
      )}

      {list && list.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-400">
              <tr className="border-b border-slate-800">
                <th className="py-2 pr-4">When</th>
                <th className="py-2 pr-4">Language</th>
                <th className="py-2 pr-4">Findings</th>
                <th className="py-2 pr-4">Severity</th>
                <th className="py-2 pr-4">Grade</th>
              </tr>
            </thead>
            <tbody>
              {list.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => openDetail(row.id)}
                  className="cursor-pointer border-b border-slate-800/60 hover:bg-slate-800/40"
                >
                  <td className="py-2 pr-4 text-slate-300">{fmtTime(row.created_at)}</td>
                  <td className="py-2 pr-4 text-slate-300">{row.language}</td>
                  <td className="py-2 pr-4 text-slate-300">{row.finding_count}</td>
                  <td className="py-2 pr-4"><SeveritySummary counts={row.severity_counts} /></td>
                  <td className={`py-2 pr-4 font-semibold ${scoreTextColor(row.score ?? 0)}`}>
                    {row.grade ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detailLoading && <p className="mt-3 text-slate-400">Loading report…</p>}
    </div>
  );
}
