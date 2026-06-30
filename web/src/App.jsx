import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import CoScientist from "./pages/CoScientist.jsx";
import SiteFinder from "./pages/SiteFinder.jsx";
import WriterAtlas from "./pages/WriterAtlas.jsx";
import DesignStudio from "./pages/DesignStudio.jsx";
import Twin from "./pages/Twin.jsx";
import OffTarget from "./pages/OffTarget.jsx";
import Oracles from "./pages/Oracles.jsx";
import WriteSpec from "./pages/WriteSpec.jsx";
import Experiments from "./pages/Experiments.jsx";
import Guardian from "./pages/Guardian.jsx";
import Challenge from "./pages/Challenge.jsx";
import Scope from "./pages/Scope.jsx";

export default function App() {
  const [backend, setBackend] = useState(null); // last chat backend (ollama / nemotron / deterministic)
  const [allowLlm, setAllowLlm] = useState(true); // global LLM-narration toggle (off = deterministic everywhere)

  return (
    <Layout backend={backend} allowLlm={allowLlm} setAllowLlm={setAllowLlm}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/chat" element={<CoScientist onBackend={setBackend} allowLlm={allowLlm} />} />
        <Route path="/writespec" element={<WriteSpec />} />
        <Route path="/site-finder" element={<SiteFinder />} />
        <Route path="/atlas" element={<WriterAtlas />} />
        <Route path="/design" element={<DesignStudio />} />
        {/* the former Verify + Designer (v7.1.4) and Delivery & Immunity (v7.1.6) pages were merged into Design
            Studio; keep old links working */}
        <Route path="/verify" element={<Navigate to="/design" replace />} />
        <Route path="/designer" element={<Navigate to="/design" replace />} />
        <Route path="/delivery" element={<Navigate to="/design" replace />} />
        <Route path="/twin" element={<Twin />} />
        <Route path="/offtarget" element={<OffTarget />} />
        <Route path="/oracles" element={<Oracles />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/guardian" element={<Guardian />} />
        <Route path="/challenge" element={<Challenge />} />
        <Route path="/scope" element={<Scope />} />
      </Routes>
    </Layout>
  );
}
