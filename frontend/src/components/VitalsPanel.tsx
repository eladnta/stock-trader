import type { Portfolio } from "../types";
import { MetricRow } from "./ui/MetricRow";
import { ConvictionRing } from "./ui/ConvictionRing";

interface Props { portfolio: Portfolio | null; }

function fmt(n: number | null | undefined, suffix = "", prefix = "") {
  if (n == null) return "—";
  const abs = Math.abs(n).toFixed(2);
  const sign = n >= 0 ? "▲" : "▼";
  return `${sign} ${prefix}${abs}${suffix}`;
}

export function VitalsPanel({ portfolio }: Props) {
  if (!portfolio) return (
    <aside style={{ width: 248, padding: "20px 16px", borderLeft: "1px solid var(--line)" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>טוען…</span>
    </aside>
  );
  const accuracy = Math.round((portfolio.conviction_accuracy?.overall ?? 0) * 100);
  return (
    <aside style={{ width: 248, padding: "20px 16px", borderLeft: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "1px", color: "var(--txt3)", textTransform: "uppercase", marginBottom: 8 }}>ויטאלים</span>
      <MetricRow label="שווי פורטפוליו" value={`$${portfolio.portfolio_value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`} />
      <MetricRow label="תשואה כוללת" value={fmt(portfolio.total_return_pct, "%")} valueColor={portfolio.total_return_pct >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="α מול SPY" value={fmt(portfolio.vs_spy_alpha, "%")} valueColor={(portfolio.vs_spy_alpha ?? 0) >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="α מול QQQ" value={fmt(portfolio.vs_qqq_alpha, "%")} valueColor={(portfolio.vs_qqq_alpha ?? 0) >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="Sharpe" value={portfolio.sharpe_ratio != null ? portfolio.sharpe_ratio.toFixed(2) : "—"} />
      <MetricRow label="Max Drawdown" value={fmt(portfolio.max_drawdown_pct, "%")} valueColor="var(--rose)" />
      <MetricRow label="מזומן" value={`${portfolio.cash_pct.toFixed(1)}%`} />
      <MetricRow label="פוזיציות" value={String(Object.keys(portfolio.positions).length)} />
      <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
        <ConvictionRing accuracy={accuracy} />
      </div>
    </aside>
  );
}
