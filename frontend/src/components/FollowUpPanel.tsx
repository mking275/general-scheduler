"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

const TONES = ["wellness", "surgery", "emergency"] as const;
type Tone = typeof TONES[number];

const TONE_LABELS: Record<Tone, string> = {
  wellness:  "Wellness",
  surgery:   "Surgery",
  emergency: "Emergency",
};

interface FollowUpPanelProps {
  timeblockId: string;
  followupStatus: string;
  onStatusChange: (s: string) => void;
  onLogEntry?: (entry: string) => void;
}

export default function FollowUpPanel({
  timeblockId, followupStatus, onStatusChange, onLogEntry,
}: FollowUpPanelProps) {
  const [draft, setDraft] = useState<any>(null);
  const [editedBody, setEditedBody] = useState("");
  const [selectedTone, setSelectedTone] = useState<Tone>("wellness");
  const [loading, setLoading] = useState(false);
  const [approved, setApproved] = useState(false);

  // Fetch draft if followup is active
  useEffect(() => {
    if (followupStatus !== "draft" && followupStatus !== "approved" && followupStatus !== "sent") return;
    fetch(`${API}/api/intake/${timeblockId}`)  // won't use; fetch followup directly
      .catch(() => {});
    fetchDraft();
  }, [followupStatus, timeblockId]);

  const fetchDraft = async () => {
    // Call draft creation which returns existing if present
    const res = await fetch(`${API}/api/followup/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: timeblockId }),
    });
    if (res.ok) {
      const d = await res.json();
      setDraft(d);
      setEditedBody(d.body);
      setSelectedTone(d.tone);
      onLogEntry?.(`FOLLOWUP AGENT: ${d.tone.charAt(0).toUpperCase() + d.tone.slice(1)} draft loaded`);
    }
  };

  const regenerate = async () => {
    if (!draft) return;
    setLoading(true);
    // Update tone then refetch
    await fetch(`${API}/api/followup/${draft.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tone: selectedTone }),
    });
    const res = await fetch(`${API}/api/followup/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: timeblockId }),
    });
    if (res.ok) {
      const d = await res.json();
      setDraft(d);
      setEditedBody(d.body);
      onLogEntry?.(`FOLLOWUP AGENT: Regenerated with ${selectedTone} tone`);
    }
    setLoading(false);
  };

  const saveEdit = async () => {
    if (!draft) return;
    await fetch(`${API}/api/followup/${draft.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: editedBody }),
    });
    setDraft((prev: any) => ({ ...prev, body: editedBody }));
  };

  const approve = async () => {
    if (!draft) return;
    setLoading(true);
    await saveEdit();
    const res = await fetch(`${API}/api/followup/${draft.id}/approve`, { method: "POST" });
    if (res.ok) {
      setApproved(true);
      onStatusChange("sent");
      onLogEntry?.("FOLLOWUP AGENT: Follow-up approved and sent (simulated)");
    }
    setLoading(false);
  };

  if (followupStatus === "not_started") return null;

  if (approved || followupStatus === "sent") {
    return (
      <div style={{
        marginTop: "10px", padding: "10px 12px",
        background: "rgba(16,185,129,0.08)",
        border: "1px solid rgba(16,185,129,0.25)",
        borderRadius: "10px", fontSize: "0.78rem",
        color: "#4ade80", fontWeight: 600, textAlign: "center",
      }}>
        ✅ Follow-up Sent
      </div>
    );
  }

  if (!draft) {
    return (
      <div style={{
        marginTop: "10px", padding: "10px 12px",
        background: "rgba(23,23,23,0.7)",
        border: "1px solid rgba(63,63,70,0.5)",
        borderRadius: "10px", fontSize: "0.75rem", color: "#a1a1aa",
      }}>
        ⏳ Generating follow-up draft...
      </div>
    );
  }

  return (
    <div style={{
      marginTop: "10px",
      background: "rgba(23,23,23,0.7)",
      border: "1px solid rgba(63,63,70,0.5)",
      borderRadius: "10px", padding: "12px",
      animation: "slideInUp 0.3s ease",
    }}>
      <style>{`
        @keyframes slideInUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#71717a", letterSpacing: "0.06em" }}>FOLLOW-UP DRAFT</span>
        {/* Tone selector */}
        <div style={{ display: "flex", gap: "4px" }}>
          {TONES.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedTone(t)}
              style={{
                padding: "2px 7px",
                borderRadius: "12px",
                fontSize: "0.65rem",
                fontWeight: 600,
                cursor: "pointer",
                border: "1px solid",
                background: selectedTone === t ? "rgba(99,102,241,0.15)" : "transparent",
                color: selectedTone === t ? "#818cf8" : "#71717a",
                borderColor: selectedTone === t ? "rgba(99,102,241,0.35)" : "rgba(63,63,70,0.5)",
                transition: "all 0.15s ease",
              }}
            >
              {TONE_LABELS[t]}
            </button>
          ))}
        </div>
      </div>

      {/* Subject */}
      <div style={{ fontSize: "0.72rem", color: "#a1a1aa", marginBottom: "3px" }}>Subject</div>
      <div style={{ fontSize: "0.78rem", color: "#d4d4d8", fontWeight: 600, marginBottom: "8px" }}>{draft.subject}</div>

      {/* Editable body */}
      <textarea
        value={editedBody}
        onChange={e => setEditedBody(e.target.value)}
        rows={6}
        style={{
          width: "100%", background: "#0c0c0e", color: "#d4d4d8",
          border: "1px solid rgba(63,63,70,0.6)", borderRadius: "7px",
          padding: "8px 10px", fontSize: "0.75rem", resize: "vertical",
          fontFamily: "inherit", boxSizing: "border-box", lineHeight: "1.5",
        }}
      />

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
        <button
          onClick={regenerate}
          disabled={loading}
          style={{
            flex: 1, padding: "7px", borderRadius: "7px",
            background: "rgba(63,63,70,0.3)", color: "#a1a1aa",
            border: "1px solid rgba(63,63,70,0.5)", fontSize: "0.72rem",
            fontWeight: 600, cursor: "pointer",
          }}
        >
          ↺ Regenerate
        </button>
        <button
          onClick={approve}
          disabled={loading}
          style={{
            flex: 2, padding: "7px", borderRadius: "7px",
            background: "rgba(16,185,129,0.12)", color: "#10b981",
            border: "1px solid rgba(16,185,129,0.3)", fontSize: "0.72rem",
            fontWeight: 700, cursor: "pointer", transition: "background 0.15s ease",
          }}
        >
          {loading ? "Approving..." : "✓ Approve & Send"}
        </button>
      </div>
    </div>
  );
}
