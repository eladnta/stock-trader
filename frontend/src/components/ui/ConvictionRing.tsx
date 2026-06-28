interface ConvictionRingProps { accuracy: number; }  // 0-100

export function ConvictionRing({ accuracy }: ConvictionRingProps) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const filled = circ * (accuracy / 100);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <svg width={88} height={88} viewBox="0 0 88 88">
        <circle cx={44} cy={44} r={r} fill="none" stroke="var(--line)" strokeWidth={6} />
        <circle cx={44} cy={44} r={r} fill="none" stroke="var(--cyan)" strokeWidth={6}
          strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 44 44)" />
        <text x={44} y={48} textAnchor="middle" fill="var(--txt)" fontSize={18} fontWeight={700} fontFamily="monospace">{accuracy}%</text>
      </svg>
      <span style={{ fontSize: 11, color: "var(--txt3)" }}>דיוק תחזיות</span>
    </div>
  );
}
