"use client";

import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface Clinic {
  id: string;
  name: string;
  color_hex: string;
  address?: string;
  is_active?: boolean;
}

interface ClinicSwitcherProps {
  selectedClinic: Clinic | null;
  onClinicChange: (clinic: Clinic) => void;
}

export default function ClinicSwitcher({ selectedClinic, onClinicChange }: ClinicSwitcherProps) {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const selectRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    fetch(`${API}/api/clinics`)
      .then((r) => r.ok ? r.json() : [])
      .then(setClinics)
      .catch(() => {});
  }, []);

  if (clinics.length <= 1) return null;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const clinic = clinics.find((c) => c.id === e.target.value);
    if (clinic) {
      onClinicChange(clinic);
      document.body.style.setProperty("--clinic-color", clinic.color_hex);
    }
  };

  return (
    <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
      {/* Colour dot */}
      <span style={{
        position: "absolute",
        left: "10px",
        width: "9px",
        height: "9px",
        borderRadius: "50%",
        background: selectedClinic?.color_hex ?? "#6C63FF",
        boxShadow: `0 0 6px ${selectedClinic?.color_hex ?? "#6C63FF"}`,
        pointerEvents: "none",
        zIndex: 1,
      }} />

      <select
        ref={selectRef}
        id="clinic-switcher-select"
        value={selectedClinic?.id ?? ""}
        onChange={handleChange}
        style={{
          paddingLeft: "28px",
          paddingRight: "28px",
          paddingTop: "6px",
          paddingBottom: "6px",
          borderRadius: "20px",
          border: "1px solid rgba(255,255,255,0.12)",
          background: "rgba(255,255,255,0.06)",
          backdropFilter: "blur(12px)",
          cursor: "pointer",
          color: "#f4f4f5",
          fontSize: "0.78rem",
          fontWeight: 600,
          fontFamily: "inherit",
          minWidth: "180px",
          appearance: "none",
          WebkitAppearance: "none",
          outline: "none",
        }}
      >
        {clinics.map((c) => (
          <option key={c.id} value={c.id} style={{ background: "#18181b", color: "#f4f4f5" }}>
            {c.name}
          </option>
        ))}
      </select>

      {/* Chevron */}
      <span style={{
        position: "absolute",
        right: "10px",
        color: "#71717a",
        fontSize: "0.65rem",
        pointerEvents: "none",
      }}>▾</span>
    </div>
  );
}
