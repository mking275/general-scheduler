"use client";

import { useState, useEffect } from "react";
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
import AccountPortal from "./AccountPortal";

type Role = "front_desk" | "vet_tech" | "vet" | "regional_manager" | "account_admin";

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
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const [accountBanner, setAccountBanner] = useState<{ status: string; days_remaining?: number } | null>(null);
  const allItems = scheduledItems;
  const filteredItems = applyFilters(allItems, filters);

  // Fetch account status for banner
  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";
    fetch(`${API}/api/account`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && (data.status === "trial" || data.status === "past_due")) {
          setAccountBanner({ status: data.status, days_remaining: data.trial_days_remaining });
        }
      })
      .catch(() => {});
  }, []);

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

          {/* Settings button — only shown for vet / regional; account_admin handled by role tab */}
          {(role === "vet" || role === "regional_manager") && (
            <div style={{ position: "relative" }}>
              <button
                onClick={() => setShowSettingsMenu(v => !v)}
                style={{
                  padding: "5px 10px", borderRadius: "8px",
                  background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.4)",
                  color: "#71717a", cursor: "pointer", display: "flex", alignItems: "center", gap: "5px",
                  fontSize: "0.7rem",
                }}
              >
                <Settings size={11} />
              </button>
              {showSettingsMenu && (
                <div style={{
                  position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 100,
                  background: "rgba(24,24,27,0.98)", border: "1px solid rgba(63,63,70,0.5)",
                  borderRadius: "10px", padding: "6px", minWidth: "180px",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
                }}>
                  <button
                    onClick={() => { onRoleChange("settings" as any); setShowSettingsMenu(false); }}
                    style={{
                      display: "block", width: "100%", padding: "7px 12px",
                      background: "transparent", border: "none", color: "#a1a1aa",
                      cursor: "pointer", textAlign: "left", fontSize: "0.75rem", borderRadius: "6px",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(63,63,70,0.4)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  >
                    🔌 Integrations &amp; Migration
                  </button>
                  <button
                    onClick={() => { onRoleChange("account_admin"); setShowSettingsMenu(false); }}
                    style={{
                      display: "block", width: "100%", padding: "7px 12px",
                      background: "transparent", border: "none", color: "#a1a1aa",
                      cursor: "pointer", textAlign: "left", fontSize: "0.75rem", borderRadius: "6px",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(63,63,70,0.4)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  >
                    💳 Account &amp; Billing
                  </button>
                </div>
              )}
            </div>
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

      {/* Account status banners */}
      {accountBanner?.status === "past_due" && (
        <div style={{
          background: "rgba(239,68,68,0.12)", borderBottom: "1px solid rgba(239,68,68,0.3)",
          color: "#fca5a5", padding: "6px 20px", fontSize: "0.75rem", fontWeight: 600,
          display: "flex", alignItems: "center", gap: "8px",
        }}>
          ❌ Payment past due — please update your billing information.
          <button onClick={() => onRoleChange("account_admin")} style={{
            background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.4)",
            color: "#fca5a5", borderRadius: "6px", padding: "2px 8px", cursor: "pointer",
            fontSize: "0.7rem", fontFamily: "inherit",
          }}>Manage Billing</button>
        </div>
      )}
      {accountBanner?.status === "trial" && (
        <div style={{
          background: "rgba(245,158,11,0.1)", borderBottom: "1px solid rgba(245,158,11,0.25)",
          color: "#fbbf24", padding: "6px 20px", fontSize: "0.75rem", fontWeight: 600,
          display: "flex", alignItems: "center", gap: "8px",
        }}>
          ⏳ Trial active — {accountBanner.days_remaining ?? 0} days remaining.
          <button onClick={() => onRoleChange("account_admin")} style={{
            background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.35)",
            color: "#fbbf24", borderRadius: "6px", padding: "2px 8px", cursor: "pointer",
            fontSize: "0.7rem", fontFamily: "inherit",
          }}>View Account</button>
        </div>
      )}
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

        {/* Account Admin View */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: role === "account_admin" ? 1 : 0,
            transform: role === "account_admin" ? "translateX(0)" : "translateX(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: role === "account_admin" ? "auto" : "none",
            overflow: "hidden",
          }}
        >
          <AccountPortal onBack={() => onRoleChange("front_desk")} />
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

      {/* Settings toggle button (floating) — only when not in account_admin or settings */}
      <div style={{
        position: "absolute", bottom: "16px", right: "16px", zIndex: 50,
      }}>
        {role !== ("settings" as any) && role !== "account_admin" ? (
          <button
            onClick={() => setShowSettingsMenu(v => !v)}
            title="Settings & Account"
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
