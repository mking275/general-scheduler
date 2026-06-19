"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, Shield, Heart, Bone, Eye } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface BreedAlert {
  protocol_id: string;
  flag_type: string;
  title: string;
  detail: string;
  severity: "critical" | "warning" | "info";
  age_threshold_years: number;
  patient_age_years: number;
  age_gate_met: boolean;
  active: boolean;
}

interface BreedAlertsPanelProps {
  patientId: string;
  patientName?: string;
  breed?: string;
}

const FLAG_ICONS: Record<string, any> = {
  brachycephalic: Shield,
  oncology:       AlertTriangle,
  cardiac:        Heart,
  ortho:          Bone,
  renal:          Eye,
};

const SEVERITY_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  critical: { bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.3)", text: "#ef4444", dot: "#ef4444" },
  warning:  { bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.3)", text: "#f59e0b", dot: "#f59e0b" },
  info:     { bg: "rgba(59,130,246,0.08)", border: "rgba(59,130,246,0.3)", text: "#3b82f6", dot: "#3b82f6" },
};

export default function BreedAlertsPanel({ patientId, patientName, breed }: BreedAlertsPanelProps) {
  const [alerts, setAlerts] = useState<BreedAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    setLoading(true);
    fetch(`${API}/api/breed-intelligence/${patientId}`)
      .then(r => r.json())
      .then(data => {
        setAlerts(data.alerts || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [patientId]);

  const activeAlerts  = alerts.filter(a => a.active);
  const pendingAlerts = alerts.filter(a => !a.active);

  if (loading) {
    return (
      <div style={{ padding: "12px 16px", color: "#71717a", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "8px" }}>
        <div style={{ width: "12px", height: "12px", borderRadius: "50%", border: "2px solid #6C63FF", borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />
        Analysing breed protocols…
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div style={{ padding: "12px 16px", color: "#52525b", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "8px" }}>
        <Shield size={14} />
        No breed-specific alerts for {breed || "this patient"}.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      {activeAlerts.length > 0 && (
        <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.05em", paddingLeft: "4px", marginBottom: "2px" }}>
          ⚠ Active Breed Alerts ({activeAlerts.length})
        </div>
      )}

      {activeAlerts.map(alert => {
        const colors  = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info;
        const Icon    = FLAG_ICONS[alert.flag_type] || AlertTriangle;
        const isOpen  = expanded === alert.protocol_id;

        return (
          <div
            key={alert.protocol_id}
            onClick={() => setExpanded(isOpen ? null : alert.protocol_id)}
            style={{
              background: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: "8px",
              padding: "8px 10px",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Icon size={14} color={colors.text} />
              <span style={{ flex: 1, fontSize: "0.78rem", fontWeight: 600, color: colors.text }}>
                {alert.title}
              </span>
              <span style={{
                fontSize: "0.62rem", fontWeight: 700, textTransform: "uppercase",
                color: colors.text, letterSpacing: "0.04em", opacity: 0.8,
              }}>
                {alert.severity}
              </span>
              <span style={{ color: "#52525b", fontSize: "0.7rem", transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>▾</span>
            </div>

            {isOpen && (
              <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: `1px solid ${colors.border}`, fontSize: "0.75rem", color: "#a1a1aa", lineHeight: 1.5 }}>
                {alert.detail}
                <div style={{ marginTop: "6px", fontSize: "0.68rem", color: "#71717a" }}>
                  Age gate: {alert.age_threshold_years}y threshold • Patient age: {alert.patient_age_years.toFixed(1)}y
                </div>
              </div>
            )}
          </div>
        );
      })}

      {pendingAlerts.length > 0 && (
        <>
          <div style={{ fontSize: "0.68rem", fontWeight: 600, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.05em", paddingLeft: "4px", marginTop: "4px" }}>
            Age-gated (not yet applicable)
          </div>
          {pendingAlerts.map(alert => {
            const Icon = FLAG_ICONS[alert.flag_type] || AlertTriangle;
            return (
              <div key={alert.protocol_id} style={{
                background: "rgba(39,39,42,0.4)", border: "1px solid rgba(63,63,70,0.3)",
                borderRadius: "8px", padding: "6px 10px", opacity: 0.6,
                display: "flex", alignItems: "center", gap: "8px",
              }}>
                <Icon size={12} color="#52525b" />
                <span style={{ fontSize: "0.73rem", color: "#71717a" }}>{alert.title}</span>
                <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "#52525b" }}>
                  at {alert.age_threshold_years}y
                </span>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
