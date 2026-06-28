import { useAnalysis } from "../hooks/useAnalysis";
import { SignalBar } from "./ui/SignalBar";

interface Props { selected: string | null; }

function actionBadgeColor(action: string) {
  if (action?.includes("BUY")) return { bg: "rgba(52,216,160,0.15)", color: "var(--em)" };
  if (action?.includes("SELL")) return { bg: "rgba(244,121,139,0.15)", color: "var(--rose)" };
  return { bg: "rgba(176,124,255,0.15)", color: "var(--vio)" };
}

export function Inspector({ selected }: Props) {
  const { analysis, loading } = useAnalysis(selected);

  if (!selected) return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px", direction: "rtl" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>לחץ על נכס בקונסטלציה</span>
    </aside>
  );

  if (loading) return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>טוען…</span>
    </aside>
  );

  const badge = actionBadgeColor(analysis?.action ?? "");
  const signals = analysis?.signals ?? [];

  return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px", direction: "rtl", overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <span className="tick" style={{ fontSize: 22, fontWeight: 800, color: "var(--txt)" }}>{selected}</span>
        <span style={{ fontSize: 11, padding: "3px 9px", borderRadius: 6, fontWeight: 700, background: badge.bg, color: badge.color, whiteSpace: "nowrap" }}>
          {analysis?.action ?? "—"}
        </span>
      </div>

      {/* Data rows */}
      {[
        { label: "ציון הזדמנות", value: analysis?.opportunity_score?.toFixed(1) ?? "—" },
        { label: "סקטור", value: analysis?.sector ?? analysis?.asset_class ?? "—" },
        { label: "מחיר", value: analysis?.price ? `$${analysis.price.toFixed(2)}` : "—" },
        { label: "יעד", value: analysis?.price_target ? `$${analysis.price_target.toFixed(0)}` : "—" },
      ].map(({ label, value }) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--line)" }}>
          <span className="label" style={{ fontSize: 12, color: "var(--txt2)" }}>{label}</span>
          <span className="num" style={{ fontSize: 12, fontWeight: 600, color: "var(--txt)" }}>{value}</span>
        </div>
      ))}

      {/* Signals */}
      {signals.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: "var(--txt3)", textTransform: "uppercase" }}>סיגנלים</span>
          <div style={{ marginTop: 10 }}>
            {signals.slice(0, 5).map((s) => (
              <SignalBar key={s.name} name={s.label ?? s.name} score={s.score} weight={s.weight} />
            ))}
          </div>
        </div>
      )}

      {/* Thesis */}
      {analysis?.thesis && (
        <div style={{ marginTop: 16, padding: "10px 12px", background: "rgba(92,224,255,0.05)", borderRadius: 8, borderRight: "2px solid var(--cyan)" }}>
          <p style={{ fontSize: 12, color: "var(--txt2)", lineHeight: 1.6 }}>{analysis.thesis}</p>
        </div>
      )}
    </aside>
  );
}
