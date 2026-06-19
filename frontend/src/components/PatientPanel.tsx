"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

// ── Species icons ──────────────────────────────────────────────────────────
const SPECIES_ICON: Record<string, string> = {
  dog: "🐕",
  cat: "🐈",
  bird: "🦜",
  exotic: "🦎",
};

// ── Flag badge config ──────────────────────────────────────────────────────
const FLAG_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  alert:       { label: "ALERT",       bg: "rgba(239,68,68,0.15)",   color: "#f87171" },
  chronic:     { label: "CHRONIC",     bg: "rgba(234,179,8,0.15)",   color: "#fbbf24" },
  first_visit: { label: "FIRST VISIT", bg: "rgba(34,197,94,0.15)",   color: "#4ade80" },
};

interface Patient {
  id: string;
  name: string;
  species: string;
  breed: string;
  dob: string;
  weight_kg: number;
  flags: string[];
  flag_notes: string;
  owner_id: string;
  visit_count: number;
  last_visit_date: string | null;
  last_visit_procedure: string | null;
  owner?: { id: string; name: string; phone: string } | null;
  home_clinic_id?: string | null;
  home_clinic_name?: string | null;
}

interface PatientPanelProps {
  patient: Patient;
  expanded?: boolean;
  currentClinicId?: string;
}

export default function PatientPanel({ patient, expanded = false, currentClinicId }: PatientPanelProps) {
  const icon = SPECIES_ICON[patient.species] ?? "🐾";
  const age = patient.dob
    ? `${Math.floor((Date.now() - new Date(patient.dob).getTime()) / (1000 * 60 * 60 * 24 * 365))} yrs`
    : null;

  // T015: Cross-clinic banner condition
  const showHomeBanner =
    patient.home_clinic_id &&
    currentClinicId &&
    patient.home_clinic_id !== currentClinicId;

  return (
    <div style={{ width: "100%" }}>
      {/* T015: Cross-clinic patient banner */}
      {showHomeBanner && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 10px",
          marginBottom: "8px",
          borderRadius: "8px",
          background: "rgba(251,191,36,0.08)",
          border: "1px solid rgba(251,191,36,0.25)",
          color: "#fbbf24",
          fontSize: "0.72rem",
          fontWeight: 600,
        }}>
          🏥 Home clinic: {patient.home_clinic_name ?? patient.home_clinic_id}. Viewing full cross-location history.
        </div>
      )}
      {/* Header row: icon + name + flags */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "1.25rem" }}>{icon}</span>
        <span style={{ fontWeight: 700, color: "#f4f4f5", fontSize: "0.95rem" }}>
          {patient.name}
        </span>
        <span style={{ color: "#71717a", fontSize: "0.78rem" }}>
          {patient.breed}{age ? ` · ${age}` : ""}{" · "}{patient.weight_kg}kg
        </span>
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {patient.flags.map((flag) => {
            const cfg = FLAG_CONFIG[flag];
            if (!cfg) return null;
            return (
              <span
                key={flag}
                style={{
                  background: cfg.bg,
                  color: cfg.color,
                  border: `1px solid ${cfg.color}40`,
                  borderRadius: "4px",
                  fontSize: "0.65rem",
                  fontWeight: 700,
                  padding: "1px 6px",
                  letterSpacing: "0.05em",
                }}
              >
                {cfg.label}
              </span>
            );
          })}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div
          style={{
            marginTop: "10px",
            paddingTop: "10px",
            borderTop: "1px solid rgba(63,63,70,0.5)",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            fontSize: "0.78rem",
          }}
        >
          {patient.flag_notes && (
            <div style={{ gridColumn: "1/-1", color: "#fbbf24", background: "rgba(251,191,36,0.08)", borderRadius: "6px", padding: "6px 8px", border: "1px solid rgba(251,191,36,0.2)" }}>
              ⚠ {patient.flag_notes}
            </div>
          )}
          <div>
            <div style={{ color: "#71717a", marginBottom: "2px" }}>Owner</div>
            <div style={{ color: "#e4e4e7", fontWeight: 600 }}>{patient.owner?.name ?? "—"}</div>
            <div style={{ color: "#a1a1aa" }}>{patient.owner?.phone ?? ""}</div>
          </div>
          <div>
            <div style={{ color: "#71717a", marginBottom: "2px" }}>Visit History</div>
            <div style={{ color: "#e4e4e7" }}>{patient.visit_count} visits</div>
            {patient.last_visit_date && (
              <div style={{ color: "#a1a1aa" }}>
                Last: {patient.last_visit_date}
                {patient.last_visit_procedure ? ` · ${patient.last_visit_procedure}` : ""}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
