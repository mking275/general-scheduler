"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface IntakePanelProps {
  timeblockId: string;
  role: "front_desk" | "vet_tech" | "vet";
  intakeStatus: string;
  onStatusChange: (status: string) => void;
  onLogEntry?: (entry: string) => void;
}

const STATUS_LABELS: Record<string, { label: string; color: string; emoji: string }> = {
  not_started: { label: "Intake not sent",  color: "#71717a", emoji: "○" },
  pending:     { label: "⏳ Pending",        color: "#fbbf24", emoji: "⏳" },
  received:    { label: "✓ Brief received", color: "#4ade80", emoji: "✓"  },
};

export default function IntakePanel({
  timeblockId, role, intakeStatus, onStatusChange, onLogEntry,
}: IntakePanelProps) {
  const [ownerResponse, setOwnerResponse] = useState("");
  const [brief, setBrief] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const statusCfg = STATUS_LABELS[intakeStatus] ?? STATUS_LABELS.not_started;

  const sendIntake = async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/intake/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: timeblockId }),
    });
    if (res.ok) {
      onStatusChange("pending");
      onLogEntry?.("INTAKE AGENT: Questionnaire sent to owner (simulated)");
    }
    setLoading(false);
  };

  const submitResponse = async () => {
    if (!ownerResponse.trim()) return;
    setLoading(true);
    const res = await fetch(`${API}/api/intake/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: timeblockId, owner_response: ownerResponse }),
    });
    if (res.ok) {
      const data = await res.json();
      setBrief(data);
      onStatusChange("received");
      onLogEntry?.(`INTAKE AGENT: Parsed → ${data.symptoms?.map((s: any) => `${s.name} (${s.duration_days}d, ${s.severity})`).join(", ")}`);
      onLogEntry?.(`INTAKE AGENT: Suggested focus: ${data.suggested_focus?.join(", ")}`);
      onLogEntry?.("INTAKE AGENT: Pre-Exam Brief saved");
    }
    setLoading(false);
  };

  // Vet role: only show summary if received
  if (role === "vet" && intakeStatus !== "received") return null;

  return (
    <div style={{
      marginTop: "10px",
      background: "rgba(23,23,23,0.7)",
      border: "1px solid rgba(63,63,70,0.5)",
      borderRadius: "10px",
      padding: "10px 12px",
    }}>
      {/* Status header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#71717a", letterSpacing: "0.06em" }}>PRE-VISIT INTAKE</span>
        <span style={{ fontSize: "0.7rem", color: statusCfg.color, fontWeight: 600 }}>
          {statusCfg.label}
        </span>
      </div>

      {/* Not started: show Send button */}
      {intakeStatus === "not_started" && role === "front_desk" && (
        <button
          onClick={sendIntake}
          disabled={loading}
          style={{
            width: "100%", padding: "7px", borderRadius: "7px",
            background: "rgba(59,130,246,0.1)", color: "#60a5fa",
            border: "1px solid rgba(59,130,246,0.25)", fontSize: "0.75rem",
            fontWeight: 600, cursor: "pointer", transition: "background 0.15s ease",
          }}
        >
          {loading ? "Sending..." : "📋 Send Intake Questionnaire"}
        </button>
      )}

      {/* Pending: show mock response textarea */}
      {intakeStatus === "pending" && role === "front_desk" && (
        <div>
          <div style={{ fontSize: "0.72rem", color: "#a1a1aa", marginBottom: "6px" }}>
            Simulate owner response:
          </div>
          <textarea
            value={ownerResponse}
            onChange={e => setOwnerResponse(e.target.value)}
            placeholder="e.g. He's been lethargic for 3 days and not eating..."
            rows={3}
            style={{
              width: "100%", background: "#0c0c0e", color: "#d4d4d8",
              border: "1px solid rgba(63,63,70,0.6)", borderRadius: "7px",
              padding: "8px 10px", fontSize: "0.78rem", resize: "vertical",
              fontFamily: "inherit", boxSizing: "border-box",
            }}
          />
          <button
            onClick={submitResponse}
            disabled={loading || !ownerResponse.trim()}
            style={{
              marginTop: "6px", width: "100%", padding: "7px", borderRadius: "7px",
              background: ownerResponse.trim() ? "rgba(99,102,241,0.15)" : "rgba(63,63,70,0.2)",
              color: ownerResponse.trim() ? "#818cf8" : "#52525b",
              border: `1px solid ${ownerResponse.trim() ? "rgba(99,102,241,0.3)" : "rgba(63,63,70,0.3)"}`,
              fontSize: "0.75rem", fontWeight: 600, cursor: ownerResponse.trim() ? "pointer" : "not-allowed",
              transition: "background 0.15s ease",
            }}
          >
            {loading ? "Processing..." : "Submit Response →"}
          </button>
        </div>
      )}

      {/* Received: show brief */}
      {intakeStatus === "received" && brief && (
        <div style={{ fontSize: "0.78rem" }}>
          <div style={{ color: "#a1a1aa", fontWeight: 600, marginBottom: "5px" }}>
            Chief Complaint: <span style={{ color: "#e4e4e7" }}>{brief.chief_complaint}</span>
          </div>
          {brief.symptoms?.length > 0 && (
            <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginBottom: "5px" }}>
              {brief.symptoms.map((s: any, i: number) => (
                <span key={i} style={{
                  background: "rgba(99,102,241,0.12)", color: "#a5b4fc",
                  border: "1px solid rgba(99,102,241,0.25)", borderRadius: "12px",
                  padding: "2px 8px", fontSize: "0.68rem", fontWeight: 600,
                }}>
                  {s.name} · {s.duration_days}d · {s.severity}
                </span>
              ))}
            </div>
          )}
          {brief.owner_verbatim && (
            <div style={{ color: "#71717a", fontStyle: "italic", marginBottom: "5px", borderLeft: "2px solid rgba(99,102,241,0.3)", paddingLeft: "8px" }}>
              "{brief.owner_verbatim}"
            </div>
          )}
          {brief.suggested_focus?.length > 0 && (
            <div style={{ color: "#a1a1aa" }}>
              Focus: {brief.suggested_focus.map((f: string) => (
                <span key={f} style={{ background: "rgba(16,185,129,0.1)", color: "#34d399", borderRadius: "4px", padding: "0 5px", marginLeft: "4px", fontSize: "0.68rem", fontWeight: 600, border: "1px solid rgba(16,185,129,0.2)" }}>{f}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Received but brief not loaded locally - fetch it */}
      {intakeStatus === "received" && !brief && (
        <BriefLoader timeblockId={timeblockId} onLoaded={setBrief} />
      )}
    </div>
  );
}

function BriefLoader({ timeblockId, onLoaded }: { timeblockId: string; onLoaded: (b: any) => void }) {
  const [fetched, setFetched] = useState(false);

  if (!fetched) {
    fetch(`${API}/api/intake/${timeblockId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && d.status === "received") { onLoaded(d); setFetched(true); } })
      .catch(() => {});
    setFetched(true);
  }

  return (
    <div style={{ color: "#4ade80", fontSize: "0.75rem" }}>
      ✓ Pre-Exam Brief on file
    </div>
  );
}
