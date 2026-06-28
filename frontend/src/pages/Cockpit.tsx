import { useState } from "react";
import { VitalsPanel } from "../components/VitalsPanel";
import { TopBar } from "../components/TopBar";
import { useSSE } from "../api/sse";
import { fetchAPI } from "../api/client";
import { Portfolio } from "../types";

export function Cockpit() {
  const portfolio = useSSE<Portfolio>("/portfolio/stream");
  const [running, setRunning] = useState(false);

  async function handleRunCycle() {
    setRunning(true);
    try { await fetchAPI("/cycle/run", { method: "POST" }); }
    finally { setTimeout(() => setRunning(false), 3000); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <TopBar onRunCycle={handleRunCycle} running={running} />
      <div style={{
        flex: 1, display: "grid",
        gridTemplateColumns: "248px 1fr 320px",
        overflow: "hidden"
      }}>
        <VitalsPanel portfolio={portfolio} />
        {/* Constellation — Task 8 */}
        <main style={{ background: "var(--ink)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ color: "var(--txt3)", fontSize: 13 }}>קונסטלציה — בקרוב</span>
        </main>
        {/* Inspector — Task 9 */}
        <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: 16 }}>
          <span style={{ color: "var(--txt3)", fontSize: 13 }}>בחר נכס</span>
        </aside>
      </div>
    </div>
  );
}
