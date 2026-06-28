interface Props { onRunCycle: () => void; running: boolean; }

export function TopBar({ onRunCycle, running }: Props) {
  return (
    <header style={{
      height: 48, display: "flex", alignItems: "center", gap: 16,
      padding: "0 20px", borderBottom: "1px solid var(--line)",
      background: "var(--surf)", direction: "rtl"
    }}>
      <span style={{ fontSize: 18, fontWeight: 800, color: "var(--cyan)", letterSpacing: "-0.5px", whiteSpace: "nowrap" }}>◈ Trader</span>
      <nav style={{ display: "flex", gap: 4, flex: 1 }}>
        {["קוקפיט", "יקום", "סיגנלים", "ביצועים"].map((t, i) => (
          <button key={t} style={{
            padding: "4px 12px", borderRadius: 6, border: "none", cursor: "pointer",
            background: i === 0 ? "rgba(92,224,255,0.12)" : "transparent",
            color: i === 0 ? "var(--cyan)" : "var(--txt3)",
            fontSize: 13, fontWeight: i === 0 ? 700 : 400
          }}>{t}</button>
        ))}
      </nav>
      <div style={{ display: "flex", alignItems: "center", gap: 8, direction: "ltr" }}>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--em)", boxShadow: "0 0 6px var(--em)", display: "inline-block" }} />
        <span style={{ fontSize: 11, color: "var(--txt3)", whiteSpace: "nowrap" }}>חי</span>
        <button onClick={onRunCycle} disabled={running} style={{
          padding: "5px 14px", borderRadius: 7, border: "1px solid var(--line)",
          background: running ? "var(--line)" : "var(--cyan)", color: running ? "var(--txt3)" : "var(--ink)",
          fontWeight: 700, fontSize: 12, cursor: running ? "not-allowed" : "pointer", whiteSpace: "nowrap"
        }}>{running ? "רץ…" : "הרץ מחזור"}</button>
      </div>
    </header>
  );
}
