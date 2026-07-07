"use client";

import { useState, useEffect } from "react";
import RiskBadge from "./RiskBadge";
import SoapWorkspace from "./SoapWorkspace";
import {
  ChevronDown, ChevronUp, Clock, User,
  FileText, History, Image, CalendarPlus, CheckCircle2, AlertTriangle, FlaskConical
} from "lucide-react";
import LabsPanel from "./LabsPanel";
import BreedAlertsPanel from "./BreedAlertsPanel";
import CareTimelinePanel from "./CareTimelinePanel";
import PrescriptionPanel from "./PrescriptionPanel";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

type Tab = "history" | "labs" | "soap" | "imaging" | "followup" | "breed" | "care" | "rx";

function suggestFollowUp(procedure: string, patientName: string): { interval: string; note: string; prompt: string } {
  const p = (procedure ?? "").toLowerCase();
  if (p.includes("surgery") || p.includes("repair") || p.includes("removal") || p.includes("cruciate"))
    return { interval: "2 weeks", note: "Post-operative recheck recommended", prompt: `Schedule a post-op check for ${patientName} in 2 weeks` };
  if (p.includes("dental") || p.includes("tooth") || p.includes("scale"))
    return { interval: "6 months", note: "Next dental clean in 6 months", prompt: `Schedule a dental cleaning follow-up for ${patientName} in 6 months` };
  if (p.includes("cardiac") || p.includes("echo") || p.includes("heart"))
    return { interval: "3 months", note: "Cardiac monitoring follow-up", prompt: `Schedule a cardiac monitoring appointment for ${patientName} in 3 months` };
  if (p.includes("ultrasound") || p.includes("imaging") || p.includes("x-ray"))
    return { interval: "3 months", note: "Imaging follow-up recommended", prompt: `Schedule an imaging follow-up for ${patientName} in 3 months` };
  if (p.includes("avian") || p.includes("exotic") || p.includes("reptile") || p.includes("bearded"))
    return { interval: "6 months", note: "Exotic species health screening", prompt: `Schedule an exotic health screening for ${patientName} in 6 months` };
  if (p.includes("vaccination") || p.includes("booster") || p.includes("annual") || p.includes("wellness"))
    return { interval: "12 months", note: "Annual wellness & vaccination due", prompt: `Schedule the annual wellness exam for ${patientName} in 12 months` };
  if (p.includes("grooming") || p.includes("bath"))
    return { interval: "6–8 weeks", note: "Regular grooming cycle", prompt: `Schedule a grooming appointment for ${patientName} in 6 weeks` };
  return { interval: "1 month", note: "General follow-up recommended", prompt: `Schedule a follow-up appointment for ${patientName} in 1 month` };
}

interface Props {
  item: any;
  patient?: any;
  onLogEntry?: (msg: string) => void;
}

function Tag({ label, color, bg }: { label: string; color: string; bg: string }) {
  return (
    <span style={{
      padding: "1px 6px", borderRadius: "4px", fontSize: "0.6rem",
      fontWeight: 700, letterSpacing: "0.05em", background: bg, color,
    }}>{label}</span>
  );
}

function TabBtn({ id, label, icon, active, onClick }: {
  id: Tab; label: string; icon: React.ReactNode; active: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: "5px",
      padding: "5px 10px", borderRadius: "8px", fontSize: "0.68rem", fontWeight: active ? 700 : 500,
      border: active ? "1px solid rgba(139,92,246,0.4)" : "1px solid transparent",
      background: active ? "rgba(139,92,246,0.12)" : "transparent",
      color: active ? "#c4b5fd" : "#71717a",
      cursor: "pointer", transition: "all 0.15s ease", outline: "none",
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.color = "#a1a1aa"; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.color = "#71717a"; }}
    >{icon}{label}</button>
  );
}

export default function VetAppointmentCard({ item, patient, onLogEntry }: Props) {
  const [expanded, setExpanded]   = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("history");
  const [riskScore, setRiskScore] = useState<any>(null);
  const [history, setHistory]     = useState<any[] | null>(null);
  const [histLoading, setHistLoading] = useState(false);
  const [isComplete, setIsComplete]   = useState(item.status === "complete");
  const [soapOpen, setSoapOpen]       = useState(false);
  const [ownerPhotos, setOwnerPhotos] = useState<any[] | null>(null);
  const [patientStudies, setPatientStudies] = useState<any[] | null>(null);
  const [soapHistory, setSoapHistory] = useState<any[] | null>(null);
  const [soapHistLoading, setSoapHistLoading] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  const tbId = item.timeblock_id ?? item.id;
  const procedure = item.job?.procedure ?? "Unknown Procedure";
  const patName = patient?.name ?? item.job?.patient_name ?? "Unknown";
  const followUp = suggestFollowUp(procedure, patName);

  // Fetch risk score
  useEffect(() => {
    if (!tbId) return;
    fetch(`${API}/api/risk/${tbId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setRiskScore(d); })
      .catch(() => {});
  }, [tbId]);

  // Fetch history when tab opened
  useEffect(() => {
    if (activeTab === "history" && expanded && patient?.id && history === null) {
      setHistLoading(true);
      fetch(`${API}/api/patients/${patient.id}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { setHistory(d?.visit_history ?? d?.history ?? []); setHistLoading(false); })
        .catch(() => { setHistory([]); setHistLoading(false); });
    }
  }, [activeTab, expanded, patient?.id]);

  // Fetch owner photos when imaging tab opened
  useEffect(() => {
    if (activeTab === "imaging" && expanded && ownerPhotos === null) {
      fetch(`${API}/api/timeblocks/${tbId}/images`)
        .then(r => r.ok ? r.json() : [])
        .then(imgs => setOwnerPhotos(imgs))
        .catch(() => setOwnerPhotos([]));
    }
  }, [activeTab, expanded, tbId]);

  // Fetch patient-level imaging studies (historical X-rays, DICOM)
  useEffect(() => {
    if (activeTab === "imaging" && expanded && patient?.id && patientStudies === null) {
      fetch(`${API}/api/patients/${patient.id}/images`)
        .then(r => r.ok ? r.json() : [])
        .then(studies => setPatientStudies(studies))
        .catch(() => setPatientStudies([]));
    }
  }, [activeTab, expanded, patient?.id]);

  // Fetch SOAP history when tab opened
  useEffect(() => {
    if (activeTab === "soap" && expanded && patient?.id && soapHistory === null) {
      setSoapHistLoading(true);
      fetch(`${API}/api/patients/${patient.id}/soap-notes`)
        .then(r => r.ok ? r.json() : [])
        .then(notes => { setSoapHistory(notes); setSoapHistLoading(false); })
        .catch(() => { setSoapHistory([]); setSoapHistLoading(false); });
    }
  }, [activeTab, expanded, patient?.id]);

  const handleComplete = async () => {
    const res = await fetch(`${API}/api/appointments/${tbId}/complete`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: false }),
    });
    if (res.ok) {
      setIsComplete(true);
      onLogEntry?.("DISPATCH: Appointment marked complete");
    }
  };

  const handleSuggestMessage = (msg: string) => {
    window.dispatchEvent(new CustomEvent("vet-suggest-message", { detail: { message: msg } }));
    onLogEntry?.(`AGENT HINT: ${msg}`);
  };

  const accentColor =
    riskScore?.risk_level === "high"   ? "#ef4444" :
    riskScore?.risk_level === "medium" ? "#f59e0b" : "#10b981";

  const allergies: string[] = patient?.allergies ?? patient?.alerts?.filter((a: string) =>
    a.toLowerCase().includes("allerg")) ?? [];
  const alertTags: string[] = patient?.conditions ?? patient?.tags ?? [];

  const vet  = (item.resources ?? []).find((r: any) => r.type === "Vet");
  const room = (item.resources ?? []).find((r: any) => r.type === "Room" || r.type === "Exam Room" || r.type === "Operating Room");

  return (
    <>
    <div style={{
      background: "linear-gradient(160deg,#18181b 0%,#09090b 100%)",
      border: "1px solid rgba(63,63,70,0.7)",
      borderRadius: "16px", overflow: "hidden",
      boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
      transition: "box-shadow 0.2s ease",
    }}>
      {/* Accent bar */}
      <div style={{ height: "3px", background: isComplete ? "#10b981" : accentColor }} />

      {/* ── HEADER (always visible) ─────────────────────────────── */}
      <div style={{ padding: "12px 16px", cursor: "pointer" }} onClick={() => setExpanded(p => !p)}>
        {/* Row 1: Skills + badges + chevron */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
          <span style={{
            background: "rgba(59,130,246,0.12)", color: "#60a5fa",
            fontSize: "0.65rem", padding: "2px 8px", borderRadius: "4px",
            fontWeight: 700, letterSpacing: "0.06em", border: "1px solid rgba(59,130,246,0.2)",
          }}>
            {(item.job?.required_skills ?? []).join(", ")}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            {isComplete && (
              <span style={{ background: "rgba(16,185,129,0.12)", color: "#10b981", fontSize: "0.62rem", padding: "2px 7px", borderRadius: "10px", fontWeight: 700, border: "1px solid rgba(16,185,129,0.25)" }}>✓ DONE</span>
            )}
            <RiskBadge level={riskScore?.risk_level ?? item.risk_level ?? null} factors={riskScore?.factors ?? []} />
            {expanded ? <ChevronUp size={14} color="#71717a" /> : <ChevronDown size={14} color="#71717a" />}
          </div>
        </div>

        {/* Row 2: Patient identity */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <span style={{ fontSize: "1.5rem", lineHeight: 1 }}>
            {patient?.emoji ?? (patient?.species === "cat" ? "🐱" : patient?.species === "bird" ? "🦜" : patient?.species === "rabbit" ? "🐰" : patient?.species === "reptile" ? "🦎" : "🐶")}
          </span>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "0.92rem", fontWeight: 700, color: "#f4f4f5" }}>{patName}</span>
              {patient?.breed && <span style={{ fontSize: "0.7rem", color: "#71717a" }}>{patient.breed}</span>}
              {patient?.age_years && <span style={{ fontSize: "0.7rem", color: "#52525b" }}>{patient.age_years}y · {patient.weight_kg}kg</span>}
            </div>
            <div style={{ display: "flex", gap: "4px", marginTop: "3px", flexWrap: "wrap" }}>
              {patient?.is_alert     && <Tag label="ALERT"       color="#f87171" bg="rgba(248,113,113,0.15)" />}
              {patient?.is_chronic   && <Tag label="CHRONIC"     color="#c084fc" bg="rgba(192,132,252,0.15)" />}
              {patient?.is_first_visit && <Tag label="FIRST VISIT" color="#34d399" bg="rgba(52,211,153,0.12)" />}
            </div>
          </div>
        </div>

        {/* Row 3: Procedure + time + vet + room */}
        <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#a1a1aa", fontSize: "0.78rem" }}>
            <FileText size={11} />
            <span style={{ fontWeight: 600, color: "#d4d4d8" }}>{procedure}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "#71717a", fontSize: "0.72rem" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <Clock size={10} />
              {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              {" – "}
              {new Date(item.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            {vet  && <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><User size={10} />{vet.name}</span>}
            {room && <span style={{ color: "#52525b" }}>📍 {room.name}</span>}
          </div>
        </div>
      </div>

      {/* ── EXPANDED CLINICAL BODY ──────────────────────────────── */}
      <div style={{
        maxHeight: expanded ? "1600px" : "0px", overflow: expanded ? "auto" : "hidden",
        transition: "max-height 0.3s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <div style={{ padding: "0 16px 16px", borderTop: "1px solid rgba(63,63,70,0.35)" }}>

          {/* Allergy / alert banner */}
          {(allergies.length > 0 || patient?.allergy_notes) && (
            <div style={{
              margin: "12px 0 8px", padding: "8px 12px", borderRadius: "8px",
              background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.3)",
              display: "flex", alignItems: "center", gap: "8px", fontSize: "0.75rem",
            }}>
              <AlertTriangle size={13} color="#fbbf24" />
              <span style={{ color: "#fcd34d", fontWeight: 600 }}>
                {patient?.allergy_notes ?? allergies.join(", ")}
              </span>
            </div>
          )}

          {/* Owner quick-ref */}
          {patient?.owner && (
            <div style={{ margin: "8px 0", padding: "8px 12px", borderRadius: "8px", background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)", fontSize: "0.72rem", color: "#71717a", display: "flex", gap: "20px" }}>
              <div><span style={{ color: "#52525b", display: "block", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>Owner</span><span style={{ color: "#d4d4d8", fontWeight: 600 }}>{patient.owner.name}</span></div>
              {patient.owner.phone && <div><span style={{ color: "#52525b", display: "block", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>Phone</span><span style={{ color: "#d4d4d8" }}>{patient.owner.phone}</span></div>}
            </div>
          )}

          {/* Tab bar */}
          <div style={{ display: "flex", gap: "4px", margin: "12px 0 10px", flexWrap: "wrap" }}>
            <TabBtn id="history"  label="History"    icon={<History size={11} />}       active={activeTab === "history"}  onClick={() => setActiveTab("history")} />
            <TabBtn id="labs"     label="Labs"       icon={<FlaskConical size={11} />}  active={activeTab === "labs"}     onClick={() => setActiveTab("labs")} />
            <TabBtn id="soap"     label="SOAP Notes" icon={<FileText size={11} />}      active={activeTab === "soap"}     onClick={() => setActiveTab("soap")} />
            <TabBtn id="imaging"  label="Imaging"    icon={<Image size={11} />}       active={activeTab === "imaging"}  onClick={() => setActiveTab("imaging")} />
            <TabBtn id="followup" label="Follow-Up"  icon={<CalendarPlus size={11} />} active={activeTab === "followup"} onClick={() => setActiveTab("followup")} />
            <TabBtn id="breed"    label="Breed"      icon={<span style={{fontSize:"10px"}}>🧬</span>}  active={activeTab === "breed"}    onClick={() => setActiveTab("breed")} />
            <TabBtn id="care"     label="Care"       icon={<span style={{fontSize:"10px"}}>💉</span>} active={activeTab === "care"}     onClick={() => setActiveTab("care")} />
            <TabBtn id="rx"       label="Rx"         icon={<span style={{fontSize:"10px"}}>💊</span>} active={activeTab === "rx"}       onClick={() => setActiveTab("rx")} />
          </div>

          {/* ── History tab ── */}
          {activeTab === "history" && (
            <div>
              {histLoading ? (
                <div style={{ color: "#52525b", fontSize: "0.75rem", padding: "12px 0" }}>Loading visit history…</div>
              ) : (history && history.length > 0) ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <div style={{ fontSize: "0.65rem", color: "#52525b", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    {history.length} past visits
                  </div>
                  {history.slice(0, 6).map((v: any, i: number) => (
                    <div key={i} style={{
                      display: "grid", gridTemplateColumns: "80px 1fr auto",
                      padding: "6px 10px", borderRadius: "7px",
                      background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                      fontSize: "0.7rem", gap: "8px", alignItems: "center",
                    }}>
                      <span style={{ color: "#52525b", fontVariantNumeric: "tabular-nums" }}>
                        {v.date ?? v.scheduled_date ?? "—"}
                      </span>
                      <span style={{ color: "#d4d4d8" }}>{v.procedure ?? v.visit_type ?? "Visit"}</span>
                      <span style={{ color: "#71717a", textAlign: "right" }}>{v.vet ?? v.provider ?? ""}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ padding: "16px 0", textAlign: "center", color: "#52525b", fontSize: "0.75rem" }}>
                  {patient ? "No prior visit history on file." : "No patient record linked to this appointment."}
                </div>
              )}
            </div>
          )}

          {/* ── SOAP tab ── */}
          {activeTab === "soap" && (
            <div>
              <p style={{ color: "#71717a", fontSize: "0.75rem", margin: "0 0 10px" }}>
                Create or update the SOAP note for today's visit.
              </p>
              <button onClick={() => setSoapOpen(true)} style={{
                width: "100%", padding: "9px", borderRadius: "8px",
                background: "rgba(139,92,246,0.1)", color: "#a78bfa",
                border: "1px solid rgba(139,92,246,0.3)", fontSize: "0.78rem",
                fontWeight: 600, cursor: "pointer", display: "flex",
                alignItems: "center", justifyContent: "center", gap: "7px",
                transition: "background 0.15s ease",
              }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(139,92,246,0.18)"}
              onMouseLeave={e => e.currentTarget.style.background = "rgba(139,92,246,0.1)"}
              >
                <FileText size={14} /> Open SOAP Workspace
              </button>

              {/* ── Historical SOAP Notes ── */}
              {soapHistLoading ? (
                <div style={{ color: "#52525b", fontSize: "0.72rem", padding: "12px 0" }}>Loading SOAP history…</div>
              ) : soapHistory && soapHistory.length > 0 ? (
                <div style={{ marginTop: "14px" }}>
                  <div style={{ fontSize: "0.65rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ background: "rgba(139,92,246,0.12)", color: "#c4b5fd", border: "1px solid rgba(139,92,246,0.25)", borderRadius: "4px", padding: "1px 6px", fontSize: "0.6rem", fontWeight: 700 }}>HISTORY</span>
                    {soapHistory.length} Prior SOAP Notes
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {soapHistory.map((note: any) => (
                      <details key={note.id} style={{
                        borderRadius: "8px", overflow: "hidden",
                        background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                      }}>
                        <summary style={{
                          padding: "10px 14px", cursor: "pointer", userSelect: "none",
                          display: "flex", alignItems: "center", gap: "8px", fontSize: "0.73rem",
                          listStyle: "none",
                        }}>
                          <span style={{ color: "#52525b", fontSize: "0.65rem", fontVariantNumeric: "tabular-nums", minWidth: "72px" }}>
                            {note.date}
                          </span>
                          <span style={{ color: "#d4d4d8", fontWeight: 600, flex: 1 }}>{note.procedure}</span>
                          {note.signed ? (
                            <span style={{ fontSize: "0.58rem", fontWeight: 700, padding: "1px 6px", borderRadius: "4px", background: "rgba(16,185,129,0.1)", color: "#34d399", border: "1px solid rgba(16,185,129,0.25)" }}>✓ SIGNED</span>
                          ) : (
                            <span style={{ fontSize: "0.58rem", fontWeight: 700, padding: "1px 6px", borderRadius: "4px", background: "rgba(251,191,36,0.1)", color: "#fbbf24", border: "1px solid rgba(251,191,36,0.25)" }}>DRAFT</span>
                          )}
                          <span style={{ color: "#52525b", fontSize: "0.65rem" }}>{note.signed_by}</span>
                        </summary>
                        <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(63,63,70,0.25)" }}>
                          {/* S — Subjective */}
                          {note.subjective && (
                            <div style={{ marginTop: "10px", marginBottom: "10px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.68rem", fontWeight: 700, color: "#818cf8", marginBottom: "4px" }}>
                                <span style={{ width: "3px", height: "12px", background: "#818cf8", borderRadius: "2px", display: "inline-block" }} />
                                S — Subjective
                              </div>
                              <div style={{ color: "#a1a1aa", fontSize: "0.7rem", lineHeight: 1.5, padding: "6px 10px", background: "rgba(9,9,11,0.5)", borderRadius: "6px", border: "1px solid rgba(63,63,70,0.25)" }}>
                                {note.subjective}
                              </div>
                            </div>
                          )}
                          {/* O — Objective */}
                          {note.objective && (
                            <div style={{ marginBottom: "10px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.68rem", fontWeight: 700, color: "#34d399", marginBottom: "4px" }}>
                                <span style={{ width: "3px", height: "12px", background: "#34d399", borderRadius: "2px", display: "inline-block" }} />
                                O — Objective
                              </div>
                              <div style={{ color: "#a1a1aa", fontSize: "0.7rem", lineHeight: 1.5, padding: "6px 10px", background: "rgba(9,9,11,0.5)", borderRadius: "6px", border: "1px solid rgba(63,63,70,0.25)", whiteSpace: "pre-wrap" }}>
                                {typeof note.objective === "string" ? note.objective : JSON.stringify(note.objective, null, 2)}
                              </div>
                            </div>
                          )}
                          {/* A — Assessment */}
                          {note.assessment && (
                            <div style={{ marginBottom: "10px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.68rem", fontWeight: 700, color: "#fbbf24", marginBottom: "4px" }}>
                                <span style={{ width: "3px", height: "12px", background: "#fbbf24", borderRadius: "2px", display: "inline-block" }} />
                                A — Assessment
                              </div>
                              <div style={{ color: "#a1a1aa", fontSize: "0.7rem", lineHeight: 1.5, padding: "6px 10px", background: "rgba(9,9,11,0.5)", borderRadius: "6px", border: "1px solid rgba(63,63,70,0.25)" }}>
                                {note.assessment}
                              </div>
                            </div>
                          )}
                          {/* P — Plan */}
                          {note.plan && (
                            <div>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.68rem", fontWeight: 700, color: "#60a5fa", marginBottom: "4px" }}>
                                <span style={{ width: "3px", height: "12px", background: "#60a5fa", borderRadius: "2px", display: "inline-block" }} />
                                P — Plan
                              </div>
                              <div style={{ color: "#a1a1aa", fontSize: "0.7rem", lineHeight: 1.5, padding: "6px 10px", background: "rgba(9,9,11,0.5)", borderRadius: "6px", border: "1px solid rgba(63,63,70,0.25)" }}>
                                {note.plan}
                              </div>
                            </div>
                          )}
                        </div>
                      </details>
                    ))}
                  </div>
                </div>
              ) : soapHistory && soapHistory.length === 0 ? (
                <div style={{ color: "#52525b", fontSize: "0.72rem", padding: "12px 0", textAlign: "center" }}>
                  No prior SOAP notes on file.
                </div>
              ) : null}
            </div>
          )}

          {/* ── Labs tab ── */}
          {activeTab === "labs" && (
            <LabsPanel
              patientId={patient?.id}
              timeblockId={tbId}
              orderedBy={vet?.name}
            />
          )}

          {/* ── Imaging tab ── */}
          {activeTab === "imaging" && (
            <div>
              {/* ── Owner-submitted photos ── */}
              {ownerPhotos === null ? (
                <div style={{ color: "#52525b", fontSize: "0.72rem", padding: "8px 0" }}>Loading images…</div>
              ) : ownerPhotos.length > 0 ? (
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ fontSize: "0.65rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ background: "rgba(16,185,129,0.12)", color: "#34d399", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "4px", padding: "1px 6px", fontSize: "0.6rem", fontWeight: 700 }}>OWNER</span>
                    Owner-Submitted Photos ({ownerPhotos.length})
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(80px, 1fr))", gap: "6px" }}>
                    {ownerPhotos.map((img: any) => (
                      <div
                        key={img.id}
                        onClick={() => setLightboxSrc(`data:${img.content_type ?? "image/jpeg"};base64,${img.data}`)}
                        style={{ cursor: "pointer", position: "relative" }}
                        title={img.caption || img.filename}
                      >
                        <img
                          src={`data:${img.content_type ?? "image/jpeg"};base64,${img.data}`}
                          alt={img.caption || "Owner photo"}
                          style={{
                            width: "100%", aspectRatio: "1", objectFit: "cover",
                            borderRadius: "7px", border: "1px solid rgba(63,63,70,0.5)",
                            transition: "transform 0.15s ease, border-color 0.15s ease",
                          }}
                          onMouseEnter={e => { (e.target as HTMLImageElement).style.transform = "scale(1.04)"; (e.target as HTMLImageElement).style.borderColor = "rgba(52,211,153,0.5)"; }}
                          onMouseLeave={e => { (e.target as HTMLImageElement).style.transform = "scale(1)"; (e.target as HTMLImageElement).style.borderColor = "rgba(63,63,70,0.5)"; }}
                        />
                        {img.caption && (
                          <div style={{ fontSize: "0.58rem", color: "#71717a", textAlign: "center", marginTop: "3px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {img.caption}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ padding: "10px 0 6px", color: "#52525b", fontSize: "0.72rem", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ opacity: 0.5 }}>📷</span> No owner photos submitted with intake
                </div>
              )}

              {/* ── Clinical imaging studies ── */}
              {(patient?.imaging_notes || item.job?.required_skills?.some((s: string) =>
                ["X-Ray","Ultrasound","Imaging"].includes(s))) ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ fontSize: "0.65rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
                    Clinical studies
                  </div>
                  {(item.job?.required_skills ?? []).filter((s: string) => ["X-Ray","Ultrasound","Imaging"].includes(s)).map((sk: string, i: number) => (
                    <div key={i} style={{
                      padding: "10px 14px", borderRadius: "8px",
                      background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                      display: "flex", alignItems: "center", gap: "10px", fontSize: "0.73rem",
                    }}>
                      <Image size={14} color="#818cf8" />
                      <div>
                        <div style={{ color: "#d4d4d8", fontWeight: 600 }}>{sk} — Today's Study</div>
                        <div style={{ color: "#52525b", fontSize: "0.65rem" }}>Results pending radiologist review</div>
                      </div>
                    </div>
                  ))}
                  {patient?.imaging_notes && (
                    <div style={{ padding: "10px 14px", borderRadius: "8px", background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)", fontSize: "0.73rem", color: "#a1a1aa" }}>
                      {patient.imaging_notes}
                    </div>
                  )}
                </div>
              ) : ownerPhotos?.length === 0 && (!patientStudies || patientStudies.length === 0) && (
                <div style={{ padding: "10px 0", textAlign: "center", color: "#52525b", fontSize: "0.75rem" }}>
                  No imaging studies for this appointment.
                </div>
              )}

              {/* ── Patient imaging history (historical studies) ── */}
              {patientStudies && patientStudies.length > 0 && (
                <div style={{ marginTop: "12px" }}>
                  <div style={{ fontSize: "0.65rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ background: "rgba(129,140,248,0.12)", color: "#a5b4fc", border: "1px solid rgba(129,140,248,0.25)", borderRadius: "4px", padding: "1px 6px", fontSize: "0.6rem", fontWeight: 700 }}>HISTORY</span>
                    Patient Imaging Studies ({patientStudies.length})
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {patientStudies.map((study: any, i: number) => {
                      const imgSrc = study.data
                        ? (study.data.startsWith("data:") ? study.data : `data:${study.content_type ?? "image/png"};base64,${study.data}`)
                        : null;
                      return (
                      <div key={study.id ?? i} style={{
                        padding: "10px 14px", borderRadius: "8px",
                        background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)",
                        fontSize: "0.73rem",
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "5px" }}>
                          <Image size={13} color="#818cf8" />
                          <span style={{ color: "#d4d4d8", fontWeight: 600, flex: 1 }}>
                            {study.caption || study.filename || "Study"}
                          </span>
                          <span style={{ color: "#52525b", fontSize: "0.65rem", fontVariantNumeric: "tabular-nums" }}>
                            {study.study_date || study.submitted_at?.slice(0, 10) || ""}
                          </span>
                        </div>
                        {/* Radiograph thumbnail */}
                        {imgSrc && (
                          <div
                            onClick={() => setLightboxSrc(imgSrc)}
                            style={{ cursor: "pointer", marginBottom: "6px", position: "relative" }}
                          >
                            <img
                              src={imgSrc}
                              alt={study.caption || "Radiograph"}
                              style={{
                                width: "100%", maxHeight: "220px", objectFit: "contain",
                                borderRadius: "6px", border: "1px solid rgba(63,63,70,0.5)",
                                background: "#000",
                                transition: "border-color 0.15s ease",
                              }}
                              onMouseEnter={e => { (e.target as HTMLImageElement).style.borderColor = "rgba(129,140,248,0.5)"; }}
                              onMouseLeave={e => { (e.target as HTMLImageElement).style.borderColor = "rgba(63,63,70,0.5)"; }}
                            />
                            <span style={{
                              position: "absolute", bottom: "8px", right: "8px",
                              background: "rgba(0,0,0,0.7)", color: "#a1a1aa",
                              fontSize: "0.58rem", padding: "2px 6px", borderRadius: "4px",
                            }}>
                              Click to enlarge
                            </span>
                          </div>
                        )}
                        {study.modality && (
                          <span style={{
                            display: "inline-block", fontSize: "0.58rem", fontWeight: 700,
                            padding: "1px 6px", borderRadius: "4px", marginBottom: "5px",
                            background: study.modality === "Radiograph" ? "rgba(96,165,250,0.1)" : "rgba(192,132,252,0.1)",
                            color: study.modality === "Radiograph" ? "#60a5fa" : "#c084fc",
                            border: `1px solid ${study.modality === "Radiograph" ? "rgba(96,165,250,0.25)" : "rgba(192,132,252,0.25)"}`,
                          }}>
                            {study.modality}
                          </span>
                        )}
                        {study.report_text && (
                          <details style={{ marginTop: "4px" }}>
                            <summary style={{ color: "#71717a", fontSize: "0.68rem", cursor: "pointer", userSelect: "none" }}>
                              View Report
                            </summary>
                            <pre style={{
                              marginTop: "6px", padding: "10px 12px", borderRadius: "6px",
                              background: "rgba(9,9,11,0.6)", border: "1px solid rgba(63,63,70,0.3)",
                              color: "#a1a1aa", fontSize: "0.65rem", lineHeight: 1.5,
                              whiteSpace: "pre-wrap", wordBreak: "break-word",
                              fontFamily: "inherit", maxHeight: "200px", overflow: "auto",
                            }}>
                              {study.report_text}
                            </pre>
                          </details>
                        )}
                      </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Lightbox */}
          {lightboxSrc && (
            <div
              onClick={() => setLightboxSrc(null)}
              style={{
                position: "fixed", inset: 0, zIndex: 100,
                background: "rgba(0,0,0,0.85)",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "zoom-out",
              }}
            >
              <img
                src={lightboxSrc}
                alt="Owner photo"
                style={{ maxWidth: "90vw", maxHeight: "85vh", borderRadius: "12px", boxShadow: "0 8px 48px rgba(0,0,0,0.8)" }}
                onClick={e => e.stopPropagation()}
              />
              <button
                onClick={() => setLightboxSrc(null)}
                style={{
                  position: "fixed", top: "20px", right: "20px",
                  background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "50%", width: "36px", height: "36px",
                  color: "white", fontSize: "18px", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >×</button>
            </div>
          )}

          {/* ── Follow-Up tab ── */}
          {activeTab === "followup" && (
            <div>
              <div style={{
                padding: "14px", borderRadius: "10px", marginBottom: "10px",
                background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                  <span style={{ fontSize: "0.6rem", fontWeight: 700, color: "#818cf8", textTransform: "uppercase", letterSpacing: "0.07em" }}>AI Recommendation</span>
                  <span style={{ fontSize: "0.6rem", color: "#52525b", background: "rgba(99,102,241,0.15)", padding: "1px 6px", borderRadius: "4px" }}>based on {procedure}</span>
                </div>
                <p style={{ margin: "0 0 4px", color: "#d4d4d8", fontSize: "0.78rem", fontWeight: 600 }}>
                  {followUp.note}
                </p>
                <p style={{ margin: 0, color: "#71717a", fontSize: "0.7rem" }}>
                  Suggested interval: <span style={{ color: "#a5b4fc" }}>{followUp.interval}</span>
                </p>
              </div>

              <button
                onClick={() => handleSuggestMessage(followUp.prompt)}
                style={{
                  width: "100%", padding: "10px 14px", borderRadius: "10px",
                  background: "linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(139,92,246,0.15) 100%)",
                  border: "1px solid rgba(99,102,241,0.35)", color: "#a5b4fc",
                  fontSize: "0.78rem", fontWeight: 700, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(99,102,241,0.3) 0%,rgba(139,92,246,0.22) 100%)"; e.currentTarget.style.borderColor = "rgba(99,102,241,0.55)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(99,102,241,0.2) 0%,rgba(139,92,246,0.15) 100%)"; e.currentTarget.style.borderColor = "rgba(99,102,241,0.35)"; }}
              >
                <CalendarPlus size={14} />
                Schedule via Agent — "{followUp.prompt.slice(0, 48)}…"
              </button>
            </div>
          )}

          {/* ── Breed Intelligence tab ── */}
          {activeTab === "breed" && patient?.id && (
            <div style={{ paddingTop: "4px" }}>
              <BreedAlertsPanel
                patientId={patient.id}
                patientName={patient.name}
                breed={patient.breed}
              />
            </div>
          )}

          {/* ── Preventive Care tab ── */}
          {activeTab === "care" && patient?.id && (
            <div style={{ paddingTop: "4px" }}>
              <CareTimelinePanel
                patientId={patient.id}
                patientName={patient.name}
                timeblockId={tbId}
                onLogEntry={onLogEntry}
              />
            </div>
          )}

          {/* ── Prescriptions tab ── */}
          {activeTab === "rx" && patient?.id && (
            <div style={{ paddingTop: "4px" }}>
              <PrescriptionPanel
                patientId={patient.id}
                patientName={patient.name}
                timeblockId={tbId}
                issuedBy={vet?.name}
                onLogEntry={onLogEntry}
              />
            </div>
          )}

          {/* ── Action buttons ── */}
          <div style={{ display: "flex", gap: "8px", marginTop: "14px" }}>
            {!isComplete && (
              <button onClick={handleComplete} style={{
                flex: 1, padding: "8px", borderRadius: "8px",
                background: "rgba(16,185,129,0.1)", color: "#10b981",
                border: "1px solid rgba(16,185,129,0.25)", fontSize: "0.75rem",
                fontWeight: 600, cursor: "pointer", display: "flex",
                alignItems: "center", justifyContent: "center", gap: "6px",
                transition: "background 0.15s ease",
              }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(16,185,129,0.18)"}
              onMouseLeave={e => e.currentTarget.style.background = "rgba(16,185,129,0.1)"}
              >
                <CheckCircle2 size={13} /> Mark Complete
              </button>
            )}
            {isComplete && (
              <div style={{ flex: 1, padding: "8px", borderRadius: "8px", background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", color: "#10b981", fontSize: "0.75rem", fontWeight: 600, textAlign: "center" }}>
                ✓ Appointment Complete
              </div>
            )}
          </div>
        </div>
      </div>
    </div>

    {/* SOAP panel slide-in */}
    <div style={{
      position: "fixed", top: 0, right: soapOpen ? 0 : "-440px",
      width: "420px", height: "100%", zIndex: 50,
      transition: "right 0.3s cubic-bezier(0.4,0,0.2,1)",
      boxShadow: soapOpen ? "-8px 0 32px rgba(0,0,0,0.5)" : "none",
    }}>
      {soapOpen && (
        <SoapWorkspace
          item={item}
          patient={patient}
          onClose={() => setSoapOpen(false)}
          onLogEntry={onLogEntry}
        />
      )}
    </div>
    </>
  );
}
