// Shared presentational components.

import {
  SEVERITY_BADGE, confidenceColor, scoreColor, scoreTextColor,
} from "./theme.js";

export function Badge({ children, cls }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

// A single confidence bar (0..1).
export function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-700">
        <div className={`h-full ${confidenceColor(value)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400">{pct}% confidence</span>
    </div>
  );
}

// Compact severity summary (used in history rows and detail headers).
export function SeveritySummary({ counts }) {
  const c = counts || {};
  const items = [
    ["Critical", c.Critical], ["High", c.High], ["Medium", c.Medium], ["Low", c.Low],
  ].filter(([, n]) => n > 0);
  if (items.length === 0) return <span className="text-xs text-green-400">clean</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {items.map(([sev, n]) => (
        <Badge key={sev} cls={SEVERITY_BADGE[sev]}>{sev[0]}:{n}</Badge>
      ))}
    </span>
  );
}

// The security score card, shared by the live view and history detail.
export function ScorePanel({ score }) {
  if (!score) return null;
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
      <h2 className="mb-4 text-xl font-semibold">Security Score</h2>
      <div className="flex items-center gap-6">
        <div className={`flex h-24 w-24 flex-col items-center justify-center rounded-full border-4 ${scoreColor(score.score)}`}>
          <span className="text-3xl font-bold">{score.score}</span>
          <span className="text-xs text-slate-400">/ 100</span>
        </div>
        <div className="space-y-2">
          <p className="text-lg font-semibold">
            Grade: <span className={scoreTextColor(score.score)}>{score.grade}</span>
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-red-500/20 px-2 py-1 text-red-300">Critical: {score.counts?.Critical ?? 0}</span>
            <span className="rounded-full bg-orange-500/20 px-2 py-1 text-orange-300">High: {score.counts?.High ?? 0}</span>
            <span className="rounded-full bg-yellow-500/20 px-2 py-1 text-yellow-300">Medium: {score.counts?.Medium ?? 0}</span>
            <span className="rounded-full bg-blue-500/20 px-2 py-1 text-blue-300">Low: {score.counts?.Low ?? 0}</span>
          </div>
        </div>
      </div>
      {score.summary && (
        <p className="mt-4 text-sm leading-relaxed text-slate-300">{score.summary}</p>
      )}
    </div>
  );
}
