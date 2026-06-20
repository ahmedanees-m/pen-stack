// The single source of truth for the pages: routing (App.jsx) and the left-rail nav (Layout.jsx) both read this.
export const NAV = [
  { path: "/", id: "coscientist", label: "Co-Scientist", group: "Ask",
    tip: "Ask a genome-writing question in plain language; the grounded co-scientist routes the engine and narrates, never a number it invented." },
  { path: "/site-finder", id: "sitefinder", label: "Site Finder", group: "Design",
    tip: "Score loci by safety × durability × reachability for an edit intent." },
  { path: "/atlas", id: "atlas", label: "Writer Atlas", group: "Design",
    tip: "Compare writers: capacity, programmability, DSB-freeness, human-cell activity, deliverability." },
  { path: "/designer", id: "designer", label: "Designer", group: "Design",
    tip: "Generative strategies on the safety/efficacy Pareto frontier, candidates, never asserted to work." },
  { path: "/verify", id: "verify", label: "Verify", group: "Assess",
    tip: "Submit a design → legality + safety + calibrated confidence + immune profile, each its own axis." },
  { path: "/delivery", id: "delivery", label: "Delivery & Immunity", group: "Assess",
    tip: "The per-axis immune-risk profile (genotox / CD8 / innate / NAb / anti-PEG) + route modifier + known-unknowns." },
  { path: "/twin", id: "twin", label: "Digital Twin", group: "Assess",
    tip: "Calibrated, OOD-gated outcome prediction bounded by the structure→phenotype boundary." },
  { path: "/offtarget", id: "offtarget", label: "Off-Target", group: "Assess",
    tip: "Cross-family off-target nomination: rank candidate sites with a real-data calibrated risk band + the assay that would confirm them. Nomination is NOT a clearance." },
  { path: "/guardian", id: "guardian", label: "Guardian", group: "Assess",
    tip: "The biosecurity / dual-use screen: clear / flag / escalate / refuse, with an audit note." },
  { path: "/experiments", id: "experiments", label: "Experiments", group: "Learn",
    tip: "The next-experiment batch, ranked by expected information gain." },
  { path: "/challenge", id: "challenge", label: "Challenge", group: "Learn",
    tip: "The open, held-out Genome-Writing Challenge: public tasks + the reference leaderboard." },
  { path: "/scope", id: "scope", label: "Scope & About", group: "Trust",
    tip: "The honesty contract: the known-unknowns, the capability manifest, decision-support not a clinical directive." },
];

export const GROUPS = ["Ask", "Design", "Assess", "Learn", "Trust"];
