interface Props { name: string; score: number; weight: number; }  // score: -1..+1

export function SignalBar({ name, score, weight }: Props) {
  const positive = score >= 0;
  const pct = Math.abs(score) * 100;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span className="label" style={{ fontSize: 11, color: "var(--txt2)" }}>{name}</span>
        <span className="num" style={{ fontSize: 11, color: positive ? "var(--em)" : "var(--rose)", fontWeight: 700 }}>
          {positive ? "+" : ""}{(score * weight).toFixed(2)}
        </span>
      </div>
      <div style={{ height: 4, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: positive ? "var(--em)" : "var(--rose)",
          borderRadius: 2, transition: "width 0.4s"
        }} />
      </div>
    </div>
  );
}
