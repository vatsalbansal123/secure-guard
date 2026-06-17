import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Ring/border color for the score circle.
const scoreColor = (s) => {
  if (s >= 75) return "border-green-500 text-green-400";
  if (s >= 50) return "border-yellow-500 text-yellow-400";
  return "border-red-500 text-red-400";
};

// Text color for the grade letter.
const scoreTextColor = (s) => {
  if (s >= 75) return "text-green-400";
  if (s >= 50) return "text-yellow-400";
  return "text-red-400";
};

function App() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const [score, setScore] = useState(null);

  // Apply a single SSE event to component state.
  const handleEvent = (event) => {
    switch (event.type) {
      case "step":
        setSteps((prev) => {
          const next = [...prev];
          const idx = next.findIndex((s) => s.id === event.id);
          if (idx === -1) {
            next.push({ id: event.id, label: event.label, status: event.status });
          } else {
            next[idx] = { id: event.id, label: event.label, status: event.status };
          }
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

  const analyzeCode = async () => {
    try {
      setLoading(true);
      setSteps([]);
      setResult(null);
      setAnalysis("");
      setScore(null);

      const response = await fetch(`${BACKEND_URL}/analyze/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Read the SSE stream and dispatch each "data:" frame.
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? ""; // keep incomplete frame for next chunk

        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          try {
            handleEvent(JSON.parse(line.slice(5).trim()));
          } catch {
            // ignore malformed frame
          }
        }
      }
    } catch (error) {
      console.error(error);
      alert("Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="mx-auto max-w-9xl px-6 py-5">
          <h1 className="text-3xl font-bold">
            SecureGuard
          </h1>
          <p className="mt-1 text-slate-400">
            AI-powered source code security analyzer
          </p>
        </div>
      </header>

      <main className="mx-auto  p-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Input Section */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
            <h2 className="mb-4 text-xl font-semibold">
              Source Code
            </h2>

            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste your code here..."
              className="h-[500px] w-full rounded-xl border border-slate-700 bg-slate-950 p-4 font-mono text-sm outline-none transition focus:border-blue-500"
            />

<button
  onClick={analyzeCode}
  disabled={loading || !code.trim()}
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
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500/20 text-green-400">
                        ✓
                      </span>
                    ) : (
                      <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500/30 border-t-blue-400" />
                    )}
                    <span
                      className={
                        step.status === "done"
                          ? "text-slate-300"
                          : "text-blue-300"
                      }
                    >
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            )}

          </div>

          {/* Results Section */}
          <div className="space-y-6">
            {score && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                <h2 className="mb-4 text-xl font-semibold">Security Score</h2>
                <div className="flex items-center gap-6">
                  <div
                    className={`flex h-24 w-24 flex-col items-center justify-center rounded-full border-4 ${scoreColor(
                      score.score
                    )}`}
                  >
                    <span className="text-3xl font-bold">{score.score}</span>
                    <span className="text-xs text-slate-400">/ 100</span>
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-semibold">
                      Grade:{" "}
                      <span className={scoreTextColor(score.score)}>
                        {score.grade}
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full bg-red-500/20 px-2 py-1 text-red-300">
                        Critical: {score.counts.Critical}
                      </span>
                      <span className="rounded-full bg-orange-500/20 px-2 py-1 text-orange-300">
                        High: {score.counts.High}
                      </span>
                      <span className="rounded-full bg-yellow-500/20 px-2 py-1 text-yellow-300">
                        Medium: {score.counts.Medium}
                      </span>
                      <span className="rounded-full bg-blue-500/20 px-2 py-1 text-blue-300">
                        Low: {score.counts.Low}
                      </span>
                    </div>
                  </div>
                </div>
                {score.summary && (
                  <p className="mt-4 text-sm leading-relaxed text-slate-300">
                    {score.summary}
                  </p>
                )}
              </div>
            )}

            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
              <h2 className="mb-4 text-xl font-semibold">
                Rule Engine Findings
              </h2>

              {result ? (
<div className="overflow-auto rounded-xl bg-slate-950 p-4 text-sm border border-slate-800">
  <pre className="text-green-300 whitespace-pre-wrap leading-relaxed">
    {JSON.stringify(result, null, 2)}
  </pre>
</div>
              ) : (
                <p className="text-slate-500">
                  No analysis results yet.
                </p>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
              <h2 className="mb-4 text-xl font-semibold">
                LLM Analysis
              </h2>

              {analysis ? (
<div className="rounded-xl bg-slate-950 border border-slate-800 p-4 text-slate-200 whitespace-pre-wrap font-mono leading-relaxed text-left">
  {analysis}
  {loading && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-blue-400 align-middle" />}
</div>
              ) : (
                <p className="text-slate-500">
                  AI analysis will appear here.
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;