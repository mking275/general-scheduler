"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface Props {
  onClinicSelect: (clinicId: string) => void;
  allTimeblocks?: any[];
  clinics?: any[];
}

// -- helpers ------------------------------------------------------------------

function isWeekday(d: Date) {
  const day = d.getDay();
  return day !== 0 && day !== 6;
}

function addWeekdays(start: Date, n: number, direction: 1 | -1): Date[] {
  const days: Date[] = [];
  const cur = new Date(start);
  cur.setHours(0, 0, 0, 0);
  while (days.length < n) {
    cur.setDate(cur.getDate() + direction);
    if (isWeekday(cur)) days.push(new Date(cur));
  }
  return days;
}

function build12WeekWindow(): Date[] {
  // Align to full ISO weeks (Mon-Fri), starting from Monday 3 weeks ago
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  // Find Monday of current week (JS getDay: 0=Sun, 1=Mon...6=Sat)
  const dow = today.getDay();
  const daysToMon = dow === 0 ? -6 : 1 - dow;
  const thisMonday = new Date(today);
  thisMonday.setDate(today.getDate() + daysToMon);
  // Start 3 full weeks back
  const startMonday = new Date(thisMonday);
  startMonday.setDate(thisMonday.getDate() - 21);
  // Enumerate exactly 12 weeks x 5 days
  const days: Date[] = [];
  for (let week = 0; week < 12; week++) {
    for (let d = 0; d < 5; d++) {
      const day = new Date(startMonday);
      day.setDate(startMonday.getDate() + week * 7 + d);
      day.setHours(0, 0, 0, 0);
      days.push(day);
    }
  }
  return days;
}

function fmtDateKey(d: Date): string {
  // Use local date to avoid UTC-offset mismatch with stored ISO strings
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtShortLabel(d: Date): string {
  const days = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
  return `${days[d.getDay()]} ${d.getDate()}`;
}

function fmtWeekOf(d: Date): string {
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `Week of ${months[d.getMonth()]} ${d.getDate()}`;
}

function isoWeekKey(d: Date): string {
  // Returns "YYYY-Www" using Monday-based week
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayOfWeek = tmp.getUTCDay() || 7; // Mon=1 … Sun=7
  tmp.setUTCDate(tmp.getUTCDate() + 4 - dayOfWeek); // Thursday of this week
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${tmp.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

function groupByWeek(days: Date[]): Date[][] {
  const weeks: Date[][] = [];
  let cur: Date[] = [];
  let lastKey = "";
  days.forEach(d => {
    const key = isoWeekKey(d);
    if (key !== lastKey && cur.length > 0) {
      weeks.push(cur);
      cur = [];
    }
    cur.push(d);
    lastKey = key;
  });
  if (cur.length > 0) weeks.push(cur);
  return weeks;
}

function cellBg(count: number): string {
  if (count === 0) return "rgba(63,63,70,0.2)";
  if (count <= 5) return "rgba(16,185,129,0.15)";
  if (count <= 12) return "rgba(251,191,36,0.2)";
  return "rgba(239,68,68,0.2)";
}

function cellBorder(count: number): string {
  if (count === 0) return "rgba(63,63,70,0.4)";
  if (count <= 5) return "rgba(16,185,129,0.3)";
  if (count <= 12) return "rgba(251,191,36,0.4)";
  return "rgba(239,68,68,0.5)";
}

// -- sub-components ---------------------------------------------------------

function SkeletonCard() {
  return (
    <div style={{
      flex: "1 1 260px",
      background: "linear-gradient(160deg,#1a1a1e 0%,#111114 100%)",
      border: "1px solid rgba(63,63,70,0.5)",
      borderRadius: "20px",
      padding: "24px",
      display: "flex",
      flexDirection: "column",
      gap: "16px",
    }}>
      {[80, 50, 100, 40, 60].map((w, i) => (
        <div key={i} style={{
          height: i === 2 ? "8px" : "16px",
          width: `${w}%`,
          background: "rgba(63,63,70,0.4)",
          borderRadius: "8px",
          animation: "rmv-pulse 1.5s ease-in-out infinite",
        }} />
      ))}
    </div>
  );
}

function MiniSparkBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
      <div style={{
        width: "18px",
        height: "36px",
        background: "rgba(63,63,70,0.3)",
        borderRadius: "4px",
        overflow: "hidden",
        display: "flex",
        alignItems: "flex-end",
      }}>
        <div style={{
          width: "100%",
          height: `${pct}%`,
          background: color,
          borderRadius: "3px",
          transition: "height 0.5s ease",
        }} />
      </div>
      <span style={{ fontSize: "0.6rem", color: "#71717a", fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );
}

function UtilBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: "6px", background: "rgba(63,63,70,0.4)", borderRadius: "4px", overflow: "hidden" }}>
      <div style={{
        height: "100%",
        width: `${Math.min(pct, 100)}%`,
        background: `linear-gradient(90deg,${color} 0%,${color}99 100%)`,
        borderRadius: "4px",
        transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)",
      }} />
    </div>
  );
}

// -- main component --------------------------------------------------------

export default function RegionalManagerView({ onClinicSelect, allTimeblocks: propBlocks, clinics: propClinics }: Props) {
  const [timeblocks, setTimeblocks] = useState<any[]>(propBlocks ?? []);
  const [clinics, setClinics] = useState<any[]>(propClinics ?? []);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [expandedClinics, setExpandedClinics] = useState<Set<string>>(new Set());

  // Fetch data on mount
  useEffect(() => {
    let cancelled = false;
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [cRes, tbRes] = await Promise.all([
          fetch(`${API}/api/clinics`),
          fetch(`${API}/api/timeblocks`),
        ]);
        if (cancelled) return;
        if (cRes.ok) {
          const data = await cRes.json();
          if (!cancelled) setClinics(data);
        }
        if (tbRes.ok) {
          const data = await tbRes.json();
          if (!cancelled) setTimeblocks(data);
        }
      } catch { /* non-fatal */ }
      if (!cancelled) setLoading(false);
    };
    fetchAll();
    return () => { cancelled = true; };
  }, []);

  // Use prop overrides if provided
  useEffect(() => { if (propBlocks) setTimeblocks(propBlocks); }, [propBlocks]);
  useEffect(() => { if (propClinics) setClinics(propClinics); }, [propClinics]);

  const window3w = build12WeekWindow();
  const today = fmtDateKey(new Date());
  const weekGroups = groupByWeek(window3w);

  const toggleExpand = useCallback((id: string) => {
    setExpandedClinics(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Per-day, per-clinic stats
  const dayClinicStats = useCallback((dateKey: string, clinicId: string) => {
    const tbs = timeblocks.filter(tb => {
      const tbDate = (tb.start_time ?? tb.date ?? "").slice(0, 10);
      return tbDate === dateKey && (tb.clinic_id === clinicId || !tb.clinic_id);
    });
    const highRisk = tbs.filter(tb => tb.risk_level === "high");
    const procedures: string[] = tbs.map((tb: any) => tb.job?.procedure ?? "").filter(Boolean);
    const vets: string[] = [];
    tbs.forEach((tb: any) => {
      (tb.resources ?? []).forEach((r: any) => { if (r.type === "Vet") vets.push(r.name); });
    });
    const uniqueVets = [...new Set(vets)];
    const vetCount = uniqueVets.length || 1;
    const util = Math.min((tbs.length / (vetCount * 18)) * 100, 100);
    return { count: tbs.length, highRisk: highRisk.length, procedures, uniqueVets, util, tbs };
  }, [timeblocks]);

  // Weekly stats for a clinic (Mon–Fri of a given ISO week index)
  const weeklyForClinic = useCallback((clinic: any, weekDays: Date[]) => {
    return weekDays.map(d => dayClinicStats(fmtDateKey(d), clinic.id));
  }, [dayClinicStats]);

  // Summary stats across all clinics for selected week
  const selectedWeekDays = weekGroups.find(wg => wg.some(d => fmtDateKey(d) === (selectedDate ?? today))) ?? weekGroups[weekGroups.findIndex(wg => wg.some(d => fmtDateKey(d) === today))];

  const summaryStats = () => {
    let totalAppts = 0;
    let totalUtil = 0;
    let totalHighRisk = 0;
    const patientClinicMap: Record<string, Set<string>> = {};

    clinics.forEach(clinic => {
      (selectedWeekDays ?? []).forEach(d => {
        const s = dayClinicStats(fmtDateKey(d), clinic.id);
        totalAppts += s.count;
        totalUtil += s.util;
        totalHighRisk += s.highRisk;
        s.tbs.forEach((tb: any) => {
          if (tb.patient_id) {
            if (!patientClinicMap[tb.patient_id]) patientClinicMap[tb.patient_id] = new Set();
            patientClinicMap[tb.patient_id].add(clinic.id);
          }
        });
      });
    });
    const crossClinic = Object.values(patientClinicMap).filter(s => s.size > 1).length;
    const avgUtil = clinics.length > 0 ? totalUtil / clinics.length : 0;
    return { totalAppts, avgUtil, totalHighRisk, crossClinic };
  };

  // High-risk in next 14 days
  const next14Days = window3w.filter(d => fmtDateKey(d) >= today);
  const allHighRisk = next14Days.flatMap(d => {
    return timeblocks
      .filter(tb => {
        const tbDate = (tb.start_time ?? tb.date ?? "").slice(0, 10);
        return tbDate === fmtDateKey(d) && tb.risk_level === "high";
      })
      .map(tb => ({ ...tb, _date: fmtDateKey(d) }));
  });

  // Get vet name for a timeblock
  const getVetName = (tb: any) => {
    const vetRes = (tb.resources ?? []).find((r: any) => r.type === "Vet");
    return vetRes?.name ?? "—";
  };

  const stats = loading ? null : summaryStats();

  // Find a clinic by id
  const clinicById = (id: string) => clinics.find(c => c.id === id);

  return (
    <>
      <style>{`
        @keyframes rmv-pulse {
          0%,100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        .rmv-card-expand {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.5s cubic-bezier(0.4,0,0.2,1);
        }
        .rmv-card-expand.open {
          max-height: 2000px;
        }
        .rmv-day-cell:hover {
          transform: translateY(-2px);
        }
        .rmv-clinic-card:hover {
          box-shadow: 0 12px 40px rgba(0,0,0,0.4) !important;
        }
        .rmv-go-btn:hover {
          opacity: 0.85;
        }
      `}</style>

      <div style={{ padding: "20px", height: "100%", overflowY: "auto", overflowX: "hidden", boxSizing: "border-box" }}>
        {/* -- Header ---------------------------------------------------- */}
        <div style={{ marginBottom: "16px" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800, color: "#f4f4f5", display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "1.2rem" }}>🗺️</span>
            Regional Overview
          </h2>
          <p style={{ margin: "4px 0 0", color: "#52525b", fontSize: "0.75rem" }}>
            12-week appointment load · click a day cell to inspect · click a card to expand
          </p>
        </div>

        {/* -- Summary stats bar ------------------------------------------ */}
        {!loading && stats && (
          <div style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            marginBottom: "16px",
            padding: "12px 16px",
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(63,63,70,0.4)",
            borderRadius: "14px",
          }}>
            {[
              { label: "Total appts", value: stats.totalAppts, color: "#a5b4fc" },
              { label: "Avg utilisation", value: `${stats.avgUtil.toFixed(1)}%`, color: "#34d399" },
              { label: "High-risk", value: stats.totalHighRisk, color: stats.totalHighRisk > 0 ? "#f87171" : "#52525b" },
              { label: "Cross-clinic patients", value: stats.crossClinic, color: "#fbbf24" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: "100px" }}>
                <span style={{ fontSize: "0.67rem", color: "#71717a", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</span>
                <span style={{ fontSize: "1.3rem", fontWeight: 800, color, fontVariantNumeric: "tabular-nums" }}>{value}</span>
              </div>
            ))}
          </div>
        )}

        {/* -- Timeline: 3 blocks of 4 weeks, side by side -------------- */}
        {!loading && (() => {
          // Slice weekGroups into 3 blocks of 4 weeks each
          const allWeeks = weekGroups.slice(0, 12);
          const blocks = [allWeeks.slice(0, 4), allWeeks.slice(4, 8), allWeeks.slice(8, 12)];
          return (
          <div style={{ display: "flex", gap: "20px", marginBottom: "20px", justifyContent: "space-between" }}>
            {blocks.map((block, bi) => (
              <div key={bi} style={{ flex: "1 1 0", minWidth: 0 }}>
                {block.map((wg, wi) => (
                  <div key={wi} style={{ marginBottom: "6px" }}>
                    <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "#52525b", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      {fmtWeekOf(wg[0])}
                    </div>
                    <div style={{ display: "flex", gap: "3px" }}>
                      {wg.map(d => {
                        const dk = fmtDateKey(d);
                        const isPast = dk < today;
                        const isToday = dk === today;
                        const isSelected = selectedDate === dk;
                        const totalCount = clinics.reduce((acc, c) => acc + dayClinicStats(dk, c.id).count, 0);
                        return (
                          <div
                            key={dk}
                            className="rmv-day-cell"
                            onClick={() => setSelectedDate(isSelected ? null : dk)}
                            title={`${dk}: ${totalCount} appointments`}
                            style={{
                              flex: "1 1 0",
                              padding: "5px 2px",
                              borderRadius: "7px",
                              background: cellBg(totalCount),
                              border: isSelected
                                ? "2px solid #a5b4fc"
                                : isToday
                                ? "2px solid rgba(165,180,252,0.7)"
                                : `1px solid ${cellBorder(totalCount)}`,
                              cursor: "pointer",
                              textAlign: "center",
                              opacity: isPast && !isToday ? 0.55 : 1,
                              transition: "all 0.18s ease",
                              userSelect: "none",
                              boxSizing: "border-box",
                            }}
                          >
                            <div style={{ fontSize: "0.58rem", color: "#71717a", fontWeight: 600, lineHeight: 1.2 }}>{fmtShortLabel(d)}</div>
                            <div style={{ fontSize: "0.9rem", fontWeight: 800, color: "#f4f4f5", fontVariantNumeric: "tabular-nums", lineHeight: 1.3 }}>{totalCount}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          );
        })()}


        {/* -- Clinic cards ----------------------------------------------- */}
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "24px" }}>
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : clinics.length === 0 ? (
            <div style={{ color: "#52525b", fontSize: "0.82rem", padding: "20px" }}>No clinics found.</div>
          ) : (
            clinics.map(clinic => {
              const color = clinic.color_hex ?? "#6C63FF";
              const isExpanded = expandedClinics.has(clinic.id);

              const displayDate = selectedDate ?? today;
              const todayStats = dayClinicStats(displayDate, clinic.id);

              // current week days
              const currentWeekDays = weekGroups.find(wg => wg.some(d => fmtDateKey(d) === (selectedDate ?? today))) ?? [];
              const nextWeekIdx = weekGroups.findIndex(wg => wg.some(d => fmtDateKey(d) === (selectedDate ?? today)));
              const nextWeekDays = weekGroups[nextWeekIdx + 1] ?? [];

              const thisWeekStats = weeklyForClinic(clinic, currentWeekDays);
              const nextWeekStats = weeklyForClinic(clinic, nextWeekDays);
              const maxThisWeek = Math.max(...thisWeekStats.map(s => s.count), 1);
              const maxNextWeek = Math.max(...nextWeekStats.map(s => s.count), 1);

              // sparkline (last 7 weekdays)
              const past7 = window3w.slice(0, 7);
              const sparkStats = past7.map(d => dayClinicStats(fmtDateKey(d), clinic.id));
              const maxSpark = Math.max(...sparkStats.map(s => s.count), 1);

              // vet utilisation for the selected date
              const vetCounts: Record<string, number> = {};
              todayStats.uniqueVets.forEach(v => { vetCounts[v] = 0; });
              todayStats.tbs.forEach((tb: any) => {
                (tb.resources ?? []).forEach((r: any) => {
                  if (r.type === "Vet" && r.name) {
                    vetCounts[r.name] = (vetCounts[r.name] ?? 0) + 1;
                  }
                });
              });
              const maxVetCount = Math.max(...Object.values(vetCounts), 1);

              // procedure breakdown
              const procMap: Record<string, number> = {};
              todayStats.procedures.forEach(p => { procMap[p] = (procMap[p] ?? 0) + 1; });
              const topProcs = Object.entries(procMap).sort((a, b) => b[1] - a[1]).slice(0, 5);

              // high-risk in next 14
              const clinicHighRisk = allHighRisk.filter(tb => tb.clinic_id === clinic.id || (!tb.clinic_id && clinics.length === 1));

              return (
                <div
                  key={clinic.id}
                  className="rmv-clinic-card"
                  style={{
                    flex: "1 1 280px",
                    background: "linear-gradient(160deg,#1a1a1e 0%,#111114 100%)",
                    border: `1px solid ${color}33`,
                    borderRadius: "20px",
                    overflow: "hidden",
                    transition: "box-shadow 0.2s ease, border-color 0.2s ease",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = `${color}66`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = `${color}33`; }}
                >
                  {/* Card header – click to expand */}
                  <div
                    onClick={() => toggleExpand(clinic.id)}
                    style={{
                      padding: "18px 20px 14px",
                      background: `linear-gradient(135deg,${color}22 0%,${color}08 100%)`,
                      borderBottom: `1px solid ${color}22`,
                      cursor: "pointer",
                      userSelect: "none",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, boxShadow: `0 0 8px ${color}88`, flexShrink: 0 }} />
                        <h3 style={{ margin: 0, fontSize: "0.9rem", fontWeight: 800, color: "#f4f4f5" }}>{clinic.name}</h3>
                      </div>
                      <span style={{ color: "#52525b", fontSize: "0.75rem", transition: "transform 0.3s", display: "inline-block", transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)" }}>▾</span>
                    </div>
                    <div style={{ marginTop: "8px", display: "flex", alignItems: "baseline", gap: "10px" }}>
                      <span style={{ fontSize: "2.8rem", fontWeight: 900, color, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{todayStats.count}</span>
                      <span style={{ color: "#71717a", fontSize: "0.78rem" }}>appts · {todayStats.util.toFixed(0)}% util</span>
                    </div>
                  </div>

                  {/* Collapsed body */}
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                    {/* Util bar */}
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                        <span style={{ color: "#a1a1aa", fontSize: "0.71rem", fontWeight: 600 }}>Utilisation</span>
                        <span style={{ color, fontSize: "0.71rem", fontWeight: 700 }}>{todayStats.util.toFixed(1)}%</span>
                      </div>
                      <UtilBar pct={todayStats.util} color={color} />
                    </div>

                    {/* High-risk badge */}
                    <div style={{
                      display: "inline-flex", alignItems: "center", gap: "5px",
                      padding: "4px 10px", borderRadius: "10px",
                      background: todayStats.highRisk > 0 ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.08)",
                      border: `1px solid ${todayStats.highRisk > 0 ? "rgba(239,68,68,0.3)" : "rgba(16,185,129,0.2)"}`,
                      color: todayStats.highRisk > 0 ? "#f87171" : "#10b981",
                      fontSize: "0.72rem", fontWeight: 700, alignSelf: "flex-start",
                    }}>
                      {todayStats.highRisk > 0 ? "⚠" : "✓"}
                      {todayStats.highRisk > 0 ? ` ${todayStats.highRisk} high-risk` : " No high-risk"}
                    </div>

                    {/* Sparkline */}
                    <div>
                      <div style={{ fontSize: "0.66rem", color: "#52525b", marginBottom: "4px", fontWeight: 600 }}>Last 7 days</div>
                      <div style={{ display: "flex", gap: "4px", alignItems: "flex-end" }}>
                        {sparkStats.map((s, i) => (
                          <MiniSparkBar key={i} value={s.count} max={maxSpark} color={color} />
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Expandable section */}
                  <div className={`rmv-card-expand${isExpanded ? " open" : ""}`}>
                    <div style={{ padding: "0 20px 18px", display: "flex", flexDirection: "column", gap: "18px" }}>
                      <div style={{ height: "1px", background: `${color}22` }} />

                      {/* a. This week day-by-day */}
                      {currentWeekDays.length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#a1a1aa", fontWeight: 700, marginBottom: "8px" }}>This week</div>
                          <div style={{ display: "flex", gap: "6px", alignItems: "flex-end" }}>
                            {currentWeekDays.map((d, i) => (
                              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
                                <MiniSparkBar value={thisWeekStats[i]?.count ?? 0} max={maxThisWeek} color={color} />
                                <span style={{ fontSize: "0.58rem", color: "#52525b" }}>{fmtShortLabel(d)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* b. Next week preview */}
                      {nextWeekDays.length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#a1a1aa", fontWeight: 700, marginBottom: "8px" }}>Next week</div>
                          <div style={{ display: "flex", gap: "6px", alignItems: "flex-end" }}>
                            {nextWeekDays.map((d, i) => (
                              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
                                <MiniSparkBar value={nextWeekStats[i]?.count ?? 0} max={maxNextWeek} color={color} />
                                <span style={{ fontSize: "0.58rem", color: "#52525b" }}>{fmtShortLabel(d)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* c. Staff utilisation */}
                      {Object.keys(vetCounts).length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#a1a1aa", fontWeight: 700, marginBottom: "8px" }}>Staff utilisation</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                            {Object.entries(vetCounts).map(([name, cnt]) => (
                              <div key={name} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <span style={{ fontSize: "0.72rem", color: "#d4d4d8", width: "90px", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
                                <div style={{ flex: 1, height: "5px", background: "rgba(63,63,70,0.4)", borderRadius: "3px", overflow: "hidden" }}>
                                  <div style={{ height: "100%", width: `${(cnt / maxVetCount) * 100}%`, background: color, borderRadius: "3px" }} />
                                </div>
                                <span style={{ fontSize: "0.68rem", color: "#71717a", fontVariantNumeric: "tabular-nums", width: "20px", textAlign: "right" }}>{cnt}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* d. Procedure breakdown */}
                      {topProcs.length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#a1a1aa", fontWeight: 700, marginBottom: "8px" }}>Top procedures</div>
                          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                            {topProcs.map(([proc, cnt]) => (
                              <span key={proc} style={{
                                display: "inline-flex", alignItems: "center", gap: "5px",
                                padding: "3px 9px", borderRadius: "8px",
                                background: `${color}18`, border: `1px solid ${color}33`,
                                color: "#d4d4d8", fontSize: "0.68rem",
                              }}>
                                {proc}
                                <span style={{ background: color, color: "#09090b", borderRadius: "6px", padding: "0 5px", fontSize: "0.62rem", fontWeight: 800 }}>{cnt}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* e. High-risk watch list */}
                      {clinicHighRisk.length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#f87171", fontWeight: 700, marginBottom: "8px" }}>⚠ High-risk watch list</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            {clinicHighRisk.map((tb, i) => (
                              <div key={i} style={{
                                display: "flex", alignItems: "center", gap: "8px",
                                padding: "6px 10px", borderRadius: "8px",
                                background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)",
                                fontSize: "0.7rem",
                              }}>
                                <span style={{ color: "#52525b", flexShrink: 0 }}>{tb._date}</span>
                                <span style={{ color: "#d4d4d8", flex: 1 }}>{tb.procedure ?? tb.service_type ?? "—"}</span>
                                <span style={{ color: "#71717a", flexShrink: 0 }}>{getVetName(tb)}</span>
                                <span style={{
                                  background: "rgba(239,68,68,0.2)", color: "#f87171",
                                  borderRadius: "5px", padding: "1px 6px", fontSize: "0.62rem", fontWeight: 700,
                                }}>HIGH</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* f. Go to schedule button */}
                      <button
                        className="rmv-go-btn"
                        onClick={e => { e.stopPropagation(); onClinicSelect(clinic.id); }}
                        style={{
                          padding: "10px 18px",
                          borderRadius: "10px",
                          background: `linear-gradient(135deg,${color} 0%,${color}cc 100%)`,
                          color: "#09090b",
                          fontWeight: 800,
                          fontSize: "0.78rem",
                          border: "none",
                          cursor: "pointer",
                          transition: "opacity 0.2s",
                          alignSelf: "flex-start",
                        }}
                      >
                        → Go to schedule
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* -- Global High-Risk Watch Panel ------------------------------- */}
        {!loading && allHighRisk.length > 0 && (
          <div style={{
            padding: "18px 20px",
            background: "rgba(239,68,68,0.05)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "16px",
            marginBottom: "20px",
          }}>
            <h3 style={{ margin: "0 0 14px", fontSize: "0.85rem", fontWeight: 700, color: "#f87171", display: "flex", alignItems: "center", gap: "6px" }}>
              ⚠ High-Risk Watch — Next 14 Days
              <span style={{ background: "rgba(239,68,68,0.2)", color: "#f87171", borderRadius: "8px", padding: "1px 8px", fontSize: "0.7rem" }}>{allHighRisk.length}</span>
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {allHighRisk.map((tb, i) => {
                const clinic = clinicById(tb.clinic_id);
                const clColor = clinic?.color_hex ?? "#6C63FF";
                const procedure = tb.job?.procedure ?? "—";
                const vetName = getVetName(tb);
                const patName = tb.job?.patient_name ?? null;
                const startFmt = tb.start_time
                  ? new Date(tb.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : null;
                const isToday2 = tb._date === today;
                const tomorrowKey = (() => {
                  const t = new Date(); t.setDate(t.getDate() + 1);
                  return fmtDateKey(t);
                })();
                const isTmrw = tb._date === tomorrowKey;
                const urgencyLabel = isToday2 ? "Today" : isTmrw ? "Tomorrow" : "Upcoming";
                const urgencyColor = isToday2 ? "#f87171" : isTmrw ? "#fbbf24" : "#a1a1aa";
                return (
                  <div key={i} style={{
                    display: "grid",
                    gridTemplateColumns: "88px 8px 1fr auto auto",
                    alignItems: "center", gap: "10px",
                    padding: "8px 14px", borderRadius: "10px",
                    background: isToday2 ? "rgba(239,68,68,0.06)" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${isToday2 ? "rgba(239,68,68,0.22)" : "rgba(63,63,70,0.3)"}`,
                    fontSize: "0.72rem",
                  }}>
                    {/* Date + time */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
                      <span style={{ fontWeight: 700, color: urgencyColor }}>{urgencyLabel}</span>
                      <span style={{ color: "#52525b", fontSize: "0.63rem" }}>
                        {isToday2 || isTmrw ? tb._date : tb._date}
                        {startFmt && ` · ${startFmt}`}
                      </span>
                    </div>

                    {/* Clinic colour dot */}
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: clColor, boxShadow: `0 0 5px ${clColor}88`, flexShrink: 0 }} />

                    {/* Procedure + patient + clinic */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
                      <span style={{ color: "#f4f4f5", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {procedure}
                        {patName && <span style={{ color: "#71717a", fontWeight: 400 }}> · {patName}</span>}
                      </span>
                      <span style={{ color: "#52525b" }}>{vetName} · {clinic?.name ?? "—"}</span>
                    </div>

                    {/* Urgency badge */}
                    <span style={{
                      background: `${urgencyColor}18`, color: urgencyColor,
                      border: `1px solid ${urgencyColor}40`,
                      borderRadius: "6px", padding: "2px 8px",
                      fontSize: "0.63rem", fontWeight: 700, flexShrink: 0, whiteSpace: "nowrap",
                    }}>
                      ⚠ {urgencyLabel}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
