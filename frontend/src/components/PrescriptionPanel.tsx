"use client";

import { useState, useEffect, useCallback } from "react";
import { Pill, Plus, AlertTriangle, RefreshCw, CheckCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface Prescription {
  id: string;
  patient_id: string;
  drug_name: string;
  dose: string;
  frequency: string;
  duration_days: number;
  refills_remaining: number;
  supply_ends_at: string;
  issued_by: string;
  issued_date: string;
  timeblock_id?: string;
}

interface PrescriptionPanelProps {
  patientId: string;
  patientName?: string;
  timeblockId?: string;
  issuedBy?: string;
  onLogEntry?: (msg: string) => void;
}

function getSupplyStatus(supplyEndsAt: string, refillsRemaining: number): { label: string; color: string; bg: string } {
  const today = new Date();
  const ends  = new Date(supplyEndsAt);
  const diffDays = Math.round((ends.getTime() - today.getTime()) / 86400000);
  if (diffDays < 0)  return { label: "Expired", color: "#ef4444", bg: "rgba(239,68,68,0.1)" };
  if (diffDays <= 7) return { label: `Expires in ${diffDays}d`, color: "#f59e0b", bg: "rgba(245,158,11,0.1)" };
  return { label: `Expires ${ends.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`, color: "#10b981", bg: "rgba(16,185,129,0.1)" };
}

export default function PrescriptionPanel({ patientId, patientName, timeblockId, issuedBy, onLogEntry }: PrescriptionPanelProps) {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refilling, setRefilling] = useState<string | null>(null);
  const [allergyAlert, setAllergyAlert] = useState<string | null>(null);
  const [form, setForm] = useState({
    drug_name: "", dose: "", frequency: "SID", duration_days: "14", refills_remaining: "0",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/prescriptions/patient/${patientId}`);
      if (res.ok) { const d = await res.json(); setPrescriptions(d.prescriptions || []); }
    } catch {}
    setLoading(false);
  }, [patientId]);

  useEffect(() => { load(); }, [load]);

  const createPrescription = async () => {
    if (!form.drug_name || !form.dose) return;
    setSaving(true);
    setAllergyAlert(null);
    try {
      const res = await fetch(`${API}/api/prescriptions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          timeblock_id: timeblockId,
          drug_name: form.drug_name,
          dose: form.dose,
          frequency: form.frequency,
          duration_days: parseInt(form.duration_days),
          refills_remaining: parseInt(form.refills_remaining),
          issued_by: issuedBy || "Dr. Smith",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.allergy_alert) {
          setAllergyAlert(data.allergy_alert.detail);
          onLogEntry?.(`PRESCRIPTION AGENT: [CRITICAL] Allergy alert — ${data.allergy_alert.detail.slice(0, 80)}`);
        } else {
          onLogEntry?.(`PRESCRIPTION AGENT: Rx created — ${form.drug_name} ${form.dose} ${form.frequency}`);
        }
        setShowNew(false);
        setForm({ drug_name: "", dose: "", frequency: "SID", duration_days: "14", refills_remaining: "0" });
        load();
      }
    } catch {}
    setSaving(false);
  };

  const requestRefill = async (rxId: string, drugName: string) => {
    setRefilling(rxId);
    try {
      const res = await fetch(`${API}/api/prescriptions/${rxId}/refill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initiated_by: "front_desk" }),
      });
      if (res.ok) {
        const data = await res.json();
        const status = data.status === "auto_approved" ? "AUTO-APPROVED ✓" : "Flagged for vet review";
        onLogEntry?.(`PRESCRIPTION AGENT: ${drugName} refill — ${status}`);
        load();
      }
    } catch {}
    setRefilling(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.78rem", fontWeight: 700, color: "#e4e4e7" }}>
          <Pill size={14} color="#8b5cf6" />
          Prescriptions
        </div>
        <button
          onClick={() => setShowNew(v => !v)}
          style={{
            display: "flex", alignItems: "center", gap: "4px",
            background: "rgba(139,92,246,0.12)", color: "#a78bfa",
            border: "1px solid rgba(139,92,246,0.25)", borderRadius: "6px",
            padding: "3px 9px", fontSize: "0.7rem", fontWeight: 600, cursor: "pointer",
          }}
        >
          <Plus size={10} /> New Rx
        </button>
      </div>

      {/* Allergy alert */}
      {allergyAlert && (
        <div style={{
          background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.4)",
          borderRadius: "8px", padding: "10px 12px", display: "flex", gap: "8px",
        }}>
          <AlertTriangle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: "0.78rem", color: "#ef4444", marginBottom: "4px" }}>
              ⚠ ALLERGY ALERT
            </div>
            <div style={{ fontSize: "0.73rem", color: "#fca5a5", lineHeight: 1.4 }}>{allergyAlert}</div>
            <button onClick={() => setAllergyAlert(null)} style={{ marginTop: "6px", fontSize: "0.65rem", color: "#71717a", background: "none", border: "none", cursor: "pointer" }}>Dismiss</button>
          </div>
        </div>
      )}

      {/* New Rx form */}
      {showNew && (
        <div style={{
          background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.2)",
          borderRadius: "10px", padding: "12px", display: "flex", flexDirection: "column", gap: "8px",
        }}>
          <input placeholder="Drug name" value={form.drug_name} onChange={e => setForm(f => ({ ...f, drug_name: e.target.value }))}
            style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
            <input placeholder="Dose (e.g. 25mg)" value={form.dose} onChange={e => setForm(f => ({ ...f, dose: e.target.value }))}
              style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }} />
            <select value={form.frequency} onChange={e => setForm(f => ({ ...f, frequency: e.target.value }))}
              style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }}>
              {["SID","BID","TID","QID","PRN","EOD","Weekly"].map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
            <input placeholder="Duration (days)" type="number" value={form.duration_days} onChange={e => setForm(f => ({ ...f, duration_days: e.target.value }))}
              style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }} />
            <input placeholder="Refills" type="number" min="0" value={form.refills_remaining} onChange={e => setForm(f => ({ ...f, refills_remaining: e.target.value }))}
              style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }} />
          </div>
          <button onClick={createPrescription} disabled={saving || !form.drug_name || !form.dose}
            style={{
              background: "rgba(139,92,246,0.2)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.3)",
              borderRadius: "6px", padding: "7px", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
            }}>
            {saving ? "Creating…" : "Create Prescription"}
          </button>
        </div>
      )}

      {/* Prescription list */}
      {loading ? (
        <div style={{ color: "#71717a", fontSize: "0.78rem" }}>Loading…</div>
      ) : prescriptions.length === 0 ? (
        <div style={{ color: "#52525b", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "6px" }}>
          <Pill size={14} style={{ opacity: 0.4 }} /> No active prescriptions
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {prescriptions.map(rx => {
            const status = getSupplyStatus(rx.supply_ends_at, rx.refills_remaining);
            const isRefilling = refilling === rx.id;
            return (
              <div key={rx.id} style={{
                background: "rgba(24,24,27,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                borderRadius: "8px", padding: "8px 10px",
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: "0.8rem", color: "#e4e4e7" }}>
                      {rx.drug_name} <span style={{ fontWeight: 400, color: "#a1a1aa" }}>{rx.dose} {rx.frequency}</span>
                    </div>
                    <div style={{ fontSize: "0.68rem", color: "#71717a", marginTop: "2px" }}>
                      {rx.duration_days}d · {rx.refills_remaining} refill{rx.refills_remaining !== 1 ? "s" : ""} · {rx.issued_by}
                    </div>
                    <span style={{ background: status.bg, color: status.color, borderRadius: "5px", padding: "1px 7px", fontSize: "0.62rem", fontWeight: 700, display: "inline-block", marginTop: "4px" }}>
                      {status.label}
                    </span>
                  </div>
                  <button
                    onClick={() => requestRefill(rx.id, rx.drug_name)}
                    disabled={isRefilling}
                    style={{
                      display: "flex", alignItems: "center", gap: "4px",
                      background: "rgba(139,92,246,0.12)", color: "#a78bfa",
                      border: "1px solid rgba(139,92,246,0.2)", borderRadius: "6px",
                      padding: "4px 9px", fontSize: "0.68rem", fontWeight: 600, cursor: "pointer", flexShrink: 0,
                    }}
                  >
                    <RefreshCw size={10} style={{ animation: isRefilling ? "spin 1s linear infinite" : "none" }} />
                    Refill
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
