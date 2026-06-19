"use client";

import { useState, useEffect } from "react";
import PatientPanel from "./PatientPanel";
import RiskBadge from "./RiskBadge";
import IntakePanel from "./IntakePanel";
import FollowUpPanel from "./FollowUpPanel";
import { User, Clock, FileText, ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface AppointmentCardProps {
  item: any;
  patient?: any;
  role: "front_desk" | "vet_tech" | "vet";
  onLogEntry?: (entry: string) => void;
  currentClinicId?: string;
}

export default function AppointmentCard({ item, patient, role, onLogEntry, currentClinicId }: AppointmentCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [riskScore, setRiskScore] = useState<any>(null);
  const [intakeStatus, setIntakeStatus] = useState(item.intake_status ?? "not_started");
  const [followupStatus, setFollowupStatus] = useState(item.followup_status ?? "not_started");
  const [completedAt, setCompletedAt] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(item.status === "complete");

  const tbId = item.timeblock_id ?? item.id;

  // Fetch risk score
  useEffect(() => {
    if (!tbId) return;
    fetch(`${API}/api/risk/${tbId}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d) setRiskScore(d); })
      .catch(() => {});
  }, [tbId]);

  const handleComplete = async (force = false) => {
    const res = await fetch(`${API}/api/appointments/${tbId}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    });
    if (res.status === 409) {
      const d = await res.json();
      if (d.detail?.warning) {
        const ok = confirm("SOAP note is unsigned — complete anyway?");
        if (ok) handleComplete(true);
      }
      return;
    }
    if (res.ok) {
      setIsComplete(true);
      setCompletedAt(new Date().toISOString());
      setFollowupStatus("draft");
      onLogEntry?.("DISPATCH: Appointment marked complete");
    }
  };

  // Accent color by risk
  const accentColor =
    riskScore?.risk_level === "high"   ? "#ef4444" :
    riskScore?.risk_level === "medium" ? "#f59e0b" :
    "#10b981";

  return (
    <div
      style={{
        background: "linear-gradient(160deg, #18181b 0%, #09090b 100%)",
        border: "1px solid rgba(63,63,70,0.7)",
        borderRadius: "16px",
        overflow: "hidden",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
        transition: "box-shadow 0.2s ease",
        position: "relative",
      }}
    >
      {/* Top accent bar */}
      <div style={{ height: "3px", background: isComplete ? "#10b981" : accentColor, width: "100%" }} />

      {/* Card header */}
      <div
        style={{ padding: "14px 16px 10px", cursor: "pointer" }}
        onClick={() => setExpanded((p) => !p)}
      >
        {/* Top row: skills + risk badge */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <span style={{
            background: "rgba(59,130,246,0.12)",
            color: "#60a5fa",
            fontSize: "0.68rem",
            padding: "2px 8px",
            borderRadius: "4px",
            fontWeight: 700,
            letterSpacing: "0.06em",
            border: "1px solid rgba(59,130,246,0.2)",
          }}>
            {(item.job?.required_skills ?? []).join(", ")}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            {isComplete && (
              <span style={{ background: "rgba(16,185,129,0.12)", color: "#10b981", fontSize: "0.65rem", padding: "2px 7px", borderRadius: "12px", fontWeight: 700, border: "1px solid rgba(16,185,129,0.25)" }}>
                ✓ DONE
              </span>
            )}
            <RiskBadge
              level={riskScore?.risk_level ?? item.risk_level ?? null}
              factors={riskScore?.factors ?? []}
            />
            {expanded ? <ChevronUp size={14} color="#71717a" /> : <ChevronDown size={14} color="#71717a" />}
          </div>
        </div>

        {/* Patient panel (always visible in collapsed state) */}
        {patient ? (
          <PatientPanel patient={patient} expanded={false} currentClinicId={currentClinicId} />
        ) : (
          item.job?.patient_name && (
            <div style={{ color: "#d4d4d8", fontSize: "0.85rem", fontWeight: 600 }}>
              {item.job.patient_name}
            </div>
          )
        )}

        {/* Procedure + time */}
        <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {item.job?.procedure && (
            <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "#a1a1aa", fontSize: "0.78rem" }}>
              <FileText size={12} />
              {item.job.procedure}
            </span>
          )}
          <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "#71717a", fontSize: "0.75rem" }}>
            <Clock size={11} />
            {new Date(item.start_time).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}
            {" · "}
            {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            {" – "}
            {new Date(item.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>

      {/* Expanded section */}
      <div
        style={{
          maxHeight: expanded ? "600px" : "0px",
          overflow: "hidden",
          transition: "max-height 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <div style={{ padding: "0 16px 14px", borderTop: "1px solid rgba(63,63,70,0.4)" }}>
          {/* Full patient panel */}
          {patient && (
            <div style={{ paddingTop: "12px", marginBottom: "12px" }}>
              <PatientPanel patient={patient} expanded={true} currentClinicId={currentClinicId} />
            </div>
          )}

          {/* Resources */}
          <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginBottom: "12px" }}>
            {(item.resources ?? []).map((res: any, idx: number) => (
              <div key={idx} style={{
                display: "flex", alignItems: "center", gap: "7px",
                background: "rgba(39,39,42,0.6)", padding: "6px 10px",
                borderRadius: "8px", border: "1px solid rgba(63,63,70,0.4)",
                fontSize: "0.78rem", color: "#a1a1aa",
                position: "relative",
              }}>
                <User size={12} color="#52525b" />
                <span>{res.name}</span>
                {/* T013: Visiting vet indicator */}
                {res.type === "Vet" && res.visiting && (
                  <span
                    title={`Visiting from primary clinic`}
                    style={{
                      fontSize: "0.7rem",
                      cursor: "help",
                      marginLeft: "2px",
                      opacity: 0.85,
                    }}
                  >
                    📍
                  </span>
                )}
                <span style={{ marginLeft: "auto", fontSize: "0.65rem", background: "rgba(63,63,70,0.5)", padding: "1px 5px", borderRadius: "4px", color: "#71717a" }}>
                  {res.type}
                </span>
              </div>
            ))}
          </div>

          {/* Intake panel — Front Desk + Vet */}
          {(role === "front_desk" || role === "vet") && tbId && (
            <IntakePanel
              timeblockId={tbId}
              patientId={item.patient?.id ?? item.patient_id}
              role={role}
              intakeStatus={intakeStatus}
              onStatusChange={setIntakeStatus}
              onLogEntry={onLogEntry}
            />
          )}

          {/* Complete button + Follow-up panel — Front Desk + Vet */}
          {(role === "front_desk" || role === "vet") && !isComplete && (
            <button
              onClick={() => handleComplete(false)}
              style={{
                marginTop: "10px",
                width: "100%",
                padding: "8px",
                background: "rgba(16,185,129,0.1)",
                color: "#10b981",
                border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: "8px",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "background 0.15s ease",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(16,185,129,0.18)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(16,185,129,0.1)")}
            >
              ✓ Mark Complete
            </button>
          )}

          {(isComplete || followupStatus !== "not_started") && tbId && (
            <FollowUpPanel
              timeblockId={tbId}
              followupStatus={followupStatus}
              onStatusChange={setFollowupStatus}
              onLogEntry={onLogEntry}
            />
          )}
        </div>
      </div>
    </div>
  );
}
