"use client";

import VetAppointmentCard from "./VetAppointmentCard";
import FilterBar, { FilterState, DEFAULT_FILTERS, applyFilters } from "./FilterBar";
import { useState } from "react";

interface VetViewProps {
  scheduledItems: any[];
  patientMap: Record<string, any>;
  onLogEntry?: (entry: string) => void;
  clinicColor?: string;
}

const VET_DEFAULT_FILTERS: FilterState = {
  ...DEFAULT_FILTERS,
  date: "today",
};

export default function VetView({ scheduledItems, patientMap, onLogEntry, clinicColor = "#6C63FF" }: VetViewProps) {
  const [filters, setFilters] = useState<FilterState>(VET_DEFAULT_FILTERS);
  const filteredItems = applyFilters(scheduledItems, filters);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Filter bar */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        allItems={scheduledItems}
        visibleCount={filteredItems.length}
        clinicColor={clinicColor}
      />

      {/* Appointment list */}
      <div style={{ flex: 1, padding: "16px", overflowY: "auto" }}>
        <h2 style={{
          color: "#e4e4e7", fontSize: "0.95rem", fontWeight: 700,
          marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px",
        }}>
          🩺 Vet — Appointment Queue
          <span style={{ fontSize: "0.65rem", fontWeight: 500, color: "#52525b" }}>
            Click a card to expand the clinical record
          </span>
        </h2>

        {filteredItems.length === 0 ? (
          <div style={{ color: "#52525b", textAlign: "center", padding: "40px 0", fontSize: "0.85rem" }}>
            {scheduledItems.length > 0
              ? "No appointments match the current filters."
              : "No appointments scheduled."}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {filteredItems.map((item: any, i: number) => {
              const patient = item.patient_id ? patientMap[item.patient_id] : null;
              return (
                <VetAppointmentCard
                  key={item.timeblock_id ?? item.id ?? i}
                  item={item}
                  patient={patient}
                  onLogEntry={onLogEntry}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
