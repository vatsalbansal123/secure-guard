import { useState } from "react";

import { analyzeStream } from "./api.js";
import { ScorePanel } from "./ui.jsx";
import { LANGUAGES } from "./theme.js";
import { CodeEditor } from "./editor.jsx";
import { FindingsPanel } from "./FindingCard.jsx";
import { HistoryView } from "./History.jsx";

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
        active ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800"
      }`}
    >
      {children}
    </button>
  );
}

function App() {
  const [tab, setTab] = useState("analyze");
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const [score, setScore] = useState(null);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("sg_api_key") || "");
  const [language, setLanguage] = useState("python");
  // The code that produced the currently displayed result — used for the
  // side-by-side diff (server never returns the original source).
  const [analyzedCode, setAnalyzedCode] = useState(null);

  // submission_id → submitted code, for THIS browser session only. Lets the
  // history tab offer "reanalyze" without the server ever storing source code.
  const [sessionCode, setSessionCode] = useState({});

  // Persist the API key locally so the developer doesn't re-enter it each time.
  const onApiKeyChange = (value) => {
    setApiKey(value);
    localStorage.setItem("sg_api_key", value);
  };

  // Apply a single SSE event to component state.
  const handleEvent = (event) => {
    switch (event.type) {
      case "step":
        setSteps((prev) => {
          const next = [...prev];
          const idx = next.findIndex((s) => s.id === event.id);
          const entry = { id: event.id, label: event.label, status: event.status };
          if (idx === -1) next.push(entry); else next[idx] = entry;
          return next;
        });
        break;
      case "result":
        setResult(event.data);
        break;
      case "score":
        setScore(event.data);
        break;
      case "token":
        setAnalysis((prev) => prev + event.data);
        break;
      case "error":
        alert("Analysis failed: " + event.data);
        break;
      default:
        break;
    }
  };

  const runAnalysis = async (theCode, theLanguage) => {
    try {
      setLoading(true);
      setSteps([]);
      setResult(null);
      setAnalysis("");
      setScore(null);
      setAnalyzedCode(theCode);
      await analyzeStream(apiKey, theCode, theLanguage, (event) => {
        // Remember which code produced this submission (this session only) so
        // history can offer "reanalyze" without the server ever storing source.
        if (event.type === "submission") {
          if (event.submission_id) {
            setSessionCode((prev) => ({ ...prev, [event.submission_id]: theCode }));
          }
          return;
        }
        handleEvent(event);
      });
    } catch (error) {
      console.error(error);
      alert(error.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const analyzeCode = () => runAnalysis(code, language);

  // Invoked from history: load the code back into the editor and re-run.
  const reanalyze = (savedCode, savedLanguage) => {
    setCode(savedCode);
    if (savedLanguage) setLanguage(savedLanguage);
    setTab("analyze");
    runAnalysis(savedCode, savedLanguage || language);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto max-w-9xl px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold">SecureGuard</h1>
              <p className="mt-1 text-slate-400">AI-powered source code security analyzer</p>
            </div>
            <nav className="flex gap-2 rounded-xl border border-slate-800 bg-slate-900 p-1">
              <TabButton active={tab === "analyze"} onClick={() => setTab("analyze")}>Analyze</TabButton>
              <TabButton active={tab === "history"} onClick={() => setTab("history")}>History</TabButton>
            </nav>
          </div>
        </div>
      </header>

      <main className="mx-auto p-6">
        {tab === "history" ? (
          <HistoryView apiKey={apiKey} sessionCode={sessionCode} onReanalyze={reanalyze} />
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Input */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
              <h2 className="mb-4 text-xl font-semibold">Source Code</h2>

              <div className="mb-4 flex flex-col gap-3 sm:flex-row">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => onApiKeyChange(e.target.value)}
                  placeholder="API key (X-API-Key)"
                  className="flex-1 rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm outline-none transition focus:border-blue-500"
                />
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm outline-none transition focus:border-blue-500"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>

              <CodeEditor
                value={code}
                onChange={setCode}
                language={language}
                placeholder="Paste your code here..."
              />

              <button
                onClick={analyzeCode}
                disabled={loading || !code.trim() || !apiKey.trim()}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 font-semibold transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze Code"
                )}
              </button>

              {steps.length > 0 && (
                <div className="mt-5 space-y-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                    Progress
                  </h3>
                  {steps.map((step) => (
                    <div key={step.id} className="flex items-center gap-3 text-sm">
                      {step.status === "done" ? (
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500/20 text-green-400">✓</span>
                      ) : (
                        <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500/30 border-t-blue-400" />
                      )}
                      <span className={step.status === "done" ? "text-slate-300" : "text-blue-300"}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Results */}
            <div className="space-y-6">
              <ScorePanel score={score} />
              <FindingsPanel result={result} language={language} originalCode={analyzedCode} />

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                <h2 className="mb-4 text-xl font-semibold">LLM Analysis</h2>
                {analysis ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-left font-mono leading-relaxed text-slate-200 whitespace-pre-wrap">
                    {analysis}
                    {loading && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-blue-400 align-middle" />}
                  </div>
                ) : (
                  <p className="text-slate-500">AI analysis will appear here.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
