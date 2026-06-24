// CodeMirror-based code input and display.
//
// SECURITY (Week 5, Tue): the fixed code and the submitted code are rendered
// here. CodeMirror builds the highlighted view from DOM text nodes — it never
// parses our content as HTML and there is no `dangerouslySetInnerHTML` in this
// file (or anywhere in src/). So even though `fixed_code` comes from an LLM, it
// is always shown as inert plain text, not executed/injected markup.

import CodeMirror from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { java } from "@codemirror/lang-java";
import { php } from "@codemirror/lang-php";
import { sql } from "@codemirror/lang-sql";
import { rust } from "@codemirror/lang-rust";
import { cpp } from "@codemirror/lang-cpp";

// Map our language enum to a CodeMirror language extension. Unknown/unsupported
// languages fall back to no grammar (still rendered safely as plain text).
function langExtension(language) {
  switch (language) {
    case "python": return [python()];
    case "javascript": return [javascript()];
    case "typescript": return [javascript({ typescript: true })];
    case "java": return [java()];
    case "php": return [php()];
    case "sql": return [sql()];
    case "rust": return [rust()];
    case "c":
    case "cpp": return [cpp()];
    default: return [];
  }
}

// Editable code input with syntax highlighting.
export function CodeEditor({ value, onChange, language, height = "500px", placeholder }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-700 text-left">
      <CodeMirror
        value={value}
        height={height}
        theme={oneDark}
        placeholder={placeholder}
        extensions={langExtension(language)}
        onChange={onChange}
        basicSetup={{ lineNumbers: true, highlightActiveLine: true, autocompletion: false }}
      />
    </div>
  );
}

// Read-only highlighted view (no editing chrome).
export function CodeView({ value, language, height = "auto" }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 text-left">
      <CodeMirror
        value={value || ""}
        height={height}
        theme={oneDark}
        editable={false}
        extensions={langExtension(language)}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLine: false,
          foldGutter: false,
          highlightActiveLineGutter: false,
        }}
      />
    </div>
  );
}

// Side-by-side "submitted vs suggested fix" comparison.
// `original` may be null (history loaded from the server never includes the
// submitted source — we don't store it), in which case only the fix is shown.
export function CodeDiff({ original, fixed, language }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Submitted
        </div>
        {original != null ? (
          <CodeView value={original} language={language} />
        ) : (
          <p className="rounded-lg border border-dashed border-slate-700 p-3 text-xs italic text-slate-500">
            Original source isn’t stored on the server (your code stays private).
            Re-run from the editor to see a side-by-side comparison.
          </p>
        )}
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-400">
          Suggested fix
        </div>
        <CodeView value={fixed} language={language} />
      </div>
    </div>
  );
}
