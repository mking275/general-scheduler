"use client";

import { useState, useEffect } from "react";
import { FlaskConical, Clock, CheckCircle, ChevronDown, ChevronUp, PlusCircle, Loader, Bell, BellOff, Zap } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

const PANELS = [
  "CBC",
  "Chemistry Panel",
  "Urinalysis",
  "Thyroid Panel",
  "Pre-Anesthetic Panel",
  "Heartworm Test",
  "Fecal Floatation",
  "Cytology",
  "Blood Pressure",
  "Electrolytes",
  "Coagulation Panel",
  "Bile Acids",
];

const PROVIDER_COLORS: Record<string, { color: string; label: string }> = {
  idexx:    { color: "#60a5fa", label: "IDEXX"    },
  antech:   { color: "#a78bfa", label: "Antech"   },
  heska:    { color: "#34d399", label: "Heska"    },
  vetscan:  { color: "#fb923c", label: "Vetscan"  },
  manual:   { color: "#71717a", label: "Manual"   },
};

function flagInfo(value: number, low: number, high: number, rawFlag?: string): { flag: string; color: string; symbol: string; critical: boolean } {
  const f = (rawFlag || "").toUpperCase();
  if (f === "HH") return { flag: "HH", color: "#ef4444", symbol: "▲▲ HH", critical: true };
  if (f === "LL") return { flag: "LL", color: "#3b82f6", symbol: "▼▼ LL", critical: true };
  if (value > high || f === "H") return { flag: "H", color: "#f87171", symbol: "▲ H", critical: false };
  if (value < low || f === "L")  return { flag: "L", color: "#60a5fa", symbol: "▼ L", critical: false };
  return { flag: "normal", color: "#4ade80", symbol: "✓", critical: false };
}


function AnalyteRow({ a }: { a: any }) {
  const { flag, color, symbol, critical } = flagInfo(a.value, a.low, a.high, a.flag);
  const isAbnormal = flag !== "normal";
  return (
    <tr style={{ background: critical ? "rgba(239,68,68,0.08)" : isAbnormal ? "rgba(239,68,68,0.04)" : "transparent" }}>
      <td style={{ padding: "5px 8px", color: "#d4d4d8", fontSize: "0.73rem", fontWeight: isAbnormal ? 600 : 400 }}>
        {critical && <span title="Critical value" style={{ color: "#ef4444", marginRight: "4px", fontSize: "0.65rem" }}>⚠</span>}
        {a.name}
      </td>
      <td style={{
        padding: "5px 8px", fontWeight: 700, fontSize: "0.73rem",
        color: critical ? "#ef4444" : isAbnormal ? color : "#f4f4f5",
        fontVariantNumeric: "tabular-nums", textAlign: "right",
      }}>
        {a.value}
      </td>
      <td style={{ padding: "5px 8px", color: "#52525b", fontSize: "0.65rem", textAlign: "center" }}>
        {a.unit}
      </td>
      <td style={{ padding: "5px 8px", color: "#3f3f46", fontSize: "0.65rem", textAlign: "center" }}>
        {a.low}–{a.high}
      </td>
      <td style={{ padding: "5px 8px", textAlign: "right" }}>
        <span style={{
          fontSize: "0.62rem", fontWeight: 700, padding: "1px 6px",
          borderRadius: "4px", color,
          background: isAbnormal ? `${color}18` : "transparent",
          border: isAbnormal ? `1px solid ${color}40` : "none",
        }}>
          {symbol}
        </span>
      </td>
    </tr>
  );
}


function LabCard({ lab, defaultOpen = false, onAcknowledge }: { lab: any; defaultOpen?: boolean; onAcknowledge?: (id: string) => void }) {
  const [open, setOpen] = useState(defaultOpen);
  const isPending = lab.status === "pending";
  const isCritical = lab.status === "critical" || lab.has_critical_values;
  const isAcknowledged = !!lab.acknowledged_at;
  const panels: any[] = lab.results?.panels ?? [];

  const allAnalytes = panels.flatMap(p => p.analytes ?? []);
  const abnormalCount = allAnalytes.filter(a => flagInfo(a.value, a.low, a.high, a.flag).flag !== "normal").length;
  const criticalCount = allAnalytes.filter(a => flagInfo(a.value, a.low, a.high, a.flag).critical).length;

  const providerInfo = PROVIDER_COLORS[lab.provider] ?? PROVIDER_COLORS.manual;


  return (
    <div style={{
      borderRadius: "10px", overflow: "hidden",
      border: `1px solid ${isCritical && !isAcknowledged
        ? "rgba(239,68,68,0.4)"
        : isPending ? "rgba(251,191,36,0.25)"
        : abnormalCount > 0 ? "rgba(248,113,113,0.25)"
        : "rgba(63,63,70,0.4)"}`,
      background: isCritical && !isAcknowledged ? "rgba(239,68,68,0.03)" : "rgba(24,24,27,0.6)",
      boxShadow: isCritical && !isAcknowledged ? "0 0 12px rgba(239,68,68,0.15)" : "none",
      transition: "border-color 0.2s ease",
    }}>
      {/* Header */}
      <div
      onClick={() => setOpen(p => !p)}
        style={{
          padding: "9px 12px", display: "flex", alignItems: "center",
          gap: "10px", cursor: "pointer",
          background: isCritical && !isAcknowledged ? "rgba(239,68,68,0.06)" : isPending ? "rgba(251,191,36,0.05)" : "transparent",
        }}
      >
        {/* Icon */}
        {isPending
          ? <Loader size={13} color="#fbbf24" style={{ flexShrink: 0 }} />
          : isCritical && !isAcknowledged
          ? <Bell size={13} color="#ef4444" style={{ flexShrink: 0, animation: "pulse 1s infinite" }} />
          : <FlaskConical size={13} color="#818cf8" style={{ flexShrink: 0 }} />}

        {/* Panel name */}
        <span style={{ fontSize: "0.75rem", fontWeight: 700, color: isCritical && !isAcknowledged ? "#fca5a5" : "#f4f4f5", flex: 1 }}>
          {lab.panel_name}
        </span>

        {/* Provider badge */}
        {lab.provider && lab.provider !== "manual" && (
          <span style={{
            fontSize: "0.58rem", fontWeight: 700, padding: "1px 6px", borderRadius: "4px",
            background: `${providerInfo.color}14`, color: providerInfo.color,
            border: `1px solid ${providerInfo.color}30`,
          }}>
            {providerInfo.label}
          </span>
        )}

        {/* Critical badge */}
        {isCritical && !isAcknowledged && (
          <span style={{
            fontSize: "0.6rem", fontWeight: 800, padding: "1px 7px", borderRadius: "4px",
            background: "rgba(239,68,68,0.2)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.4)",
            animation: "pulse 1s infinite",
          }}>
            ⚠ CRITICAL
          </span>
        )}

        {/* Acknowledged badge */}
        {isCritical && isAcknowledged && (
          <span style={{
            fontSize: "0.6rem", fontWeight: 700, padding: "1px 6px", borderRadius: "4px",
            background: "rgba(52,211,153,0.1)", color: "#34d399", border: "1px solid rgba(52,211,153,0.25)",
          }}>
            <BellOff size={9} style={{ display: "inline", marginRight: "3px" }} />ACK
          </span>
        )}

        {/* Abnormal count */}
        {!isPending && abnormalCount > 0 && !isCritical && (
          <span style={{
            fontSize: "0.6rem", fontWeight: 700, padding: "1px 6px", borderRadius: "4px",
            background: "rgba(248,113,113,0.15)", color: "#f87171", border: "1px solid rgba(248,113,113,0.3)",
          }}>
            {abnormalCount} abnormal
          </span>
        )}

        {/* Status */}
        <span style={{
          fontSize: "0.62rem", fontWeight: 700, padding: "1px 7px", borderRadius: "4px",
          background: isPending ? "rgba(251,191,36,0.12)" : "rgba(52,211,153,0.1)",
          color: isPending ? "#fbbf24" : "#34d399",
          border: isPending ? "1px solid rgba(251,191,36,0.3)" : "1px solid rgba(52,211,153,0.25)",
        }}>
          {isPending ? "⏳ Pending" : "✓ Resulted"}
        </span>

        {/* Date */}
        <span style={{ fontSize: "0.63rem", color: "#52525b" }}>
          {new Date(lab.resulted_at ?? lab.ordered_at).toLocaleDateString([], { month: "short", day: "numeric" })}
        </span>

        {open ? <ChevronUp size={12} color="#52525b" /> : <ChevronDown size={12} color="#52525b" />}
      </div>

      {/* Critical acknowledge banner */}
      {open && isCritical && !isAcknowledged && (
        <div style={{
          padding: "8px 12px", background: "rgba(239,68,68,0.08)",
          borderBottom: "1px solid rgba(239,68,68,0.2)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontSize: "0.72rem", color: "#fca5a5", fontWeight: 600 }}>
            ⚠ {criticalCount} critical value{criticalCount > 1 ? "s" : ""} — acknowledge before discharging
          </span>
          <button
            onClick={() => onAcknowledge?.(lab.id)}
            style={{
              padding: "5px 12px", borderRadius: "7px",
              background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)",
              color: "#f87171", fontSize: "0.7rem", fontWeight: 700, cursor: "pointer",
              display: "flex", alignItems: "center", gap: "5px",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(239,68,68,0.25)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(239,68,68,0.15)"; }}
          >
            <CheckCircle size={11} /> Acknowledge
          </button>
        </div>
      )}

      {/* Results table */}
      {open && !isPending && panels.length > 0 && (
        <div style={{ borderTop: "1px solid rgba(63,63,70,0.35)", padding: "8px 0" }}>
          {panels.map((panel, pi) => (
            <div key={pi}>
              <div style={{ padding: "4px 12px", fontSize: "0.6rem", fontWeight: 700, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                {panel.name}
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Test", "Value", "Unit", "Ref Range", "Flag"].map(h => (
                      <th key={h} style={{ padding: "3px 8px", fontSize: "0.58rem", color: "#3f3f46", fontWeight: 600, textAlign: h === "Test" ? "left" : h === "Value" ? "right" : "center", borderBottom: "1px solid rgba(63,63,70,0.25)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(panel.analytes ?? []).map((a: any, ai: number) => (
                    <AnalyteRow key={ai} a={a} />
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {lab.ordered_by && (
            <div style={{ padding: "6px 12px 2px", fontSize: "0.63rem", color: "#3f3f46" }}>
              Ordered by {lab.ordered_by} · {new Date(lab.ordered_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
        </div>
      )}

      {open && isPending && (
        <div style={{ borderTop: "1px solid rgba(63,63,70,0.3)", padding: "14px 16px", color: "#71717a", fontSize: "0.73rem", display: "flex", alignItems: "center", gap: "8px" }}>
          <Loader size={13} color="#fbbf24" />
          Ordered {new Date(lab.ordered_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · results typically ready in 1–2 hours
        </div>
      )}
    </div>
  );
}

interface LabsPanelProps {
  patientId?: string;
  timeblockId?: string;
  orderedBy?: string;
}

export default function LabsPanel({ patientId, timeblockId, orderedBy }: LabsPanelProps) {
  const [labs, setLabs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [ordering, setOrdering] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [selectedPanel, setSelectedPanel] = useState(PANELS[0]);
  const [showOrder, setShowOrder] = useState(false);
  const [showSimulate, setShowSimulate] = useState(false);
  const [justOrdered, setJustOrdered] = useState<string | null>(null);


  const fetchLabs = async () => {
    if (!patientId) { setLoading(false); return; }
    try {
      const r = await fetch(`${API}/api/labs/patient/${patientId}`);
      if (r.ok) setLabs(await r.json());
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchLabs(); }, [patientId]);

  const handleOrder = async () => {
    if (!patientId) return;
    setOrdering(true);
    try {
      const r = await fetch(`${API}/api/labs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          timeblock_id: timeblockId,
          panel_name: selectedPanel,
          ordered_by: orderedBy ?? "Attending Vet",
        }),
      });
      if (r.ok) {
        const lab = await r.json();
        setLabs(prev => [lab, ...prev]);
        setJustOrdered(selectedPanel);
        setShowOrder(false);
        setTimeout(() => setJustOrdered(null), 4000);
      }
    } catch {}
    setOrdering(false);
  };

  const handleSimulate = async (panel: string, includeCritical: boolean) => {
    if (!patientId) return;
    setSimulating(true);
    try {
      await fetch(
        `${API}/api/labs/simulate?patient_id=${patientId}&panel=${encodeURIComponent(panel)}&include_critical=${includeCritical}`,
        { method: "POST" }
      );
      setJustOrdered(`Simulated ${panel}${includeCritical ? " (critical)" : ""}`);
      setShowSimulate(false);
      // Poll for the new result
      setTimeout(async () => {
        await fetchLabs();
        setTimeout(fetchLabs, 2500);
      }, 1200);
    } catch {}
    setSimulating(false);
  };

  const handleAcknowledge = async (labId: string) => {
    try {
      await fetch(`${API}/api/labs/${labId}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vet_id: orderedBy ?? "Attending Vet" }),
      });
      await fetchLabs();
    } catch {}
  };


  // Separate today's labs from history
  const todayKey = new Date().toISOString().slice(0, 10);
  const todayLabs = labs.filter(l => l.ordered_at?.slice(0, 10) === todayKey);
  const histLabs  = labs.filter(l => l.ordered_at?.slice(0, 10) !== todayKey);

  if (!patientId) {
    return (
      <div style={{ padding: "14px 0", textAlign: "center", color: "#52525b", fontSize: "0.75rem" }}>
        No patient linked to this appointment.
      </div>
    );
  }

  const criticalUnacknowledged = labs.filter(l => (l.status === "critical" || l.has_critical_values) && !l.acknowledged_at);

  return (
    <div>
      {/* Critical alert banner */}
      {criticalUnacknowledged.length > 0 && (
        <div style={{
          marginBottom: "12px", padding: "9px 12px", borderRadius: "8px",
          background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.35)",
          display: "flex", alignItems: "center", gap: "8px",
          color: "#fca5a5", fontSize: "0.73rem", fontWeight: 700,
          animation: "pulse 1.5s infinite",
        }}>
          <Bell size={13} color="#ef4444" />
          {criticalUnacknowledged.length} result{criticalUnacknowledged.length > 1 ? "s" : ""} with CRITICAL values — review required
        </div>
      )}


      {/* Order new lab */}
      <div style={{ marginBottom: "12px" }}>
        {!showOrder && !showSimulate ? (
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => setShowOrder(true)}
              style={{
                flex: 1, padding: "8px 14px", borderRadius: "9px",
                background: "rgba(99,102,241,0.08)", border: "1px dashed rgba(99,102,241,0.3)",
                color: "#818cf8", fontSize: "0.73rem", fontWeight: 600,
                cursor: "pointer", display: "flex", alignItems: "center",
                justifyContent: "center", gap: "7px", transition: "all 0.15s ease",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(99,102,241,0.14)"; e.currentTarget.style.borderStyle = "solid"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(99,102,241,0.08)"; e.currentTarget.style.borderStyle = "dashed"; }}
            >
              <PlusCircle size={13} /> Order Panel
            </button>
            <button
              onClick={() => setShowSimulate(true)}
              title="Simulate in-house instrument result"
              style={{
                padding: "8px 12px", borderRadius: "9px",
                background: "rgba(251,191,36,0.08)", border: "1px dashed rgba(251,191,36,0.3)",
                color: "#fbbf24", fontSize: "0.73rem", fontWeight: 600,
                cursor: "pointer", display: "flex", alignItems: "center", gap: "6px",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(251,191,36,0.14)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(251,191,36,0.08)"; }}
            >
              <Zap size={12} /> Simulate
            </button>
          </div>
        ) : showSimulate ? (
          /* Simulate in-house result form */
          <div style={{
            padding: "12px", borderRadius: "10px",
            background: "rgba(251,191,36,0.06)", border: "1px solid rgba(251,191,36,0.25)",
            display: "flex", flexDirection: "column", gap: "10px",
          }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#fbbf24", textTransform: "uppercase", letterSpacing: "0.07em" }}>
              Simulate In-House Instrument Result
            </div>
            <select
              value={selectedPanel}
              onChange={e => setSelectedPanel(e.target.value)}
              style={{
                width: "100%", padding: "7px 10px", borderRadius: "7px",
                background: "#18181b", border: "1px solid rgba(63,63,70,0.6)",
                color: "#f4f4f5", fontSize: "0.75rem", outline: "none",
              }}
            >
              {["CBC", "Chemistry Panel", "Electrolytes"].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => handleSimulate(selectedPanel, false)}
                disabled={simulating}
                style={{
                  flex: 1, padding: "7px", borderRadius: "7px",
                  background: "rgba(251,191,36,0.12)", border: "1px solid rgba(251,191,36,0.35)",
                  color: "#fbbf24", fontSize: "0.72rem", fontWeight: 700, cursor: simulating ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "5px",
                }}
              >
                {simulating ? <Loader size={11} /> : <Zap size={11} />} Normal Result
              </button>
              <button
                onClick={() => handleSimulate(selectedPanel, true)}
                disabled={simulating}
                style={{
                  flex: 1, padding: "7px", borderRadius: "7px",
                  background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.35)",
                  color: "#f87171", fontSize: "0.72rem", fontWeight: 700, cursor: simulating ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "5px",
                }}
              >
                <Bell size={11} /> Critical
              </button>
              <button
                onClick={() => setShowSimulate(false)}
                style={{
                  padding: "7px 12px", borderRadius: "7px", background: "transparent",
                  border: "1px solid rgba(63,63,70,0.4)", color: "#71717a",
                  fontSize: "0.73rem", cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>
          </div>
        ) : (

          <div style={{
            padding: "12px", borderRadius: "10px",
            background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.25)",
            display: "flex", flexDirection: "column", gap: "10px",
          }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#818cf8", textTransform: "uppercase", letterSpacing: "0.07em" }}>
              Order Lab Panel
            </div>
            <select
              value={selectedPanel}
              onChange={e => setSelectedPanel(e.target.value)}
              style={{
                width: "100%", padding: "7px 10px", borderRadius: "7px",
                background: "#18181b", border: "1px solid rgba(63,63,70,0.6)",
                color: "#f4f4f5", fontSize: "0.75rem", outline: "none",
              }}
            >
              {PANELS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={handleOrder}
                disabled={ordering}
                style={{
                  flex: 1, padding: "7px", borderRadius: "7px",
                  background: ordering ? "rgba(99,102,241,0.1)" : "rgba(99,102,241,0.2)",
                  border: "1px solid rgba(99,102,241,0.4)", color: "#a5b4fc",
                  fontSize: "0.73rem", fontWeight: 700, cursor: ordering ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                  transition: "all 0.15s ease",
                }}
              >
                {ordering ? <><Loader size={11} /> Ordering…</> : <><FlaskConical size={11} /> Submit Order</>}
              </button>
              <button
                onClick={() => setShowOrder(false)}
                style={{
                  padding: "7px 14px", borderRadius: "7px", background: "transparent",
                  border: "1px solid rgba(63,63,70,0.4)", color: "#71717a",
                  fontSize: "0.73rem", cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>


      {/* Success toast */}
      {justOrdered && (
        <div style={{
          marginBottom: "10px", padding: "8px 12px", borderRadius: "8px",
          background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.3)",
          color: "#34d399", fontSize: "0.73rem", fontWeight: 600,
          display: "flex", alignItems: "center", gap: "7px",
          animation: "fadeIn 0.2s ease",
        }}>
          <CheckCircle size={13} /> {justOrdered} ordered — results pending
        </div>
      )}

      {loading ? (
        <div style={{ color: "#52525b", fontSize: "0.75rem", padding: "12px 0", display: "flex", alignItems: "center", gap: "7px" }}>
          <Loader size={13} /> Loading lab history…
        </div>
      ) : (
        <>
          {/* Today's labs */}
          {todayLabs.length > 0 && (
            <div style={{ marginBottom: "12px" }}>
              <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "6px" }}>
                Today's Orders
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {todayLabs.map((lab, i) => <LabCard key={lab.id} lab={lab} defaultOpen={i === 0} onAcknowledge={handleAcknowledge} />)}
              </div>
            </div>
          )}

          {/* Historical labs */}
          {histLabs.length > 0 && (
            <div>
              <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "6px" }}>
                Lab History · {histLabs.length} records
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {histLabs.map((lab, i) => <LabCard key={lab.id} lab={lab} defaultOpen={i === 0} onAcknowledge={handleAcknowledge} />)}
              </div>
            </div>
          )}


          {labs.length === 0 && !showOrder && (
            <div style={{ padding: "16px 0", textAlign: "center", color: "#52525b", fontSize: "0.75rem" }}>
              No lab results on file. Order a panel above.
            </div>
          )}
        </>
      )}
    </div>
  );
}
