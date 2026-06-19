"use client";

interface RiskBadgeProps {
  level: string | null;
  factors?: string[];
}

const RISK_CONFIG: Record<string, { color: string; bg: string; label: string; dot: string }> = {
  low:    { color: "#4ade80", bg: "rgba(74,222,128,0.12)",  label: "Low",    dot: "#22c55e" },
  medium: { color: "#fbbf24", bg: "rgba(251,191,36,0.12)",  label: "Medium", dot: "#f59e0b" },
  high:   { color: "#f87171", bg: "rgba(248,113,113,0.12)", label: "High",   dot: "#ef4444" },
};

export default function RiskBadge({ level, factors = [] }: RiskBadgeProps) {
  if (!level) return null;
  const cfg = RISK_CONFIG[level] ?? RISK_CONFIG.low;

  return (
    <div
      className="risk-badge-container"
      style={{ position: "relative", display: "inline-block" }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "5px",
          background: cfg.bg,
          border: `1px solid ${cfg.color}40`,
          borderRadius: "20px",
          padding: "3px 8px 3px 5px",
          cursor: "default",
        }}
        aria-label={`Risk level: ${cfg.label}. Factors: ${factors.join("; ")}`}
        role="status"
      >
        {/* Coloured dot */}
        <span
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: cfg.dot,
            display: "inline-block",
            flexShrink: 0,
          }}
        />
        <span style={{ color: cfg.color, fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.04em" }}>
          {cfg.label.toUpperCase()} RISK
        </span>
      </div>

      {/* Hover tooltip */}
      {factors.length > 0 && (
        <div
          className="risk-tooltip"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            right: 0,
            background: "#18181b",
            border: "1px solid rgba(63,63,70,0.8)",
            borderRadius: "8px",
            padding: "8px 10px",
            minWidth: "180px",
            maxWidth: "240px",
            zIndex: 50,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            pointerEvents: "none",
            opacity: 0,
            transform: "translateY(-4px)",
            transition: "opacity 0.15s ease, transform 0.15s ease",
          }}
        >
          <div style={{ fontSize: "0.65rem", color: "#71717a", marginBottom: "5px", fontWeight: 700, letterSpacing: "0.05em" }}>
            CONTRIBUTING FACTORS
          </div>
          {factors.map((f, i) => (
            <div key={i} style={{ fontSize: "0.72rem", color: "#d4d4d8", marginBottom: "3px", display: "flex", alignItems: "flex-start", gap: "5px" }}>
              <span style={{ color: cfg.color, flexShrink: 0 }}>•</span>
              {f}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .risk-badge-container:hover .risk-tooltip {
          opacity: 1 !important;
          transform: translateY(0) !important;
        }
      `}</style>
    </div>
  );
}
