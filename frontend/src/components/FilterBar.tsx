"use client";

import { useMemo } from "react";

export interface FilterState {
  date: "today" | "tomorrow" | "week" | "all";
  risks: Set<string>;
  types: Set<string>;
  statuses: Set<string>;
}

export const DEFAULT_FILTERS: FilterState = {
  date: "today",
  risks: new Set(),
  types: new Set(),
  statuses: new Set(),
};

interface FilterBarProps {
  filters: FilterState;
  onChange: (f: FilterState) => void;
  allItems: any[];
  visibleCount: number;
  clinicColor?: string;
}

const RISK_OPTS = [
  { key: "high",   label: "⚠ High",   color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.35)" },
  { key: "medium", label: "▲ Medium", color: "#fbbf24", bg: "rgba(251,191,36,0.12)",  border: "rgba(251,191,36,0.35)"  },
  { key: "low",    label: "✓ Low",    color: "#4ade80", bg: "rgba(74,222,128,0.12)",  border: "rgba(74,222,128,0.35)"  },
];

const STATUS_OPTS = [
  { key: "alert",       label: "🔴 Alert",       color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.3)" },
  { key: "chronic",     label: "⚡ Chronic",     color: "#a78bfa", bg: "rgba(167,139,250,0.12)", border: "rgba(167,139,250,0.3)" },
  { key: "first_visit", label: "✨ First Visit", color: "#34d399", bg: "rgba(52,211,153,0.12)",  border: "rgba(52,211,153,0.3)"  },
];

const DATE_OPTS = [
  { key: "today",    label: "Today"     },
  { key: "tomorrow", label: "Tomorrow"  },
  { key: "week",     label: "This Week" },
  { key: "all",      label: "All"       },
] as const;

function localDateKey(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function applyFilters(items: any[], filters: FilterState): any[] {
  const today = new Date(); today.setHours(0,0,0,0);
  const todayKey = localDateKey(today);
  const tomorrowKey = localDateKey(new Date(today.getTime() + 86400000));
  const weekStart = localDateKey(today);
  const weekEnd   = localDateKey(new Date(today.getTime() + 6 * 86400000));

  return items.filter(item => {
    const dateKey = (item.start_time ?? "").slice(0, 10);

    // -- Date filter --
    if (filters.date === "today"    && dateKey !== todayKey) return false;
    if (filters.date === "tomorrow" && dateKey !== tomorrowKey) return false;
    if (filters.date === "week"     && (dateKey < weekStart || dateKey > weekEnd)) return false;

    // -- Risk filter --
    if (filters.risks.size > 0 && !filters.risks.has(item.risk_level)) return false;

    // -- Type filter (procedure specialty) --
    if (filters.types.size > 0) {
      const proc = item.job?.procedure ?? "";
      const matched = [...filters.types].some(t => proc.toLowerCase().includes(t.toLowerCase())
        || (item.resources ?? []).some((r: any) => (r.hard_skills ?? []).some((s: string) => s.toLowerCase() === t.toLowerCase())));
      if (!matched) return false;
    }

    // -- Status filter --
    if (filters.statuses.size > 0) {
      const patientData = item.patient ?? {};
      const hasAlert   = patientData.is_alert   ?? patientData.alert   ?? false;
      const hasChronic = patientData.is_chronic  ?? patientData.chronic ?? false;
      const isFirst    = patientData.is_first_visit ?? patientData.first_visit ?? false;
      const statusMap: Record<string, boolean> = {
        alert: hasAlert, chronic: hasChronic, first_visit: isFirst,
      };
      if (![...filters.statuses].some(s => statusMap[s])) return false;
    }

    return true;
  });
}

export function deriveTypeOptions(items: any[]): string[] {
  const skillSet = new Set<string>();
  items.forEach(item => {
    (item.resources ?? []).forEach((r: any) => {
      (r.hard_skills ?? []).forEach((s: string) => skillSet.add(s));
    });
  });
  const priority = ["Surgery","Dental","Avian","Exotics","Grooming","Vaccination","Ultrasound","X-Ray","General Practice"];
  return priority.filter(p => skillSet.has(p));
}

export default function FilterBar({ filters, onChange, allItems, visibleCount, clinicColor = "#6C63FF" }: FilterBarProps) {
  const typeOpts = useMemo(() => deriveTypeOptions(allItems), [allItems]);
  const totalCount = allItems.length;
  const hasActive = filters.date !== "all" || filters.risks.size > 0 || filters.types.size > 0 || filters.statuses.size > 0;
  const isDefaultDate = filters.date === "today";

  function toggleSet(set: Set<string>, key: string): Set<string> {
    const next = new Set(set);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  }

  const ROW_STYLE: React.CSSProperties = {
    display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap",
  };
  const LABEL_STYLE: React.CSSProperties = {
    fontSize: "0.6rem", fontWeight: 700, color: "#52525b",
    textTransform: "uppercase", letterSpacing: "0.07em",
    minWidth: "46px", flexShrink: 0,
  };

  function Pill({ label, active, color, bg, border, onClick }: {
    label: string; active: boolean;
    color?: string; bg?: string; border?: string;
    onClick: () => void;
  }) {
    const activeColor = color ?? clinicColor;
    const activeBg    = bg    ?? `${clinicColor}22`;
    const activeBorder = border ?? `${clinicColor}55`;
    return (
      <button
        onClick={onClick}
        style={{
          padding: "3px 10px",
          borderRadius: "20px",
          fontSize: "0.65rem",
          fontWeight: active ? 700 : 500,
          cursor: "pointer",
          border: `1px solid ${active ? activeBorder : "rgba(63,63,70,0.45)"}`,
          background: active ? activeBg : "rgba(24,24,27,0.6)",
          color: active ? activeColor : "#71717a",
          transition: "all 0.15s ease",
          whiteSpace: "nowrap",
          outline: "none",
        }}
        onMouseEnter={e => { if (!active) { e.currentTarget.style.borderColor = activeBorder; e.currentTarget.style.color = "#a1a1aa"; }}}
        onMouseLeave={e => { if (!active) { e.currentTarget.style.borderColor = "rgba(63,63,70,0.45)"; e.currentTarget.style.color = "#71717a"; }}}
      >
        {label}
      </button>
    );
  }

  return (
    <div style={{
      padding: "10px 16px",
      background: "rgba(9,9,11,0.8)",
      borderBottom: "1px solid rgba(63,63,70,0.35)",
      display: "flex",
      flexDirection: "column",
      gap: "7px",
      flexShrink: 0,
      backdropFilter: "blur(4px)",
    }}>
      {/* Date row */}
      <div style={ROW_STYLE}>
        <span style={LABEL_STYLE}>Date</span>
        {DATE_OPTS.map(opt => (
          <Pill
            key={opt.key}
            label={opt.label}
            active={filters.date === opt.key}
            color={clinicColor}
            bg={`${clinicColor}22`}
            border={`${clinicColor}55`}
            onClick={() => onChange({ ...filters, date: opt.key })}
          />
        ))}
      </div>

      {/* Risk row */}
      <div style={ROW_STYLE}>
        <span style={LABEL_STYLE}>Risk</span>
        {RISK_OPTS.map(opt => (
          <Pill
            key={opt.key}
            label={opt.label}
            active={filters.risks.has(opt.key)}
            color={opt.color}
            bg={opt.bg}
            border={opt.border}
            onClick={() => onChange({ ...filters, risks: toggleSet(filters.risks, opt.key) })}
          />
        ))}
      </div>

      {/* Type row */}
      {typeOpts.length > 0 && (
        <div style={ROW_STYLE}>
          <span style={LABEL_STYLE}>Type</span>
          {typeOpts.map(t => (
            <Pill
              key={t}
              label={t}
              active={filters.types.has(t)}
              color={clinicColor}
              bg={`${clinicColor}1a`}
              border={`${clinicColor}44`}
              onClick={() => onChange({ ...filters, types: toggleSet(filters.types, t) })}
            />
          ))}
        </div>
      )}

      {/* Status row */}
      <div style={{ ...ROW_STYLE, justifyContent: "space-between" }}>
        <div style={ROW_STYLE}>
          <span style={LABEL_STYLE}>Flag</span>
          {STATUS_OPTS.map(opt => (
            <Pill
              key={opt.key}
              label={opt.label}
              active={filters.statuses.has(opt.key)}
              color={opt.color}
              bg={opt.bg}
              border={opt.border}
              onClick={() => onChange({ ...filters, statuses: toggleSet(filters.statuses, opt.key) })}
            />
          ))}
        </div>

        {/* Count + clear */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginLeft: "auto" }}>
          <span style={{ fontSize: "0.65rem", color: hasActive ? "#a1a1aa" : "#52525b", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
            {hasActive ? (
              <><span style={{ color: clinicColor, fontWeight: 700 }}>{visibleCount}</span> of {totalCount}</>
            ) : (
              <span>{totalCount} appointments</span>
            )}
          </span>
          {hasActive && (
            <button
              onClick={() => onChange({ date: "all", risks: new Set(), types: new Set(), statuses: new Set() })}
              style={{
                padding: "2px 9px", borderRadius: "12px", fontSize: "0.62rem",
                fontWeight: 600, cursor: "pointer",
                border: "1px solid rgba(99,102,241,0.3)",
                background: "rgba(99,102,241,0.08)",
                color: "#818cf8", transition: "all 0.15s ease",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(99,102,241,0.15)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(99,102,241,0.08)"; }}
            >
              Clear ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
