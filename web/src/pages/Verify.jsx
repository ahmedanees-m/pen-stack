// Verify, submit a design, get a Verdict: legality + safety + calibrated confidence + immune profile, each as a
// separate axis (never collapsed). A refused design short-circuits to the safety verdict.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import VerdictCard from "../components/VerdictCard.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScopeLedger from "../components/ScopeLedger.jsx";

export default function Verify() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try { setRes(await api.verify(design)); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const refused = res?.safety?.decision === "refuse";
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Design" subtitle="Build a proposed genomic write; the verifier evaluates each axis independently.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={run} disabled={busy}>Verify design</Button></div>
      </Card>

      <Card title="Verdict" subtitle="Legality and confidence are distinct, a legal design can still be low-confidence.">
        {busy ? <Spinner /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Submit a design to see the verdict.</p>
        ) : (
          <div className="space-y-4">
            {res.safety?.decision && <SafetyBadge decision={res.safety.decision} reason={res.safety.reason} />}
            {refused ? (
              <p className="text-sm text-fg-dim">This design was <strong className="text-bad">refused</strong> by the
                Guardian and is not evaluated further, that is the honest stop, not a low score.</p>
            ) : (
              <>
                <VerdictCard verdict={res} />
                {res.immune_profile?.axes && <ImmuneProfileCard profile={res.immune_profile} />}
                <ScopeLedger knownUnknowns={res.immune_profile?.known_unknowns}
                             outOfScope={res.scope_flags?.length ? { title: "scope flags raised", why: "see flags above" } : null} dense />
              </>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
