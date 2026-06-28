import type { Position } from "../types";

interface Props {
  positions: Position[];
  onSelect: (ticker: string) => void;
}

function actionColor(action: string) {
  if (action === "BUY") return "var(--em)";
  if (action === "SELL") return "var(--rose)";
  return "var(--txt3)";
}

export function PositionStrip({ positions, onSelect }: Props) {
  return (
    <div style={{
      height: 90,
      borderTop: "1px solid var(--line)",
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "0 16px",
      overflowX: "auto",
      overflowY: "hidden",
      direction: "rtl",
    }}>
      {positions.map((p) => {
        const color = actionColor(p.action);
        const convictionPct = Math.min(100, Math.max(0, 50 + p.pnl_pct));
        return (
          <button
            key={p.ticker}
            onClick={() => onSelect(p.ticker)}
            style={{
              minWidth: 120,
              maxWidth: 140,
              height: 68,
              padding: "8px 12px",
              background: "var(--surf)",
              border: "1px solid var(--line)",
              borderRadius: 10,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span
                className="tick"
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: "var(--txt)",
                  whiteSpace: "nowrap",
                }}
              >
                {p.ticker}
              </span>
              <span style={{ fontSize: 10, color, fontWeight: 600, whiteSpace: "nowrap" }}>
                {p.action}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span
                className="num"
                style={{
                  fontSize: 12,
                  color: p.pnl_pct >= 0 ? "var(--em)" : "var(--rose)",
                  fontWeight: 700,
                }}
              >
                {p.pnl_pct >= 0 ? "+" : ""}
                {p.pnl_pct.toFixed(1)}%
              </span>
            </div>
            {/* Conviction bar */}
            <div style={{ height: 3, background: "var(--line)", borderRadius: 2 }}>
              <div
                style={{
                  height: "100%",
                  width: `${convictionPct}%`,
                  background: color,
                  borderRadius: 2,
                }}
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}
