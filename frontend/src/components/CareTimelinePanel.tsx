"use client";

import { useState, useEffect, useCallback } from "react";
import { Syringe, Plus, CheckCircle, AlertCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface CareEvent {
  id: string;
  patient_id: string;
  patient_name?: string;
  protocol_name: string;
  interval_months: number;
  administered_date: string;
  next_due_date: string;
  batch_number?: string;
  administered_by?: string;
}

interface CareTimelinePanelProps {
  patientId: string;
  patientName?: string;
  timeblockId?: string;
  onLogEntry?: (msg: string) => void;
}

function getDueStatus(nextDue: string): { label: string; color: string; bg: string } {
  const today = new Date();
  const due   = new Date(nextDue);
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86400000);
  if (diffDays < 0)  return { label: `${Math.abs(diffDays)}d overdue`, color: "#ef4444", bg: "rgba(239,68,68,0.1)" };
  if (diffDays <= 14) return { label: `Due in ${diffDays}d`, color: "#f59e0b", bg: "rgba(245,158,11,0.1)" };
  return { label: `Due ${due.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`, color: "#10b981", bg: "rgba(16,185,129,0.1)" };
}

export default function CareTimelinePanel({ patientId, patientName, timeblockId, onLogEntry }: CareTimelinePanelProps) {
  const [events, setEvents] = useState<CareEvent[]>([]);
  const [protocols, setProtocols] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRecord, setShowRecord] = useState(false);
  const [form, setForm] = useState({ protocol_id: "", administered_date: new Date().toISOString().slice(0, 10), batch_number: "", administered_by: "" });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [evRes, prRes] = await Promise.all([
        fetch(`${API}/api/care/patient/${patientId}`),
        fetch(`${API}/api/care/protocols`),
      ]);
      if (evRes.ok) { const d = await evRes.json(); setEvents(d.events || []); }
      if (prRes.ok) { const d = await prRes.json(); setProtocols(d.protocols || []); }
    } catch {}
    setLoading(false);
  }, [patientId]);

  useEffect(() => { load(); }, [load]);

  const recordEvent = async () => {
    if (!form.protocol_id) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/care/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, patient_id: patientId, timeblock_id: timeblockId }),
      });
      if (res.ok) {
        const ev = await res.json();
        onLogEntry?.(`PREVENTIVE CARE AGENT: Recorded ${ev.protocol_name} — next due ${ev.next_due_date}`);
        setShowRecord(false);
        setForm({ protocol_id: "", administered_date: new Date().toISOString().slice(0, 10), batch_number: "", administered_by: "" });
        load();
      }
    } catch {}
    setSaving(false);
  };

  if (loading) {
    return <div style={{ padding: "12px 16px", color: "#71717a", fontSize: "0.78rem" }}>Loading care timeline…</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.78rem", fontWeight: 700, color: "#e4e4e7" }}>
          <Syringe size={14} color="#10b981" />
          Care Timeline
        </div>
        <button
          onClick={() => setShowRecord(v => !v)}
          style={{
            display: "flex", alignItems: "center", gap: "4px",
            background: "rgba(16,185,129,0.12)", color: "#10b981",
            border: "1px solid rgba(16,185,129,0.25)", borderRadius: "6px",
            padding: "3px 9px", fontSize: "0.7rem", fontWeight: 600, cursor: "pointer",
          }}
        >
          <Plus size={10} /> Record
        </button>
      </div>

      {/* Record form */}
      {showRecord && (
        <div style={{
          background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)",
          borderRadius: "10px", padding: "12px", display: "flex", flexDirection: "column", gap: "8px",
        }}>
          <select
            value={form.protocol_id}
            onChange={e => setForm(f => ({ ...f, protocol_id: e.target.value }))}
            style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }}
          >
            <option value="">Select protocol…</option>
            {protocols.map(p => (
              <option key={p.id} value={p.id}>{p.protocol_name} ({p.species}, {p.interval_months}mo)</option>
            ))}
          </select>
          <input
            type="date" value={form.administered_date}
            onChange={e => setForm(f => ({ ...f, administered_date: e.target.value }))}
            style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }}
          />
          <input
            placeholder="Batch number (optional)"
            value={form.batch_number}
            onChange={e => setForm(f => ({ ...f, batch_number: e.target.value }))}
            style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }}
          />
          <input
            placeholder="Administered by"
            value={form.administered_by}
            onChange={e => setForm(f => ({ ...f, administered_by: e.target.value }))}
            style={{ background: "#18181b", color: "#e4e4e7", border: "1px solid rgba(63,63,70,0.5)", borderRadius: "6px", padding: "6px 8px", fontSize: "0.78rem" }}
          />
          <button
            onClick={recordEvent} disabled={saving || !form.protocol_id}
            style={{
              background: saving ? "rgba(16,185,129,0.1)" : "rgba(16,185,129,0.2)",
              color: "#10b981", border: "1px solid rgba(16,185,129,0.3)",
              borderRadius: "6px", padding: "6px", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
            }}
          >
            {saving ? "Saving…" : "Save Care Event"}
          </button>
        </div>
      )}

      {/* Timeline */}
      {events.length === 0 ? (
        <div style={{ color: "#52525b", fontSize: "0.75rem", padding: "8px 0", display: "flex", alignItems: "center", gap: "6px" }}>
          <Syringe size={14} style={{ opacity: 0.4 }} /> No care events recorded
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {events.map(ev => {
            const status = getDueStatus(ev.next_due_date);
            return (
              <div key={ev.id} style={{
                background: "rgba(24,24,27,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                borderRadius: "8px", padding: "8px 10px", display: "flex", alignItems: "center", gap: "10px",
              }}>
                <CheckCircle size={14} color="#10b981" style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.78rem", color: "#e4e4e7" }}>{ev.protocol_name}</div>
                  <div style={{ fontSize: "0.68rem", color: "#71717a", marginTop: "2px" }}>
                    Given: {ev.administered_date.slice(0, 10)}
                    {ev.administered_by ? ` · ${ev.administered_by}` : ""}
                  </div>
                </div>
                <span style={{ background: status.bg, color: status.color, borderRadius: "6px", padding: "2px 8px", fontSize: "0.65rem", fontWeight: 700, flexShrink: 0 }}>
                  {status.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
