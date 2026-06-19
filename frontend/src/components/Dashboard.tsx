"use client";

import { useState } from "react";
import { Calendar, Settings, WifiOff } from "lucide-react";
import AppointmentCard from "./AppointmentCard";
import RoleSelector from "./RoleSelector";
import RoomBoard from "./RoomBoard";
import VetView from "./VetView";
import ClinicSwitcher from "./ClinicSwitcher";
import RegionalManagerView from "./RegionalManagerView";
import FilterBar, { FilterState, DEFAULT_FILTERS, applyFilters } from "./FilterBar";
import IntegrationsPanel from "./IntegrationsPanel";
import DataMigrationPanel from "./DataMigrationPanel";


type Role = "front_desk" | "vet_tech" | "vet" | "regional_manager";

interface Clinic {
  id: string;
  name: string;
  color_hex: string;
  address?: string;
}

interface DashboardProps {
  scheduledItems: any[];
  patientMap: Record<string, any>;
  role: Role;
  onRoleChange: (r: Role) => void;
  onLogEntry?: (entry: string) => void;
  selectedClinic?: Clinic | null;
  onClinicChange?: (clinic: Clinic) => void;
}

export default function Dashboard({
  scheduledItems,
  patientMap,
  role,
  onRoleChange,
  onLogEntry,
  selectedClinic,
  onClinicChange,
}: DashboardProps) {

  const clinicColor = selectedClinic?.color_hex ?? "#6C63FF";
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [settingsTab, setSettingsTab] = useState<"integrations" | "migration">("integrations");
  const allItems = scheduledItems;
  const filteredItems = applyFilters(allItems, filters);


  // When regional manager drills into a clinic, switch to front_desk view
  const handleClinicSelect = (clinicId: string) => {
    if (onClinicChange) {
      // Find the clinic from the switcher data (we rely on external handler)
      onRoleChange("front_desk");
      // Signal the parent to switch to this clinic
      const fakeClinic = { id: clinicId, name: clinicId, color_hex: "#6C63FF" };
      onClinicChange(fakeClinic);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#09090b", color: "#f4f4f5", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "16px 20px 12px",
        borderBottom: "1px solid rgba(63,63,70,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
        background: "rgba(9,9,11,0.95)",
        backdropFilter: "blur(8px)",
        borderTop: `3px solid ${clinicColor}`,
        transition: "border-color 0.4s ease",
      }}>
        <div>
          <h1 style={{
            fontSize: "1.3rem",
            fontWeight: 800,
            margin: 0,
            color: clinicColor,
            transition: "color 0.4s ease",
          }}>
            {selectedClinic?.name ?? "Vet Clinic Schedule"}
          </h1>
          <p style={{ color: "#52525b", fontSize: "0.72rem", margin: "2px 0 0" }}>
            Neuro-Symbolic Agentic Dispatch System
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Clinic Switcher */}
          {onClinicChange && (
            <ClinicSwitcher
              selectedClinic={selectedClinic ?? null}
              onClinicChange={onClinicChange}
            />
          )}

          <RoleSelector role={role} onRoleChange={onRoleChange} />

          {/* Settings button — only shown for vet / regional */}
          {(role === "vet" || role === "regional_manager") && (
            <button
              onClick={() => onRoleChange("regional_manager")}
              style={{
                padding: "5px 10px", borderRadius: "8px",
                background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.4)",
                color: "#71717a", cursor: "pointer", display: "flex", alignItems: "center", gap: "5px",
                fontSize: "0.7rem",
              }}
            >
              <Settings size={11} />
            </button>
          )}

          <div style={{
            background: "rgba(16,185,129,0.08)",
            color: "#10b981",
            padding: "5px 12px",
            borderRadius: "20px",
            fontSize: "0.72rem",
            fontWeight: 600,
            border: "1px solid rgba(16,185,129,0.2)",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", display: "inline-block", animation: "pulse 2s infinite" }} />
            Online
          </div>
        </div>

      </div>

      {/* Filter bar — shown only in front_desk view */}
      {role === "front_desk" && (
        <FilterBar
          filters={filters}
          onChange={setFilters}
          allItems={allItems}
          visibleCount={filteredItems.length}
          clinicColor={clinicColor}
        />
      )}

      {/* Content area - animated role switch */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {/* Front Desk View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === "front_desk" ? 1 : 0,
            transform: role === "front_desk" ? "translateX(0)" : "translateX(-20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === "front_desk" ? "auto" : "none",
            overflow: "auto",
            padding: "16px",
          }}
        >
          {filteredItems.length === 0 ? (
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", height: "200px", border: "2px dashed rgba(63,63,70,0.4)",
              borderRadius: "16px", color: "#52525b",
            }}>
              <Calendar size={40} style={{ marginBottom: "12px", opacity: 0.5 }} />
              <p style={{ margin: 0 }}>{allItems.length > 0 ? "No appointments match the current filters." : "No appointments scheduled yet. Use the chat below to book one."}</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "12px" }}>
              {filteredItems.map((item: any, i: number) => {
                const patient = item.patient_id ? patientMap[item.patient_id] : null;
                return (
                  <AppointmentCard
                    key={item.timeblock_id ?? i}
                    item={item}
                    patient={patient}
                    role="front_desk"
                    onLogEntry={onLogEntry}
                    currentClinicId={selectedClinic?.id}
                  />
                );
              })}
            </div>
          )}
        </div>

        {/* Vet Tech View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === "vet_tech" ? 1 : 0,
            transform: role === "vet_tech" ? "translateX(0)" : "translateX(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === "vet_tech" ? "auto" : "none",
            overflow: "auto",
          }}
        >
          <RoomBoard
            onLogEntry={onLogEntry}
            clinicId={selectedClinic?.id}
            scheduledItems={scheduledItems}
          />
        </div>

        {/* Vet View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === "vet" ? 1 : 0,
            transform: role === "vet" ? "translateX(0)" : "translateX(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === "vet" ? "auto" : "none",
            overflow: "hidden",
          }}
        >
          <VetView
            scheduledItems={allItems}
            patientMap={patientMap}
            onLogEntry={onLogEntry}
            clinicColor={clinicColor}
          />
        </div>

        {/* Regional Manager View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === "regional_manager" ? 1 : 0,
            transform: role === "regional_manager" ? "translateX(0)" : "translateX(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === "regional_manager" ? "auto" : "none",
            overflow: "auto",
          }}
        >
          <RegionalManagerView onClinicSelect={handleClinicSelect} />
        </div>

        {/* Settings View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === ("settings" as any) ? 1 : 0,
            transform: role === ("settings" as any) ? "translateX(0)" : "translateX(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === ("settings" as any) ? "auto" : "none",
            overflow: "hidden",
            display: "flex", flexDirection: "column",
          }}
        >
          {/* Settings sub-tabs */}
          <div style={{
            padding: "8px 16px", borderBottom: "1px solid rgba(63,63,70,0.3)",
            display: "flex", gap: "6px", flexShrink: 0, background: "rgba(9,9,11,0.7)",
          }}>
            {(["integrations", "migration"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setSettingsTab(tab)}
                style={{
                  padding: "5px 12px", borderRadius: "7px", fontSize: "0.72rem", fontWeight: 600,
                  background: settingsTab === tab ? "rgba(129,140,248,0.15)" : "transparent",
                  border: `1px solid ${settingsTab === tab ? "rgba(129,140,248,0.35)" : "transparent"}`,
                  color: settingsTab === tab ? "#a5b4fc" : "#71717a",
                  cursor: "pointer", textTransform: "capitalize", transition: "all 0.15s ease",
                }}
              >
                {tab === "integrations" ? "🔌 Integrations" : "📦 Data Migration"}
              </button>
            ))}
          </div>

          <div style={{ flex: 1, overflowY: "auto" }}>
            {settingsTab === "integrations" && (
              <IntegrationsPanel onLog={onLogEntry} />
            )}
            {settingsTab === "migration" && (
              <DataMigrationPanel onLog={onLogEntry} />
            )}
          </div>
        </div>
      </div>

      {/* Settings toggle button (floating) */}
      <div style={{
        position: "absolute", bottom: "16px", right: "16px", zIndex: 50,
      }}>
        {role !== ("settings" as any) ? (
          <button
            onClick={() => onRoleChange("settings" as any)}
            title="Settings — Integrations &amp; Migration"
            style={{
              width: "38px", height: "38px", borderRadius: "50%",
              background: "rgba(39,39,42,0.9)", border: "1px solid rgba(63,63,70,0.6)",
              color: "#71717a", cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#a5b4fc"; e.currentTarget.style.borderColor = "rgba(129,140,248,0.5)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#71717a"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.6)"; }}
          >
            <Settings size={16} />
          </button>
        ) : (
          <button
            onClick={() => onRoleChange("front_desk")}
            style={{
              width: "38px", height: "38px", borderRadius: "50%",
              background: "rgba(129,140,248,0.15)", border: "1px solid rgba(129,140,248,0.5)",
              color: "#a5b4fc", cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
              transition: "all 0.15s ease",
            }}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
