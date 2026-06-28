import { useState } from "react";
import { VitalsPanel } from "../components/VitalsPanel";
import { TopBar } from "../components/TopBar";
import { Constellation } from "../components/Constellation";
import { useSSE } from "../api/sse";
import { fetchAPI } from "../api/client";
import { Portfolio, Position } from "../types";

export function Cockpit() {
  const portfolio = useSSE<Portfolio>("/portfolio/stream");
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const positions: Position[] = portfolio ? Object.entries(portfolio.positions).map(([ticker, pos]) => ({
    ticker,
    shares: (pos as any).shares ?? 0,
    avg_cost: (pos as any).avg_cost ?? 0,
    current_price: (pos as any).current_price ?? (pos as any).avg_cost ?? 0,
    pnl_pct: (pos as any).pnl_pct ?? 0,
    action: (pos as any).action ?? "HOLD",
  })) : [];

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
        <main style={{ background: "var(--ink)", overflow: "hidden", display: "flex" }}>
          <Constellation positions={positions} selected={selected} onSelect={setSelected} />
        </main>
        {/* Inspector — Task 9 */}
        <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: 16 }}>
          <span style={{ color: "var(--txt3)", fontSize: 13 }}>בחר נכס</span>
        </aside>
      </div>
    </div>
  );
}
