// The single source of truth for the pages: routing (App.jsx) and the left-rail nav + page headers (Layout.jsx)
// read this. Each item carries an icon (see components/icons.jsx) and a one-line tip used as the page subtitle.
export const NAV = [
  { path: "/", id: "home", label: "Home", group: "Start", icon: "home",
    tip: "What PEN-STACK is, what it can compute, and where to begin." },
  { path: "/chat", id: "coscientist", label: "Co-Scientist", group: "Start", icon: "chat",
    tip: "The conversational front door, a multi-turn chat. Ask anything (a write request, \"is this legal?\", \"what can't you tell me?\"); it routes the engine and narrates a full answer, never a number it invented. For a structured, typed spec instead, use Describe a Write." },
  { path: "/writespec", id: "writespec", label: "Describe a Write", group: "Start", icon: "writespec",
    tip: "The structured intent parser (not a chat): turn ONE plain-language goal into a typed, ontology-backed WriteSpec, write-type, target, cell type, cargo, constraints, each with its provenance, plus a feasibility check. Deterministic, one-shot. For open-ended questions, use the Co-Scientist." },

  { path: "/site-finder", id: "sitefinder", label: "Site Finder", group: "Design", icon: "site",
    tip: "Score loci by safety, durability and reachability for an edit intent." },
  { path: "/atlas", id: "atlas", label: "Writer Atlas", group: "Design", icon: "atlas",
    tip: "Compare writers: capacity, programmability, DSB-freeness, human-cell activity, deliverability, and the writer's own immunogenicity (MHC-II + ADA)." },
  { path: "/design", id: "design-studio", label: "Design Studio", group: "Design", icon: "verify",
    tip: "One design form, three actions: Verify a single design (legality / confidence / biosecurity, each its own axis, with a repairable proof), Generate alternatives (sweep the goal for legal, screened candidates with a calibrated confidence band), or Profile immune & delivery (the per-axis delivery immune profile: genotox / CD8 / innate / NAb / anti-PEG, never collapsed; the writer's own immunogenicity is on the Writer Atlas)." },

  { path: "/twin", id: "twin", label: "Digital Twin", group: "Assess", icon: "twin",
    tip: "Calibrated, OOD-gated outcome prediction bounded by the structure-to-phenotype boundary." },
  { path: "/offtarget", id: "offtarget", label: "Off-Target", group: "Assess", icon: "offtarget",
    tip: "A genome-wide off-target finder: give a guide or target, get the ranked genome-wide off-target sites with a real-data risk band, the learned CRISOT score, and the confirming lab assay. The genome scan runs on the VM; the app replays the cache or abstains. A result is NOT a clearance." },
  { path: "/guardian", id: "guardian", label: "Guardian", group: "Assess", icon: "guardian",
    tip: "The biosecurity / dual-use screen: clear / flag / escalate / refuse, with an audit note." },

  { path: "/oracles", id: "oracles", label: "Oracle Mesh", group: "Build & learn", icon: "oracles",
    tip: "The foundation-model oracle mesh under one contract: per-oracle execution, latency, live status and published reliability, plus a protein-ligand binding-affinity query. Every output is a candidate, never ground truth." },
  { path: "/experiments", id: "experiments", label: "Experiments", group: "Build & learn", icon: "experiments",
    tip: "The next-experiment batch ranked by expected information gain, and the validation campaign that targets the first outcome-validated axis." },
  { path: "/closed-loop", id: "closed-loop", label: "Closed Loop", group: "Build & learn", icon: "loop",
    tip: "The closed-loop design→build→test→learn loop: safety-gated cloud-lab submission (verify-first, DRAFT protocol, mock/dry-run), the SDL-brain benchmark vs BayBE/Atlas, and the provenanced world-model graph. Level 3, human in control." },
  { path: "/challenge", id: "challenge", label: "Challenge", group: "Build & learn", icon: "challenge",
    tip: "The open, held-out Genome-Writing Challenge: public tasks and the reference leaderboard." },

  { path: "/scope", id: "scope", label: "Scope & About", group: "Trust", icon: "scope",
    tip: "The scope contract: the known-unknowns, the capability manifest, decision-support not a clinical directive." },
];

export const GROUPS = ["Start", "Design", "Assess", "Build & learn", "Trust"];
