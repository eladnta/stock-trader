interface MetricRowProps {
  label: string;
  value: string;
  valueColor?: string;
}

export function MetricRow({ label, value, valueColor }: MetricRowProps) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
      <span className="label" style={{ fontSize: "clamp(11px,1.2vw,13px)", color: "var(--txt2)" }}>{label}</span>
      <span className="num" style={{ fontSize: "clamp(12px,1.3vw,14px)", fontWeight: 700, color: valueColor ?? "var(--txt)" }}>{value}</span>
    </div>
  );
}
