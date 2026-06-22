// Small shared primitives (Card, Button, Field, Spinner, Stat, Pill, ErrorNote, Empty). Pure presentation.
import React from "react";

export function Card({ title, subtitle, right, children, className = "" }) {
  return (
    <section className={`card p-4 sm:p-5 ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div>
            {title && <h3 className="text-sm font-semibold text-fg">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-xs text-fg-dim">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function Button({ variant = "primary", className = "", ...p }) {
  return <button className={`${variant === "primary" ? "btn-primary" : "btn-ghost"} ${className}`} {...p} />;
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-fg-faint">{hint}</span>}
    </label>
  );
}

export function Select({ value, onChange, options }) {
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
      ))}
    </select>
  );
}

export function Spinner({ label = "Running the engine…" }) {
  return (
    <div className="flex items-center gap-2 text-sm text-fg-dim">
      <span className="dotpulse h-2 w-2 rounded-full bg-brand" />
      <span className="dotpulse h-2 w-2 rounded-full bg-brand" style={{ animationDelay: "0.2s" }} />
      <span className="dotpulse h-2 w-2 rounded-full bg-brand" style={{ animationDelay: "0.4s" }} />
      <span className="ml-1">{label}</span>
    </div>
  );
}

export function Stat({ label, value, color }) {
  return (
    <div className="rounded-lg border border-line bg-ink-900 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-fg-faint">{label}</div>
      <div className="mt-0.5 text-lg font-semibold tabular-nums" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}

export function Pill({ children, color }) {
  return (
    <span className="chip" style={color ? { color, borderColor: color + "55" } : undefined}>{children}</span>
  );
}

export function ErrorNote({ error }) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
      <strong className="font-semibold">Engine error.</strong> {String(error.message || error)}
      <div className="mt-1 text-xs text-fg-dim">If a data file is missing, that endpoint needs the full data
        mount (VM); the system never invents a value to fill the gap.</div>
    </div>
  );
}

export function Empty({ children }) {
  return <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm text-fg-faint">{children}</div>;
}
