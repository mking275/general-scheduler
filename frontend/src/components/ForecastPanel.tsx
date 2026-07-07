"use client";

import { useState, useEffect, useCallback } from "react";
import { TrendingUp, TrendingDown, Minus, RefreshCw, DollarSign, BarChart2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface ForecastWeek {
  week_label: string;
  booked_slots: number;
  projected_slots: number;
  capacity_slots: number;
  utilisation_pct: number;
  projected_revenue: number;
}

interface ForecastResult {
  clinic_id: string;
  clinic_name: string;
  trend: "on_track" | "action_needed" | "strong_growth";
  forecast_weeks: ForecastWeek[];
  insight: string;
  verbose_log: string[];
}

interface ForecastPanelProps {
  clinicId: string;
  clinicName?: string;
  onLogEntry?: (msg: string) => void;
}

const TREND_CONFIG = {
  strong_growth: { icon: TrendingUp, color: "#10b981", bg: "rgba(16,185,129,0.1)", label: "Strong Growth" },
  on_track:      { icon: Minus,       color: "#3b82f6", bg: "rgba(59,130,246,0.1)",  label: "On Track"     },
  action_needed: { icon: TrendingDown, color: "#ef4444", bg: "rgba(239,68,68,0.1)",  label: "Action Needed" },
};

function UtilBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ width: "100%", height: "6px", background: "rgba(63,63,70,0.5)", borderRadius: "3px", overflow: "hidden" }}>
      <div style={{
        height: "100%", width: `${Math.min(pct, 100)}%`,
        background: color, borderRadius: "3px",
        transition: "width 0.6s cubic-bezier(0.34,1.56,0.64,1)",
      }} />
    </div>
  );
}

export default function ForecastPanel({ clinicId, clinicName, onLogEntry }: ForecastPanelProps) {
  const [forecast, setForecast] = useState<ForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [weeks, setWeeks] = useState(4);

  const loadForecast = useCallback(async (w = weeks) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/forecast/${clinicId}?weeks=${w}`);
      if (res.ok) {
        const data: ForecastResult = await res.json();
        setForecast(data);
        data.verbose_log?.forEach(l => onLogEntry?.(`VERA (Forecast): ${l}`));
      }
    } catch {}
    setLoading(false);
  }, [clinicId, weeks]);

  useEffect(() => { loadForecast(weeks); }, [clinicId]);

  const trend = forecast ? TREND_CONFIG[forecast.trend] ?? TREND_CONFIG.on_track : null;

  // Color based on utilisation
  const utilColor = (pct: number) => {
    if (pct >= 90) return "#ef4444";
    if (pct >= 70) return "#f59e0b";
    return "#10b981";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <BarChart2 size={15} color="#6C63FF" />
          <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#e4e4e7" }}>
            Capacity Forecast
          </span>
          {trend && (
            <span style={{
              display: "flex", alignItems: "center", gap: "4px",
              background: trend.bg, color: trend.color,
              borderRadius: "8px", padding: "2px 8px", fontSize: "0.65rem", fontWeight: 700,
            }}>
              <trend.icon size={10} /> {trend.label}
            </span>
          )}
        </div>
        <button
          onClick={() => loadForecast(weeks)}
          disabled={loading}
          style={{
            display: "flex", alignItems: "center", gap: "4px",
            background: "rgba(108,99,255,0.12)", color: "#8b87ff",
            border: "1px solid rgba(108,99,255,0.25)", borderRadius: "6px",
            padding: "4px 10px", fontSize: "0.7rem", cursor: "pointer",
          }}
        >
          <RefreshCw size={11} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
          Refresh
        </button>
      </div>

      {/* Week selector */}
      <div style={{ display: "flex", gap: "4px" }}>
        {[2, 4, 6, 8].map(w => (
          <button
            key={w}
            onClick={() => { setWeeks(w); loadForecast(w); }}
            style={{
              flex: 1, padding: "4px", fontSize: "0.7rem", fontWeight: 600,
              background: weeks === w ? "rgba(108,99,255,0.2)" : "rgba(39,39,42,0.4)",
              color: weeks === w ? "#8b87ff" : "#71717a",
              border: weeks === w ? "1px solid rgba(108,99,255,0.3)" : "1px solid rgba(63,63,70,0.3)",
              borderRadius: "6px", cursor: "pointer", transition: "all 0.15s",
            }}
          >
            {w}W
          </button>
        ))}
      </div>

      {loading && !forecast && (
        <div style={{ color: "#52525b", fontSize: "0.78rem", padding: "16px", textAlign: "center" }}>
          Running linear regression…
        </div>
      )}

      {forecast && (
        <>
          {/* Insight */}
          <div style={{
            background: trend?.bg ?? "rgba(39,39,42,0.3)",
            border: `1px solid ${trend?.color ? trend.color + "33" : "rgba(63,63,70,0.3)"}`,
            borderRadius: "8px", padding: "10px 12px",
            fontSize: "0.75rem", color: "#a1a1aa", lineHeight: 1.5,
          }}>
            {forecast.insight}
          </div>

          {/* Weekly breakdown */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {forecast.forecast_weeks.map(w => {
              const color = utilColor(w.utilisation_pct);
              return (
                <div key={w.week_label} style={{
                  background: "rgba(24,24,27,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                  borderRadius: "8px", padding: "8px 10px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#e4e4e7" }}>{w.week_label}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span style={{ fontSize: "0.7rem", color: "#a1a1aa" }}>
                        {w.projected_slots}/{w.capacity_slots} slots
                      </span>
                      <span style={{
                        fontSize: "0.68rem", fontWeight: 700,
                        color, background: color + "15",
                        borderRadius: "5px", padding: "1px 6px",
                      }}>
                        {w.utilisation_pct}%
                      </span>
                      <span style={{ fontSize: "0.7rem", color: "#10b981", display: "flex", alignItems: "center", gap: "2px" }}>
                        <DollarSign size={10} />{w.projected_revenue.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <UtilBar pct={w.utilisation_pct} color={color} />
                </div>
              );
            })}
          </div>

          {/* Summary row */}
          {forecast.forecast_weeks.length > 0 && (
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
              gap: "6px", marginTop: "2px",
            }}>
              {[
                { label: "Avg Slots", value: Math.round(forecast.forecast_weeks.reduce((s, w) => s + w.projected_slots, 0) / forecast.forecast_weeks.length).toString() },
                { label: "Avg Util", value: `${(forecast.forecast_weeks.reduce((s, w) => s + w.utilisation_pct, 0) / forecast.forecast_weeks.length).toFixed(0)}%` },
                { label: "Total Rev", value: `$${(forecast.forecast_weeks.reduce((s, w) => s + w.projected_revenue, 0) / 1000).toFixed(1)}k` },
              ].map(stat => (
                <div key={stat.label} style={{
                  background: "rgba(39,39,42,0.4)", border: "1px solid rgba(63,63,70,0.3)",
                  borderRadius: "8px", padding: "8px", textAlign: "center",
                }}>
                  <div style={{ fontSize: "0.68rem", color: "#52525b", marginBottom: "2px" }}>{stat.label}</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 800, color: "#e4e4e7" }}>{stat.value}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
