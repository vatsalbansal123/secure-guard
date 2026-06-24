import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge, ConfidenceBar } from "./ui.jsx";
import { SEVERITY_BADGE, STATUS_BADGE } from "./theme.js";
import { CodeDiff } from "./editor.jsx";

// One finding + its (optional) AI-generated, checker-verified fix.
// `originalCode` is the submitted source for the side-by-side diff; it is null
// when viewing history (the server never stores submitted code).
export function FindingCard({ finding, language, originalCode }) {
  const fix = finding.fix;
  const sev = SEVERITY_BADGE[finding.severity] || SEVERITY_BADGE.Medium;
  const status = STATUS_BADGE[finding.status] || STATUS_BADGE.confirmed;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-slate-100">{finding.name}</span>
        <Badge cls={sev}>{finding.severity}</Badge>
        <Badge cls={status.cls}>{status.label}</Badge>
        <span className="text-xs text-slate-500">{finding.rule_id}</span>
        {finding.line_hint != null && (
          <span className="text-xs text-slate-500">line ~{finding.line_hint}</span>
        )}
      </div>
      <p className="mt-2 text-sm text-slate-300">{finding.description}</p>
      <div className="mt-2"><ConfidenceBar value={finding.confidence} /></div>

      {fix && (
        <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-200">Suggested fix</span>
            <Badge cls={(STATUS_BADGE[fix.status] || STATUS_BADGE.needs_review).cls}>
              {(STATUS_BADGE[fix.status] || STATUS_BADGE.needs_review).label}
            </Badge>
            {fix.owasp_reference && (
              <span className="text-xs text-slate-500">{fix.owasp_reference}</span>
            )}
          </div>
          <div className="mt-2"><ConfidenceBar value={fix.confidence} /></div>

          {/* LLM09 mitigation: never present an AI fix as authoritative. */}
          <p className="mt-2 text-xs text-amber-400/90">
            ⚠ AI-generated fix — review and test before applying.
            {fix.checker_note ? ` Reviewer note: ${fix.checker_note}` : ""}
          </p>

          {fix.fixed_code && (
            <div className="mt-3">
              <CodeDiff original={originalCode} fixed={fix.fixed_code} language={language} />
            </div>
          )}
          {fix.explanation && (
            <div className="mt-3 text-sm leading-relaxed text-slate-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{fix.explanation}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Shared "Findings & Fixes" list panel.
export function FindingsPanel({ result, language, originalCode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
      <h2 className="mb-4 text-xl font-semibold">Findings &amp; Fixes</h2>
      {result && result.length > 0 ? (
        <div className="space-y-3">
          {result.map((finding, i) => (
            <FindingCard
              key={`${finding.rule_id}-${i}`}
              finding={finding}
              language={language}
              originalCode={originalCode}
            />
          ))}
        </div>
      ) : result ? (
        <p className="text-slate-400">No issues detected. ✅</p>
      ) : (
        <p className="text-slate-500">No analysis results yet.</p>
      )}
    </div>
  );
}
