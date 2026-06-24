// Thin fetch wrappers around the SecureGuard backend.

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function authHeaders(apiKey) {
  return { "X-API-Key": apiKey };
}

// Map common status codes to human messages (mirrors the analyze flow).
function describeStatus(status) {
  if (status === 401) return "Invalid or missing API key";
  if (status === 404) return "Not found";
  if (status === 429) return "Rate limit reached — try again later";
  return `Request failed (${status})`;
}

export async function fetchHistory(apiKey) {
  const resp = await fetch(`${BACKEND_URL}/history`, { headers: authHeaders(apiKey) });
  if (!resp.ok) throw new Error(describeStatus(resp.status));
  return (await resp.json()).history;
}

export async function fetchHistoryDetail(apiKey, submissionId) {
  const resp = await fetch(`${BACKEND_URL}/history/${encodeURIComponent(submissionId)}`, {
    headers: authHeaders(apiKey),
  });
  if (!resp.ok) throw new Error(describeStatus(resp.status));
  return await resp.json();
}

// Stream an analysis over SSE, dispatching each event to `onEvent`.
export async function analyzeStream(apiKey, code, language, onEvent) {
  const response = await fetch(`${BACKEND_URL}/analyze/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(apiKey) },
    body: JSON.stringify({ code, language }),
  });

  if (response.status === 401) throw new Error("Invalid or missing API key");
  if (response.status === 422) throw new Error("Invalid input (check size/language)");
  if (response.status === 429) throw new Error("Rate limit reached — try again later");
  if (!response.ok || !response.body) throw new Error(`Request failed (${response.status})`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()));
      } catch {
        // ignore malformed frame
      }
    }
  }
}
