"use client";

import { useState, useRef } from "react";
import { Camera, X, Upload, Image as ImageIcon } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface IntakePanelProps {
  timeblockId: string;
  patientId?: string;
  role: "front_desk" | "vet_tech" | "vet";
  intakeStatus: string;
  onStatusChange: (status: string) => void;
  onLogEntry?: (entry: string) => void;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  not_started: { label: "Intake not sent",  color: "#71717a" },
  pending:     { label: "⏳ Pending reply", color: "#fbbf24" },
  received:    { label: "✓ Brief received", color: "#4ade80" },
};

/* Resize + base64-encode a File for storage */
async function fileToBase64(file: File): Promise<{ filename: string; content_type: string; data: string; caption: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({
      filename: file.name,
      content_type: file.type || "image/jpeg",
      data: (reader.result as string).split(",")[1], // strip data URL prefix
      caption: file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "),
    });
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function IntakePanel({
  timeblockId, patientId, role, intakeStatus, onStatusChange, onLogEntry,
}: IntakePanelProps) {
  const [ownerResponse, setOwnerResponse] = useState("");
  const [brief, setBrief]     = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [sentMessage, setSentMessage] = useState<string | null>(null);

  // Photo state
  const [pendingPhotos, setPendingPhotos] = useState<Array<{
    file: File; previewUrl: string; caption: string;
  }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const statusCfg = STATUS_LABELS[intakeStatus] ?? STATUS_LABELS.not_started;

  /* ── Send questionnaire ── */
  const sendIntake = async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/intake/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeblock_id: timeblockId }),
    });
    if (res.ok) {
      const data = await res.json();
      setSentMessage(data.message ?? null);
      onStatusChange("pending");
      onLogEntry?.("INTAKE AGENT: Questionnaire with photo prompt sent to owner (simulated)");
    }
    setLoading(false);
  };

  /* ── Photo picker ── */
  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const newPhotos = Array.from(files)
      .filter(f => f.type.startsWith("image/"))
      .slice(0, 5 - pendingPhotos.length) // max 5 total
      .map(file => ({
        file,
        previewUrl: URL.createObjectURL(file),
        caption: file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "),
      }));
    setPendingPhotos(prev => [...prev, ...newPhotos]);
  };

  const removePhoto = (idx: number) => {
    setPendingPhotos(prev => {
      URL.revokeObjectURL(prev[idx].previewUrl);
      return prev.filter((_, i) => i !== idx);
    });
  };

  /* ── Submit response + photos ── */
  const submitResponse = async () => {
    if (!ownerResponse.trim() && pendingPhotos.length === 0) return;
    setLoading(true);

    // 1. Parse symptoms from text
    if (ownerResponse.trim()) {
      const res = await fetch(`${API}/api/intake/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timeblock_id: timeblockId, owner_response: ownerResponse }),
      });
      if (res.ok) {
        const data = await res.json();
        setBrief(data);
        onLogEntry?.(`INTAKE AGENT: Parsed → ${data.symptoms?.map((s: any) => `${s.name} (${s.duration_days}d, ${s.severity})`).join(", ") || "no specific symptoms"}`);
        if (data.suggested_focus?.length)
          onLogEntry?.(`INTAKE AGENT: Suggested focus: ${data.suggested_focus.join(", ")}`);
      }
    }

    // 2. Upload photos if any
    if (pendingPhotos.length > 0) {
      try {
        const encoded = await Promise.all(pendingPhotos.map(p => fileToBase64(p.file)));
        const imgRes = await fetch(`${API}/api/intake/${timeblockId}/images`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ images: encoded, patient_id: patientId }),
        });
        if (imgRes.ok) {
          const imgData = await imgRes.json();
          onLogEntry?.(`INTAKE AGENT: ${imgData.saved} owner photo(s) uploaded — visible in Imaging tab`);
        }
      } catch {}
    }

    onStatusChange("received");
    onLogEntry?.("INTAKE AGENT: Pre-Exam Brief saved ✓");
    setLoading(false);
  };

  // Vet view: only show if received
  if (role === "vet" && intakeStatus !== "received") return null;

  return (
    <div style={{
      marginTop: "10px", background: "rgba(23,23,23,0.7)",
      border: "1px solid rgba(63,63,70,0.5)", borderRadius: "10px", padding: "10px 12px",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#71717a", letterSpacing: "0.06em" }}>PRE-VISIT INTAKE</span>
        <span style={{ fontSize: "0.7rem", color: statusCfg.color, fontWeight: 600 }}>{statusCfg.label}</span>
      </div>

      {/* ── NOT STARTED: Send button ── */}
      {intakeStatus === "not_started" && role === "front_desk" && (
        <button onClick={sendIntake} disabled={loading} style={{
          width: "100%", padding: "7px", borderRadius: "7px",
          background: "rgba(59,130,246,0.1)", color: "#60a5fa",
          border: "1px solid rgba(59,130,246,0.25)", fontSize: "0.75rem",
          fontWeight: 600, cursor: "pointer", transition: "background 0.15s ease",
        }}>
          {loading ? "Sending…" : "📋 Send Intake Questionnaire"}
        </button>
      )}

      {/* ── PENDING: Show sent message + owner reply panel ── */}
      {intakeStatus === "pending" && role === "front_desk" && (
        <div>
          {/* Show the actual message sent to owner */}
          {sentMessage && (
            <div style={{
              marginBottom: "10px", padding: "10px 12px", borderRadius: "8px",
              background: "rgba(59,130,246,0.05)", border: "1px solid rgba(59,130,246,0.18)",
              fontSize: "0.7rem", color: "#a1a1aa", lineHeight: 1.5,
            }}>
              <div style={{ fontSize: "0.6rem", color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "5px" }}>
                📤 Message sent to owner
              </div>
              {sentMessage}
            </div>
          )}

          <div style={{ fontSize: "0.72rem", color: "#a1a1aa", marginBottom: "6px" }}>
            Simulate owner response:
          </div>

          {/* Text response */}
          <textarea
            value={ownerResponse}
            onChange={e => setOwnerResponse(e.target.value)}
            placeholder="e.g. He's been lethargic for 3 days and not eating..."
            rows={3}
            style={{
              width: "100%", background: "#0c0c0e", color: "#d4d4d8",
              border: "1px solid rgba(63,63,70,0.6)", borderRadius: "7px",
              padding: "8px 10px", fontSize: "0.78rem", resize: "vertical",
              fontFamily: "inherit", boxSizing: "border-box",
            }}
          />

          {/* Photo attachment area */}
          <div style={{ marginTop: "8px" }}>
            <div style={{ fontSize: "0.65rem", color: "#52525b", marginBottom: "6px", display: "flex", alignItems: "center", gap: "5px" }}>
              <Camera size={11} /> Attach owner photos (up to 5)
            </div>

            {/* Existing previews */}
            {pendingPhotos.length > 0 && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "8px" }}>
                {pendingPhotos.map((p, i) => (
                  <div key={i} style={{ position: "relative", width: "64px", height: "64px" }}>
                    <img
                      src={p.previewUrl}
                      alt={p.caption}
                      style={{ width: "64px", height: "64px", objectFit: "cover", borderRadius: "6px", border: "1px solid rgba(63,63,70,0.5)" }}
                    />
                    <button
                      onClick={() => removePhoto(i)}
                      style={{
                        position: "absolute", top: "-4px", right: "-4px",
                        width: "16px", height: "16px", borderRadius: "50%",
                        background: "#ef4444", border: "none", color: "white",
                        fontSize: "9px", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center", padding: 0,
                      }}
                    >
                      <X size={9} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add photo button */}
            {pendingPhotos.length < 5 && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  style={{ display: "none" }}
                  onChange={e => handleFiles(e.target.files)}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    width: "100%", padding: "6px", borderRadius: "7px",
                    background: "rgba(16,185,129,0.05)", border: "1px dashed rgba(16,185,129,0.25)",
                    color: "#34d399", fontSize: "0.7rem", cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = "rgba(16,185,129,0.1)"; e.currentTarget.style.borderStyle = "solid"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "rgba(16,185,129,0.05)"; e.currentTarget.style.borderStyle = "dashed"; }}
                >
                  <Upload size={11} /> Add Photos
                </button>
              </>
            )}
          </div>

          {/* Submit */}
          <button
            onClick={submitResponse}
            disabled={loading || (!ownerResponse.trim() && pendingPhotos.length === 0)}
            style={{
              marginTop: "8px", width: "100%", padding: "7px", borderRadius: "7px",
              background: (ownerResponse.trim() || pendingPhotos.length > 0) ? "rgba(99,102,241,0.15)" : "rgba(63,63,70,0.2)",
              color: (ownerResponse.trim() || pendingPhotos.length > 0) ? "#818cf8" : "#52525b",
              border: `1px solid ${(ownerResponse.trim() || pendingPhotos.length > 0) ? "rgba(99,102,241,0.3)" : "rgba(63,63,70,0.3)"}`,
              fontSize: "0.75rem", fontWeight: 600,
              cursor: (ownerResponse.trim() || pendingPhotos.length > 0) ? "pointer" : "not-allowed",
              transition: "background 0.15s ease",
            }}
          >
            {loading ? "Processing…" : `Submit Response${pendingPhotos.length > 0 ? ` + ${pendingPhotos.length} photo(s)` : ""} →`}
          </button>
        </div>
      )}

      {/* ── RECEIVED: Show brief ── */}
      {intakeStatus === "received" && brief && (
        <div style={{ fontSize: "0.78rem" }}>
          <div style={{ color: "#a1a1aa", fontWeight: 600, marginBottom: "5px" }}>
            Chief Complaint: <span style={{ color: "#e4e4e7" }}>{brief.chief_complaint}</span>
          </div>
          {brief.symptoms?.length > 0 && (
            <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginBottom: "5px" }}>
              {brief.symptoms.map((s: any, i: number) => (
                <span key={i} style={{
                  background: "rgba(99,102,241,0.12)", color: "#a5b4fc",
                  border: "1px solid rgba(99,102,241,0.25)", borderRadius: "12px",
                  padding: "2px 8px", fontSize: "0.68rem", fontWeight: 600,
                }}>
                  {s.name} · {s.duration_days}d · {s.severity}
                </span>
              ))}
            </div>
          )}
          {brief.owner_verbatim && (
            <div style={{ color: "#71717a", fontStyle: "italic", marginBottom: "5px", borderLeft: "2px solid rgba(99,102,241,0.3)", paddingLeft: "8px" }}>
              "{brief.owner_verbatim}"
            </div>
          )}
          {brief.suggested_focus?.length > 0 && (
            <div style={{ color: "#a1a1aa" }}>
              Focus: {brief.suggested_focus.map((f: string) => (
                <span key={f} style={{ background: "rgba(16,185,129,0.1)", color: "#34d399", borderRadius: "4px", padding: "0 5px", marginLeft: "4px", fontSize: "0.68rem", fontWeight: 600, border: "1px solid rgba(16,185,129,0.2)" }}>{f}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Received but brief not loaded locally — fetch it */}
      {intakeStatus === "received" && !brief && (
        <BriefLoader timeblockId={timeblockId} onLoaded={setBrief} />
      )}
    </div>
  );
}

function BriefLoader({ timeblockId, onLoaded }: { timeblockId: string; onLoaded: (b: any) => void }) {
  const [fetched, setFetched] = useState(false);
  if (!fetched) {
    fetch(`${API}/api/intake/${timeblockId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && d.status === "received") { onLoaded(d); setFetched(true); } })
      .catch(() => {});
    setFetched(true);
  }
  return <div style={{ color: "#4ade80", fontSize: "0.75rem" }}>✓ Pre-Exam Brief on file</div>;
}
