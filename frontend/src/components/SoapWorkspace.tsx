"use client";

import { useState, useEffect } from "react";
import { X, Lock, Unlock } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface SoapWorkspaceProps {
  item: any;
  patient: any | null;
  onClose: () => void;
  onLogEntry?: (entry: string) => void;
}

const VITAL_LABELS: Record<string, string> = {
  temperature_c: "Temperature (°C)",
  heart_rate:    "Heart Rate (bpm)",
  resp_rate:     "Resp. Rate (bpm)",
  weight_kg:     "Weight (kg)",
};

const EXAM_LABELS: Record<string, string> = {
  general:            "General",
  skin_coat:          "Skin & Coat",
  eyes_ears:          "Eyes & Ears",
  cardiovascular:     "Cardiovascular",
  respiratory:        "Respiratory",
  gastrointestinal:   "GI",
  surgical_site:      "Surgical Site",
  oral_exam:          "Oral Exam",
  periodontal_score:  "Periodontal Score",
  tooth_resorption:   "Tooth Resorption",
  skin_coat_condition:"Skin & Coat Condition",
  matting_level:      "Matting Level",
  ear_condition:      "Ear Condition",
  nail_condition:     "Nail Condition",
  vaccination_site:   "Vaccination Site",
  lymph_nodes:        "Lymph Nodes",
  pre_op_assessment:  "Pre-Op Assessment",
};

export default function SoapWorkspace({ item, patient, onClose, onLogEntry }: SoapWorkspaceProps) {
  const [note, setNote] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [localNote, setLocalNote] = useState<any>(null);

  const tbId = item.timeblock_id ?? item.id;

  useEffect(() => {
    if (!tbId) return;
    loadNote();
  }, [tbId]);

  const loadNote = async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/soap/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: tbId }),
    });
    if (res.ok) {
      const d = await res.json();
      setNote(d);
      setLocalNote(JSON.parse(JSON.stringify(d)));  // deep copy for editing
      onLogEntry?.(`VERA (SOAP): Draft generated from ${item.job?.procedure ?? "General"} template`);
    }
    setLoading(false);
  };

  const updateVital = (key: string, value: string) => {
    setLocalNote((prev: any) => ({
      ...prev,
      objective: {
        ...prev.objective,
        vitals: { ...prev.objective.vitals, [key]: value || null },
      },
    }));
  };

  const updateExamFinding = (key: string, value: string) => {
    setLocalNote((prev: any) => ({
      ...prev,
      objective: {
        ...prev.objective,
        exam_findings: { ...prev.objective?.exam_findings, [key]: value || null },
      },
    }));
  };

  const save = async () => {
    if (!note || note.signed) return;
    setSaving(true);
    const res = await fetch(`${API}/api/soap/${note.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjective: localNote.subjective,
        objective: localNote.objective,
        assessment: localNote.assessment,
        plan: localNote.plan,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      setNote(updated);
      setLocalNote(JSON.parse(JSON.stringify(updated)));
    }
    setSaving(false);
  };

  const sign = async () => {
    if (!note) return;
    await save();
    setSigning(true);
    const res = await fetch(`${API}/api/soap/${note.id}/sign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signed_by: "Dr. Smith" }),
    });
    if (res.status === 400) {
      const d = await res.json();
      alert(d.detail || "Must enter at least one vital before signing.");
      setSigning(false);
      return;
    }
    if (res.ok) {
      const d = await res.json();
      setNote((prev: any) => ({ ...prev, signed: true, signed_at: d.signed_at }));
      setLocalNote((prev: any) => ({ ...prev, signed: true, signed_at: d.signed_at }));
      onLogEntry?.("VERA (SOAP): Note signed — triggering follow-up generation");
      onLogEntry?.(`VERA (Follow-Up): Follow-up draft created (id: ${d.followup_draft_id?.substring(0, 8)}...)`);
      // Close after brief delay
      setTimeout(() => onClose(), 1500);
    }
    setSigning(false);
  };

  const isSigned = note?.signed ?? false;

  return (
    <div style={{
      width: "420px",
      height: "100%",
      background: "#101012",
      borderLeft: "1px solid rgba(63,63,70,0.7)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "14px 16px",
        borderBottom: "1px solid rgba(63,63,70,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
        background: isSigned ? "rgba(139,92,246,0.08)" : "rgba(15,15,17,0.8)",
      }}>
        <div>
          <div style={{ color: "#e4e4e7", fontWeight: 700, fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "7px" }}>
            {isSigned ? <Lock size={14} color="#a78bfa" /> : <Unlock size={14} color="#a78bfa" />}
            SOAP Note — {patient?.name ?? "Patient"}
          </div>
          <div style={{ color: "#71717a", fontSize: "0.7rem", marginTop: "2px" }}>
            {item.job?.procedure ?? "Examination"}{isSigned ? ` · Signed ${note?.signed_at ? new Date(note.signed_at).toLocaleTimeString() : ""}` : ""}
          </div>
        </div>
        <button onClick={onClose} style={{ background: "transparent", border: "none", cursor: "pointer", color: "#71717a", padding: "4px" }}>
          <X size={16} />
        </button>
      </div>

      {loading ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#52525b" }}>
          Vera is drafting the SOAP note...
        </div>
      ) : (
        <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px" }}>
          {/* S — Subjective */}
          <SoapSection label="S — Subjective" color="#818cf8">
            <textarea
              value={localNote?.subjective ?? ""}
              onChange={e => setLocalNote((p: any) => ({ ...p, subjective: e.target.value }))}
              disabled={isSigned}
              rows={4}
              style={textareaStyle(isSigned)}
              placeholder="Owner's history and chief complaint..."
            />
          </SoapSection>

          {/* O — Objective */}
          <SoapSection label="O — Objective" color="#34d399">
            <div style={{ marginBottom: "8px" }}>
              <div style={{ fontSize: "0.68rem", color: "#71717a", fontWeight: 700, marginBottom: "5px", letterSpacing: "0.05em" }}>VITALS</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                {Object.entries(localNote?.objective?.vitals ?? {}).map(([key, val]) => (
                  <div key={key}>
                    <label style={{ fontSize: "0.65rem", color: "#71717a", display: "block", marginBottom: "2px" }}>
                      {VITAL_LABELS[key] ?? key}
                    </label>
                    <input
                      type="text"
                      value={(val as string) ?? ""}
                      onChange={e => updateVital(key, e.target.value)}
                      disabled={isSigned}
                      placeholder="—"
                      style={inputStyle(isSigned)}
                    />
                  </div>
                ))}
              </div>
            </div>
            {localNote?.objective?.exam_findings && Object.keys(localNote.objective.exam_findings).length > 0 && (
              <div>
                <div style={{ fontSize: "0.68rem", color: "#71717a", fontWeight: 700, marginBottom: "5px", letterSpacing: "0.05em" }}>EXAM FINDINGS</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  {Object.entries(localNote.objective.exam_findings).map(([key, val]) => (
                    <div key={key} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <label style={{ fontSize: "0.65rem", color: "#71717a", width: "110px", flexShrink: 0 }}>
                        {EXAM_LABELS[key] ?? key}
                      </label>
                      <input
                        type="text"
                        value={(val as string) ?? ""}
                        onChange={e => updateExamFinding(key, e.target.value)}
                        disabled={isSigned}
                        placeholder="—"
                        style={{ ...inputStyle(isSigned), flex: 1 }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </SoapSection>

          {/* A — Assessment */}
          <SoapSection label="A — Assessment" color="#fbbf24">
            <textarea
              value={localNote?.assessment ?? ""}
              onChange={e => setLocalNote((p: any) => ({ ...p, assessment: e.target.value }))}
              disabled={isSigned}
              rows={3}
              style={textareaStyle(isSigned)}
              placeholder="Enter diagnosis..."
            />
          </SoapSection>

          {/* P — Plan */}
          <SoapSection label="P — Plan" color="#60a5fa">
            <textarea
              value={localNote?.plan ?? ""}
              onChange={e => setLocalNote((p: any) => ({ ...p, plan: e.target.value }))}
              disabled={isSigned}
              rows={4}
              style={textareaStyle(isSigned)}
              placeholder="Treatment and follow-up plan..."
            />
          </SoapSection>
        </div>
      )}

      {/* Footer actions */}
      {!loading && (
        <div style={{
          padding: "12px 16px",
          borderTop: "1px solid rgba(63,63,70,0.5)",
          flexShrink: 0,
          display: "flex",
          gap: "8px",
        }}>
          {!isSigned ? (
            <>
              <button
                onClick={save}
                disabled={saving}
                style={{
                  flex: 1, padding: "8px", borderRadius: "8px",
                  background: "rgba(63,63,70,0.3)", color: "#a1a1aa",
                  border: "1px solid rgba(63,63,70,0.5)", fontSize: "0.75rem",
                  fontWeight: 600, cursor: "pointer",
                }}
              >
                {saving ? "Saving..." : "Save Draft"}
              </button>
              <button
                onClick={sign}
                disabled={signing}
                style={{
                  flex: 2, padding: "8px", borderRadius: "8px",
                  background: "rgba(139,92,246,0.15)", color: "#a78bfa",
                  border: "1px solid rgba(139,92,246,0.35)", fontSize: "0.75rem",
                  fontWeight: 700, cursor: "pointer", transition: "background 0.15s ease",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                }}
              >
                <Lock size={13} />
                {signing ? "Signing..." : "Sign & Complete"}
              </button>
            </>
          ) : (
            <div style={{
              flex: 1, padding: "8px", textAlign: "center",
              background: "rgba(139,92,246,0.1)", color: "#a78bfa",
              border: "1px solid rgba(139,92,246,0.25)", borderRadius: "8px",
              fontSize: "0.75rem", fontWeight: 700,
            }}>
              🔒 Signed — Read Only
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SoapSection({ label, color, children }: { label: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{
        fontSize: "0.72rem", fontWeight: 700, color,
        letterSpacing: "0.06em", marginBottom: "6px",
        display: "flex", alignItems: "center", gap: "6px",
      }}>
        <span style={{ width: "3px", height: "14px", background: color, borderRadius: "2px", display: "inline-block" }} />
        {label}
      </div>
      {children}
    </div>
  );
}

const textareaStyle = (disabled: boolean): React.CSSProperties => ({
  width: "100%",
  background: disabled ? "rgba(9,9,11,0.5)" : "#0c0c0e",
  color: disabled ? "#71717a" : "#d4d4d8",
  border: "1px solid rgba(63,63,70,0.6)",
  borderRadius: "7px",
  padding: "8px 10px",
  fontSize: "0.78rem",
  resize: "vertical",
  fontFamily: "inherit",
  boxSizing: "border-box",
  lineHeight: "1.5",
  opacity: disabled ? 0.7 : 1,
});

const inputStyle = (disabled: boolean): React.CSSProperties => ({
  background: disabled ? "rgba(9,9,11,0.5)" : "#0c0c0e",
  color: disabled ? "#71717a" : "#d4d4d8",
  border: "1px solid rgba(63,63,70,0.6)",
  borderRadius: "6px",
  padding: "5px 8px",
  fontSize: "0.75rem",
  fontFamily: "inherit",
  width: "100%",
  boxSizing: "border-box",
  opacity: disabled ? 0.7 : 1,
});
