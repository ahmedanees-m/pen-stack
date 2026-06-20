import React, { useState } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import CoScientist from "./pages/CoScientist.jsx";
import SiteFinder from "./pages/SiteFinder.jsx";
import WriterAtlas from "./pages/WriterAtlas.jsx";
import Verify from "./pages/Verify.jsx";
import Delivery from "./pages/Delivery.jsx";
import Twin from "./pages/Twin.jsx";
import OffTarget from "./pages/OffTarget.jsx";
import Experiments from "./pages/Experiments.jsx";
import Designer from "./pages/Designer.jsx";
import Guardian from "./pages/Guardian.jsx";
import Challenge from "./pages/Challenge.jsx";
import Scope from "./pages/Scope.jsx";

export default function App() {
  const [backend, setBackend] = useState(null); // last chat backend (ollama / nemotron / deterministic)
  const [allowLlm, setAllowLlm] = useState(true); // global LLM-narration toggle (off = deterministic everywhere)

  return (
    <Layout backend={backend} allowLlm={allowLlm} setAllowLlm={setAllowLlm}>
      <Routes>
        <Route path="/" element={<CoScientist onBackend={setBackend} allowLlm={allowLlm} />} />
        <Route path="/site-finder" element={<SiteFinder />} />
        <Route path="/atlas" element={<WriterAtlas />} />
        <Route path="/verify" element={<Verify />} />
        <Route path="/delivery" element={<Delivery />} />
        <Route path="/twin" element={<Twin />} />
        <Route path="/offtarget" element={<OffTarget />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/designer" element={<Designer />} />
        <Route path="/guardian" element={<Guardian />} />
        <Route path="/challenge" element={<Challenge />} />
        <Route path="/scope" element={<Scope />} />
      </Routes>
    </Layout>
  );
}
