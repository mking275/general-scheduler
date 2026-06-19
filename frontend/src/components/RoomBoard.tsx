"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  available: { label: "Available",  color: "#4ade80", bg: "rgba(74,222,128,0.08)"  },
  prep:      { label: "In Prep",    color: "#fbbf24", bg: "rgba(251,191,36,0.08)"  },
  occupied:  { label: "Occupied",   color: "#f87171", bg: "rgba(248,113,113,0.08)" },
  cleaning:  { label: "Cleaning",   color: "#818cf8", bg: "rgba(129,140,248,0.08)" },
};

const ACTIONS = [
  { status: "prep",     label: "Mark In Prep"   },
  { status: "occupied", label: "Mark Occupied"  },
  { status: "cleaning", label: "Mark Cleaning"  },
  { status: "available",label: "Mark Available" },
];

interface Room {
  id: string;
  name: string;
  status: string;
  current_timeblock_id: string | null;
  // derived from schedule
  appointmentProcedure?: string;
  appointmentPatient?: string;
  appointmentVet?: string;
  appointmentTime?: string;
  riskLevel?: string;
}

interface RoomBoardProps {
  onLogEntry?: (entry: string) => void;
  clinicId?: string;
  scheduledItems?: any[];
}

export default function RoomBoard({ onLogEntry, clinicId, scheduledItems = [] }: RoomBoardProps) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  const deriveRooms = useCallback(async () => {
    const res = await fetch(`${API}/api/rooms`);
    if (!res.ok) return;
    const allRooms: Room[] = await res.json();

    // Filter to current clinic only
    const clinicItems = clinicId
      ? scheduledItems.filter(item => item.clinic_id === clinicId)
      : scheduledItems;

    // Build a map of roomId → appointment for today
    const today = new Date().toDateString();
    const roomApptMap: Record<string, any> = {};
    for (const item of clinicItems) {
      const apptDate = new Date(item.start_time).toDateString();
      if (apptDate !== today) continue;
      const resources: { id: string; name: string; type: string }[] = item.resources ?? [];
      const roomRes = resources.find(r => r.type === "Room");
      if (roomRes) {
        roomApptMap[roomRes.id] = item;
      }
    }

    // Enrich rooms with appointment context
    const enriched = allRooms
      .filter(r => {
        // Only show rooms belonging to this clinic
        // Westside rooms only shown for Westside; downtown rooms for downtown
        if (!clinicId) return true;
        const isWestside = r.name.toLowerCase().includes("westside");
        const isWestsideClinic = clinicId === "clinic-westside";
        return isWestside === isWestsideClinic || (!isWestside && !isWestsideClinic);
      })
      .map(room => {
        const appt = roomApptMap[room.id];
        if (appt) {
          const resources: { id: string; name: string; type: string }[] = appt.resources ?? [];
          const vetRes = resources.find(r => r.type === "Vet");
          const start = new Date(appt.start_time);
          const end = new Date(appt.end_time);
          const fmt = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          return {
            ...room,
            status: room.status === "available" ? "occupied" : room.status,
            appointmentProcedure: appt.job?.procedure ?? "Appointment",
            appointmentPatient: appt.job?.patient_name ?? "—",
            appointmentVet: vetRes?.name ?? "—",
            appointmentTime: `${fmt(start)} – ${fmt(end)}`,
            riskLevel: appt.risk_level ?? "low",
          };
        }
        return room;
      });

    setRooms(enriched);
  }, [clinicId, scheduledItems]);

  useEffect(() => { deriveRooms(); }, [deriveRooms]);

  const updateStatus = async (roomId: string, status: string) => {
    setLoading(roomId + status);
    const res = await fetch(`${API}/api/rooms/${roomId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) {
      const updated = await res.json();
      setRooms(prev => prev.map(r => r.id === roomId ? { ...r, status: updated.status } : r));
      onLogEntry?.(`ROOM: ${rooms.find(r => r.id === roomId)?.name} → ${status}`);
    }
    setLoading(null);
  };

  const riskColor: Record<string, string> = { high: "#f87171", medium: "#fbbf24", low: "#4ade80" };

  return (
    <div style={{ padding: "16px" }}>
      <h2 style={{ color: "#e4e4e7", fontSize: "1rem", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
        🔬 Vet Tech — Room Status Board
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: "12px" }}>
        {rooms.map((room) => {
          const cfg = STATUS_CONFIG[room.status] ?? STATUS_CONFIG.available;
          const hasAppt = !!room.appointmentProcedure;
          return (
            <div
              key={room.id}
              style={{
                background: hasAppt
                  ? `linear-gradient(160deg, ${cfg.bg}, #09090b)`
                  : "linear-gradient(160deg, #18181b, #09090b)",
                border: `1px solid ${hasAppt ? cfg.color + "40" : "rgba(63,63,70,0.6)"}`,
                borderRadius: "14px",
                padding: "14px",
                position: "relative",
                overflow: "hidden",
                transition: "border-color 0.3s ease",
              }}
            >
              {/* Status accent bar */}
              <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "3px", background: cfg.color, transition: "background 0.3s ease" }} />

              {/* Room name + status badge */}
              <div style={{ marginBottom: hasAppt ? "10px" : "8px" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#e4e4e7", marginBottom: "4px" }}>
                  {room.name}
                </div>
                <span style={{
                  display: "inline-flex", alignItems: "center", gap: "5px",
                  background: cfg.bg, color: cfg.color,
                  border: `1px solid ${cfg.color}30`, borderRadius: "12px",
                  padding: "2px 8px", fontSize: "0.68rem", fontWeight: 700,
                }}>
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: cfg.color, display: "inline-block" }} />
                  {cfg.label}
                </span>
              </div>

              {/* Appointment context — shown when occupied by schedule */}
              {hasAppt && (
                <div style={{
                  background: "rgba(0,0,0,0.25)",
                  borderRadius: "10px",
                  padding: "8px 10px",
                  marginBottom: "10px",
                  fontSize: "0.72rem",
                  borderLeft: `3px solid ${riskColor[room.riskLevel ?? "low"]}`,
                }}>
                  <div style={{ color: "#f4f4f5", fontWeight: 700, marginBottom: "3px", lineHeight: 1.3 }}>
                    {room.appointmentProcedure}
                  </div>
                  <div style={{ color: "#a1a1aa", display: "flex", flexDirection: "column", gap: "2px" }}>
                    <span>🕐 {room.appointmentTime}</span>
                    <span>👨‍⚕️ {room.appointmentVet}</span>
                    {room.riskLevel === "high" && (
                      <span style={{ color: "#f87171", fontWeight: 700 }}>⚠ High Risk</span>
                    )}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }}>
                {ACTIONS.filter(a => a.status !== room.status).map(({ status, label }) => (
                  <button
                    key={status}
                    onClick={() => updateStatus(room.id, status)}
                    disabled={loading === room.id + status}
                    style={{
                      padding: "4px 9px",
                      borderRadius: "7px",
                      fontSize: "0.63rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      border: "1px solid rgba(63,63,70,0.5)",
                      background: "rgba(39,39,42,0.6)",
                      color: "#a1a1aa",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = "#e4e4e7"; e.currentTarget.style.borderColor = "rgba(99,102,241,0.4)"; }}
                    onMouseLeave={e => { e.currentTarget.style.color = "#a1a1aa"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.5)"; }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
