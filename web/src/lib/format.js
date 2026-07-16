// Small formatting helpers shared by the provenance-UX components. None of these invent a value, they only render
// what the engine returns (and explicitly show "n/a" when the engine abstained, never a guessed placeholder).

export const num = (x, dp = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "n/a" : Number(x).toFixed(dp).replace(/\.?0+$/, "");

export const pct = (x, dp = 0) =>
  x === null || x === undefined || Number.isNaN(x) ? "n/a" : `${(Number(x) * 100).toFixed(dp)}%`;

export const titleCase = (s) =>
  String(s || "").replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const humanize = (s) => String(s || "").replace(/[_-]+/g, " ");

// Input-validation helpers (client-side): flag clearly out-of-domain input rather than silently
// accepting it. The engine remains authoritative; these only surface a warning next to the field.

// The unique characters in a pasted sequence that are NOT valid nucleotide symbols (A/C/G/T/U/N), ignoring
// whitespace. Empty array => the input is clean (or empty). Used to warn on non-nucleotide sequence input.
export function invalidNucleotides(seq) {
  const cleaned = String(seq || "").toUpperCase().replace(/\s+/g, "");
  return [...new Set(cleaned.split("").filter((c) => !"ACGTUN".includes(c)))];
}

// Clamp an integer into [lo, hi]; returns {value, clamped} so a caller can show a "clamped to X" note.
export function clampInt(raw, lo, hi, fallback = lo) {
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return { value: fallback, clamped: false };
  const value = Math.min(hi, Math.max(lo, n));
  return { value, clamped: value !== n };
}

// Map a verdict/axis epistemic state to one of the three provenance-UX statuses the ConfidenceBand colours by.
export function statusOf({ in_scope, validation, epistemic_status } = {}) {
  if (in_scope === false) return "out_of_scope";
  if (epistemic_status && /out.?of.?scope|not.?computable|deferred/i.test(epistemic_status)) return "out_of_scope";
  if (validation && /not outcome-validated|proxy|partial|extrapolat/i.test(validation)) return "extrapolating";
  if (epistemic_status && /extrapolat|ood|uncertain/i.test(epistemic_status)) return "extrapolating";
  return "grounded";
}

export const STATUS_COLOR = {
  grounded: "var(--ok)",
  extrapolating: "var(--warn)",
  out_of_scope: "var(--muted)",
};

export const SAFETY_COLOR = {
  clear: "var(--ok)",
  flag: "var(--warn)",
  escalate: "var(--warn)",
  refuse: "var(--bad)",
};
