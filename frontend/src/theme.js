// Shared constants + color helpers (no components — keeps Fast Refresh happy).

export const LANGUAGES = [
  "python", "javascript", "typescript", "java", "go", "ruby", "php",
  "csharp", "cpp", "c", "rust", "kotlin", "swift", "sql", "shell", "other",
];

export const SEVERITY_BADGE = {
  Critical: "bg-red-500/20 text-red-300",
  High: "bg-orange-500/20 text-orange-300",
  Medium: "bg-yellow-500/20 text-yellow-300",
  Low: "bg-blue-500/20 text-blue-300",
};

// Status → label + color. Surfaces the LLM09 trust signal clearly.
export const STATUS_BADGE = {
  confirmed: { label: "Confirmed", cls: "bg-red-500/20 text-red-300" },
  needs_review: { label: "Needs human review", cls: "bg-yellow-500/20 text-yellow-300" },
  verified: { label: "Fix verified", cls: "bg-green-500/20 text-green-300" },
  rejected: { label: "Fix rejected", cls: "bg-red-500/20 text-red-300" },
};

export const scoreColor = (s) =>
  s >= 75 ? "border-green-500 text-green-400"
    : s >= 50 ? "border-yellow-500 text-yellow-400"
      : "border-red-500 text-red-400";

export const scoreTextColor = (s) =>
  s >= 75 ? "text-green-400" : s >= 50 ? "text-yellow-400" : "text-red-400";

export const confidenceColor = (c) =>
  c >= 0.75 ? "bg-green-500" : c >= 0.5 ? "bg-yellow-500" : "bg-red-500";
