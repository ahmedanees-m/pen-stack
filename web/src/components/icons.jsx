// Inline stroke-icon set (dependency-free; keeps the node:20 build lean). One <Icon name=… /> component reads a
// path table. All icons share a 24x24 viewBox, currentColor stroke, round caps/joins.
import React from "react";

const P = {
  // brand / nav
  dna: "M7 4c4 3 6 5 6 8s-2 5-6 8M17 4c-4 3-6 5-6 8s2 5 6 8M8 8h8M8 16h8M9.5 6h5M9.5 18h5",
  home: "M3 11l9-8 9 8M5 9.5V21h5v-6h4v6h5V9.5",
  chat: "M21 11.5a8.5 8.5 0 0 1-12.6 7.4L3 21l2.1-5.4A8.5 8.5 0 1 1 21 11.5Z",
  writespec: "M14 3v5h5M7 3h8l5 5v13H7zM9.5 12h7M9.5 16h5",
  site: "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11ZM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  atlas: "M3 7l9-4 9 4-9 4-9-4ZM3 12l9 4 9-4M3 17l9 4 9-4",
  designer: "M5 3v4M3 5h4M6 17v4M4 19h4M14 4l2.5 5.5L22 12l-5.5 2.5L14 20l-2.5-5.5L6 12l5.5-2.5L14 4Z",
  verify: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3ZM9 12l2 2 4-4",
  delivery: "M3 7h11v8H3zM14 10h4l3 3v2h-7zM7 17.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM17.5 17.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
  twin: "M3 12h4l2 6 4-12 2 6h6",
  offtarget: "M12 3v3M12 18v3M3 12h3M18 12h3M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
  oracles: "M9 3h6M9 21h6M3 9v6M21 9v6M7 7h10v10H7zM10.5 10.5h3v3h-3z",
  guardian: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3ZM12 8v4M12 15.5h.01",
  experiments: "M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3M7.5 14h9",
  challenge: "M8 4h8v3a4 4 0 1 1-8 0V4ZM6 5H4v1a3 3 0 0 0 3 3M18 5h2v1a3 3 0 0 1-3 3M9 21h6M12 14v7",
  scope: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 8h.01M11 12h1v4h1",
  // utility
  github: "M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12 12 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21",
  external: "M14 4h6v6M20 4l-9 9M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6",
  arrow: "M5 12h14M13 6l6 6-6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  spark: "M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.8 2.8M14.9 14.9l2.8 2.8M17.7 6.3l-2.8 2.8M9.1 14.9l-2.8 2.8",
  shieldx: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3ZM10 10l4 4M14 10l-4 4",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 1 1 8 0v3",
  book: "M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2V5ZM6 19h12",
  layers: "M12 3l9 5-9 5-9-5 9-5ZM3 13l9 5 9-5",
  check: "M5 12l4 4 10-10",
};

export function Icon({ name, size = 18, className = "", strokeWidth = 1.7, style }) {
  const d = P[name];
  if (!d) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className} style={style}
         stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {d.split("M").filter(Boolean).map((seg, i) => <path key={i} d={"M" + seg} />)}
    </svg>
  );
}

export const ICONS = Object.keys(P);
