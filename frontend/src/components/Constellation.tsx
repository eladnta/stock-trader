import { useRef, useState, useEffect } from "react";
import { Position } from "../types";

interface Props {
  positions: Position[];
  selected: string | null;
  onSelect: (ticker: string) => void;
}

function actionColor(action: string) {
  if (action === "BUY") return "var(--em)";
  if (action === "SELL") return "var(--rose)";
  return "var(--txt3)";
}

function orbSize(pnl: number, baseSize = 42) {
  const scale = Math.min(2, Math.max(0.6, 1 + pnl / 50));
  return baseSize * scale;
}

export function Constellation({ positions, selected, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 600, h: 400 });

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Distribute orbs in a loose circle
  const orbPositions = positions.map((p, i) => {
    const angle = (2 * Math.PI * i) / positions.length - Math.PI / 2;
    const radius = Math.min(dims.w, dims.h) * 0.32;
    return {
      ...p,
      cx: dims.w / 2 + radius * Math.cos(angle),
      cy: dims.h / 2 + radius * Math.sin(angle),
    };
  });

  return (
    <div ref={containerRef} style={{ position: "relative", flex: 1, overflow: "hidden" }}>
      {/* Hero number */}
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none" }}>
        <div className="num" style={{ fontSize: "clamp(28px,5vw,52px)", fontWeight: 900, color: "var(--txt)", opacity: 0.07 }}>
          {positions.length}
        </div>
        <div style={{ fontSize: 11, color: "var(--txt3)" }}>פוזיציות</div>
      </div>

      {/* SVG correlation lines */}
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
        {orbPositions.map((a, i) =>
          orbPositions.slice(i + 1).map((b) => (
            <line key={`${a.ticker}-${b.ticker}`}
              x1={a.cx} y1={a.cy} x2={b.cx} y2={b.cy}
              stroke="var(--line)" strokeWidth={1} opacity={0.4} />
          ))
        )}
      </svg>

      {/* Orbs */}
      {orbPositions.map((p) => {
        const size = orbSize(p.pnl_pct);
        const color = actionColor(p.action);
        const isSelected = selected === p.ticker;
        return (
          <button key={p.ticker}
            onClick={() => onSelect(p.ticker)}
            style={{
              position: "absolute",
              left: p.cx - size / 2,
              top: p.cy - size / 2,
              width: size,
              height: size,
              borderRadius: "50%",
              background: `radial-gradient(circle at 35% 35%, ${color}44, ${color}22)`,
              border: `${isSelected ? 2 : 1}px solid ${color}`,
              boxShadow: isSelected ? `0 0 16px ${color}88` : `0 0 6px ${color}44`,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 1,
              transition: "box-shadow 0.2s",
            }}>
            <span className="tick" style={{ fontSize: `clamp(9px,${size * 0.22}px,13px)`, fontWeight: 700, color: "var(--txt)", whiteSpace: "nowrap" }}>{p.ticker}</span>
            <span className="num" style={{ fontSize: `clamp(8px,${size * 0.18}px,11px)`, color: p.pnl_pct >= 0 ? "var(--em)" : "var(--rose)" }}>
              {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct.toFixed(1)}%
            </span>
          </button>
        );
      })}
    </div>
  );
}
