// Small shared primitives (presentation only). The 14 pages build on these, so the design system lives here.
import React from "react";
import { Icon } from "./icons.jsx";

export function Card({ title, subtitle, icon, right, hover = false, children, className = "" }) {
  return (
    <section className={`card p-4 sm:p-5 ${hover ? "card-hover" : ""} ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            {icon && <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand/10 text-brand"><Icon name={icon} size={16} /></span>}
            <div>
              {title && <h3 className="text-sm font-semibold text-fg">{title}</h3>}
              {subtitle && <p className="mt-0.5 text-xs text-fg-dim">{subtitle}</p>}
            </div>
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function Button({ variant = "primary", size, className = "", children, icon, ...p }) {
  const v = variant === "primary" ? "btn-primary" : variant === "secondary" ? "btn-secondary" : "btn-ghost";
  const s = size === "sm" ? "px-2.5 py-1.5 text-xs" : "";
  return (
    <button className={`${v} ${s} ${className}`} {...p}>
      {icon && <Icon name={icon} size={16} />}{children}
    </button>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      {label && <span className="label">{label}</span>}
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
    <div className="rounded-lg border border-line bg-ink-900/70 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-fg-faint">{label}</div>
      <div className="mt-0.5 text-lg font-semibold tabular-nums" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}

export function Pill({ children, color }) {
  return <span className="chip" style={color ? { color, borderColor: color + "55" } : undefined}>{children}</span>;
}

const TONE = {
  ok: { color: "var(--ok)", bg: "rgba(63,185,80,0.12)" },
  warn: { color: "var(--warn)", bg: "rgba(210,153,34,0.12)" },
  bad: { color: "var(--bad)", bg: "rgba(248,81,73,0.12)" },
  brand: { color: "var(--brand)", bg: "rgba(94,200,216,0.12)" },
  neutral: { color: "var(--muted)", bg: "rgba(110,118,129,0.12)" },
};
export function Badge({ tone = "neutral", children }) {
  const t = TONE[tone] || TONE.neutral;
  return <span className="badge" style={{ color: t.color, background: t.bg }}>{children}</span>;
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

export function Skeleton({ className = "h-4 w-full" }) {
  return <div className={`skeleton ${className}`} />;
}

// Consistent page header (icon + title + subtitle + optional actions). Driven by nav metadata in the shell.
export function PageHeader({ icon, title, subtitle, actions }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {icon && (
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-brand/25 bg-brand/10 text-brand">
            <Icon name={icon} size={20} />
          </span>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
          {subtitle && <p className="mt-0.5 max-w-2xl text-sm text-fg-dim">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
