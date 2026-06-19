"use client";

import { useState, useEffect, useCallback } from "react";
import { Users, RefreshCw, CheckCircle, Clock, Zap } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface WaitlistEntry {
  id: string;
  patient_id: string;
  patient_name: string;
  owner_name: string;
  clinic_id: string;
  procedure_type: string;
  urgency: "asap" | "within_week" | "flexible";
  offer_status: "waiting" | "offered" | "accepted" | "expired";
  join_date: string;
}

interface BackfillMatch {
  offer_id?: string;
  waitlist_entry_id: string;
  patient_id: string;
  patient_name: string;
  procedure_type: string;
  urgency: string;
  slot_timeblock_id: string;
  slot_start: string;
  slot_end: string;
  clinic_id: string;
}

interface WaitlistPanelProps {
  clinicId?: string;
  onLogEntry?: (msg: string) => void;
}

const URGENCY_STYLES: Record<string, { color: string; bg: string; label: string; icon: any }> = {
  asap:        { color: "#ef4444", bg: "rgba(239,68,68,0.12)", label: "ASAP", icon: Zap },
  within_week: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", label: "Within Week", icon: Clock },
  flexible:    { color: "#10b981", bg: "rgba(16,185,129,0.12)", label: "Flexible", icon: Clock },
};

export default function WaitlistPanel({ clinicId, onLogEntry }: WaitlistPanelProps) {
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [matches, setMatches] = useState<BackfillMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"waitlist" | "backfill">("waitlist");

  const loadWaitlist = useCallback(async () => {
    setLoading(true);
    try {
      const url = clinicId ? `${API}/api/waitlist?clinic_id=${clinicId}` : `${API}/api/waitlist`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEntries(data.entries || []);
      }
    } catch {}
    setLoading(false);
  }, [clinicId]);

  useEffect(() => { loadWaitlist(); }, [loadWaitlist]);

  const runBackfill = async () => {
    setRunning(true);
    try {
      const url = clinicId ? `${API}/api/waitlist/backfill?clinic_id=${clinicId}` : `${API}/api/waitlist/backfill`;
      const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
      if (res.ok) {
        const data = await res.json();
        setMatches(data.matches || []);
        setActiveTab("backfill");
        onLogEntry?.(`WAITLIST AGENT: Backfill complete — ${data.matches_found} match(es) from ${data.waitlist_count} waiting`);
      }
    } catch {}
    setRunning(false);
  };

  const offerSlot = async (entryId: string) => {
    await fetch(`${API}/api/waitlist/${entryId}/offer`, { method: "PUT" });
    onLogEntry?.(`WAITLIST AGENT: Slot offered to entry ${entryId.slice(0, 8)}`);
    setMatches(prev => prev.filter(m => m.waitlist_entry_id !== entryId));
    loadWaitlist();
  };

  const formatDate = (dt: string) => {
    try { return new Date(dt).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch { return dt; }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 0 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid rgba(63,63,70,0.4)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Users size={16} color="#8b5cf6" />
          <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#e4e4e7" }}>Waitlist</span>
          <span style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa", borderRadius: "10px", padding: "1px 7px", fontSize: "0.68rem", fontWeight: 600 }}>
            {entries.length}
          </span>
        </div>
        <button
          onClick={runBackfill}
          disabled={running}
          style={{
            display: "flex", alignItems: "center", gap: "6px",
            background: "rgba(139,92,246,0.15)", color: "#a78bfa",
            border: "1px solid rgba(139,92,246,0.3)", borderRadius: "8px",
            padding: "5px 12px", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer",
            opacity: running ? 0.7 : 1, transition: "all 0.2s",
          }}
        >
          <RefreshCw size={12} style={{ animation: running ? "spin 1s linear infinite" : "none" }} />
          Backfill
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid rgba(63,63,70,0.3)", flexShrink: 0 }}>
        {(["waitlist", "backfill"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1, padding: "8px", fontSize: "0.73rem", fontWeight: 600,
              background: activeTab === tab ? "rgba(139,92,246,0.1)" : "transparent",
              color: activeTab === tab ? "#a78bfa" : "#71717a",
              border: "none", borderBottom: activeTab === tab ? "2px solid #8b5cf6" : "2px solid transparent",
              cursor: "pointer", transition: "all 0.2s", textTransform: "capitalize",
            }}
          >
            {tab === "backfill" ? `Matches (${matches.length})` : `Queue (${entries.length})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "10px" }}>
        {activeTab === "waitlist" && (
          loading ? (
            <div style={{ color: "#52525b", fontSize: "0.78rem", padding: "16px", textAlign: "center" }}>Loading waitlist…</div>
          ) : entries.length === 0 ? (
            <div style={{ color: "#52525b", fontSize: "0.78rem", padding: "24px 16px", textAlign: "center" }}>
              <Users size={32} style={{ opacity: 0.3, marginBottom: "8px" }} />
              <div>No patients on waitlist</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {entries.map(entry => {
                const ug = URGENCY_STYLES[entry.urgency] || URGENCY_STYLES.flexible;
                const Icon = ug.icon;
                return (
                  <div key={entry.id} style={{
                    background: "rgba(24,24,27,0.6)", border: "1px solid rgba(63,63,70,0.4)",
                    borderRadius: "10px", padding: "10px 12px",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 700, fontSize: "0.83rem", color: "#e4e4e7" }}>
                        {entry.patient_name || entry.patient_id.slice(0, 8)}
                      </span>
                      <span style={{ background: ug.bg, color: ug.color, borderRadius: "6px", padding: "2px 7px", fontSize: "0.65rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                        <Icon size={9} /> {ug.label}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#a1a1aa" }}>{entry.procedure_type}</div>
                    <div style={{ fontSize: "0.68rem", color: "#52525b", marginTop: "4px" }}>
                      Joined: {formatDate(entry.join_date)}
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}

        {activeTab === "backfill" && (
          matches.length === 0 ? (
            <div style={{ color: "#52525b", fontSize: "0.78rem", padding: "24px 16px", textAlign: "center" }}>
              <RefreshCw size={32} style={{ opacity: 0.3, marginBottom: "8px" }} />
              <div>Run backfill to find open slot matches</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {matches.map(match => {
                const ug = URGENCY_STYLES[match.urgency] || URGENCY_STYLES.flexible;
                return (
                  <div key={match.offer_id || match.slot_timeblock_id} style={{
                    background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.2)",
                    borderRadius: "10px", padding: "10px 12px",
                  }}>
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "#e4e4e7", marginBottom: "2px" }}>
                          {match.patient_name || "Patient"} → {match.procedure_type}
                        </div>
                        <div style={{ fontSize: "0.73rem", color: "#10b981" }}>
                          Slot: {formatDate(match.slot_start)}
                        </div>
                        <div style={{ fontSize: "0.68rem", color: "#52525b", marginTop: "2px" }}>
                          Urgency: {ug.label}
                        </div>
                      </div>
                      <button
                        onClick={() => offerSlot(match.waitlist_entry_id)}
                        style={{
                          display: "flex", alignItems: "center", gap: "4px",
                          background: "rgba(16,185,129,0.15)", color: "#10b981",
                          border: "1px solid rgba(16,185,129,0.3)", borderRadius: "6px",
                          padding: "4px 10px", fontSize: "0.7rem", fontWeight: 600, cursor: "pointer",
                          flexShrink: 0,
                        }}
                      >
                        <CheckCircle size={11} /> Offer
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}
      </div>
    </div>
  );
}
