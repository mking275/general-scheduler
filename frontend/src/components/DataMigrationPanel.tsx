"use client";

import { useState, useRef, useCallback } from "react";
import {
  Upload, CheckCircle2, AlertTriangle, Download, Loader,
  Database, ChevronRight, ChevronDown, RefreshCw, Play
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

type Phase = "owners" | "patients" | "visits" | "vaccines" | "rx" | "done" | "starting" | "error" | "";

const PHASE_ORDER: Phase[] = ["owners", "patients", "visits", "vaccines", "rx", "done"];

function PhaseBar({ run }: { run: any }) {
  const currentPhase = run?.phase as Phase;
  const isRunning = run?.status === "running";
  const isDone = run?.status === "completed" || currentPhase === "done";
  const isFailed = run?.status === "failed";

  const PHASE_LABELS: Record<string, string> = {
    owners: "Owners",
    patients: "Patients",
    visits: "Visits",
    vaccines: "Vaccines",
    rx: "Prescriptions",
    done: "Complete",
  };

  const currentIdx = PHASE_ORDER.indexOf(currentPhase);

  return (
    <div style={{ marginTop: "14px" }}>
      <div style={{ fontSize: "0.65rem", color: "#52525b", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
        Migration Progress
      </div>
      <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
        {PHASE_ORDER.filter(p => p !== "done").map((phase, idx) => {
          const passed = isDone || (currentIdx > idx);
          const active = phase === currentPhase && isRunning;
          return (
            <div key={phase} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
              <div style={{
                width: "100%", height: "4px", borderRadius: "2px",
                background: isFailed && active ? "rgba(248,113,113,0.6)"
                  : passed ? "rgba(52,211,153,0.7)"
                  : active ? "rgba(129,140,248,0.7)"
                  : "rgba(63,63,70,0.4)",
                transition: "background 0.3s ease",
              }} />
              <span style={{
                fontSize: "0.58rem", color: passed ? "#34d399" : active ? "#a5b4fc" : "#52525b",
                fontWeight: active ? 700 : 400,
              }}>
                {PHASE_LABELS[phase]}
                {active && " ⟳"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MigrationReport({ run, flags }: { run: any; flags: any[] }) {
  const stats = [
    { label: "Owners",       val: run.imported_owners   },
    { label: "Patients",     val: run.imported_patients },
    { label: "Visits",       val: run.imported_visits   },
    { label: "Vaccines",     val: run.imported_vaccines },
    { label: "Prescriptions",val: run.imported_rx       },
  ];

  return (
    <div style={{
      marginTop: "14px", padding: "14px", borderRadius: "10px",
      background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.4)",
    }}>
      <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "#d4d4d8", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
        <CheckCircle2 size={13} color="#34d399" /> Migration Report
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "8px" }}>
        {stats.map(s => (
          <div key={s.label} style={{
            padding: "8px", borderRadius: "7px",
            background: "rgba(24,24,27,0.6)", border: "1px solid rgba(63,63,70,0.3)",
            textAlign: "center",
          }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#f4f4f5", lineHeight: 1 }}>
              {(s.val ?? 0).toLocaleString()}
            </div>
            <div style={{ fontSize: "0.6rem", color: "#52525b", marginTop: "3px" }}>{s.label}</div>
          </div>
        ))}
      </div>
      {run.flagged_count > 0 && (
        <div style={{
          marginTop: "10px", padding: "8px 12px", borderRadius: "7px",
          background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.25)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "7px", color: "#fbbf24", fontSize: "0.73rem", fontWeight: 600 }}>
            <AlertTriangle size={13} /> {run.flagged_count} records flagged
          </div>
          <a
            href={`${API}/api/migration/${run.id}/flags/download`}
            download
            style={{
              padding: "5px 10px", borderRadius: "6px",
              background: "rgba(251,191,36,0.12)", border: "1px solid rgba(251,191,36,0.3)",
              color: "#fbbf24", fontSize: "0.68rem", fontWeight: 700,
              textDecoration: "none", display: "flex", alignItems: "center", gap: "5px",
            }}
          >
            <Download size={11} /> Download CSV
          </a>
        </div>
      )}
    </div>
  );
}

interface Props {
  onLog?: (msg: string) => void;
}

export default function DataMigrationPanel({ onLog }: Props) {
  const [sourceSystem, setSourceSystem] = useState<"avimark" | "cornerstone">("avimark");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const log = (msg: string) => onLog?.(msg);

  const startPolling = (rid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/migration/${rid}`);
        if (!res.ok) return;
        const data = await res.json();
        setRun(data);

        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollRef.current!);
          if (data.flagged_count > 0) {
            const fRes = await fetch(`${API}/api/migration/${rid}/flags`);
            if (fRes.ok) setFlags(await fRes.json());
          }
        }
      } catch {}
    }, 800);
  };

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith(".zip")) {
      setError("Please upload a .zip file");
      return;
    }
    setError(null);
    setUploading(true);
    setRun(null);
    setFlags([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(
        `${API}/api/migration/upload?source_system=${sourceSystem}`,
        { method: "POST", body: formData }
      );
      if (!res.ok) {
        const e = await res.json();
        setError(e.detail || "Upload failed");
        setUploading(false);
        return;
      }
      const data = await res.json();
      setRunId(data.run_id);
      log(`MIGRATION AGENT: ${sourceSystem} migration started · run ${data.run_id}`);
      startPolling(data.run_id);
    } catch {
      setError("Network error — check backend");
    }
    setUploading(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleSeedAvimark = async () => {
    setSeedLoading(true);
    setError(null);
    setRun(null);
    setFlags([]);
    try {
      const res = await fetch(`${API}/api/migration/seed-avimark-fixture`, { method: "POST" });
      if (!res.ok) {
        const e = await res.json();
        setError(e.detail || "Fixture seed failed");
        setSeedLoading(false);
        return;
      }
      const data = await res.json();
      setRunId(data.run_id);
      log(`MIGRATION AGENT: Avimark 847-patient fixture migration started`);
      startPolling(data.run_id);
    } catch {
      setError("Network error");
    }
    setSeedLoading(false);
  };

  const isDone = run?.status === "completed";
  const isFailed = run?.status === "failed";
  const isRunning = run?.status === "running" || uploading;

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800, color: "#f4f4f5" }}>
          Data Migration
        </h2>
        <p style={{ margin: "4px 0 0", fontSize: "0.72rem", color: "#71717a" }}>
          Import patient records from your previous practice management system
        </p>
      </div>

      {/* Source system selector */}
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontSize: "0.65rem", color: "#71717a", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Source System
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {(["avimark", "cornerstone"] as const).map((sys) => (
            <button
              key={sys}
              onClick={() => setSourceSystem(sys)}
              style={{
                padding: "7px 14px", borderRadius: "8px", fontSize: "0.73rem", fontWeight: 600,
                background: sourceSystem === sys ? "rgba(96,165,250,0.15)" : "rgba(39,39,42,0.6)",
                border: `1px solid ${sourceSystem === sys ? "rgba(96,165,250,0.4)" : "rgba(63,63,70,0.4)"}`,
                color: sourceSystem === sys ? "#60a5fa" : "#71717a",
                cursor: "pointer", transition: "all 0.15s ease", textTransform: "capitalize",
              }}
            >
              {sys}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          padding: "28px 20px", borderRadius: "12px", border: `2px dashed ${dragging ? "rgba(96,165,250,0.6)" : "rgba(63,63,70,0.4)"}`,
          background: dragging ? "rgba(96,165,250,0.04)" : "rgba(24,24,27,0.4)",
          cursor: "pointer", textAlign: "center", transition: "all 0.2s ease",
          marginBottom: "12px",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".zip"
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
        {uploading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
            <Loader size={22} color="#60a5fa" style={{ animation: "spin 1s linear infinite" }} />
            <span style={{ color: "#60a5fa", fontSize: "0.78rem", fontWeight: 600 }}>Uploading…</span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
            <Upload size={22} color={dragging ? "#60a5fa" : "#52525b"} />
            <div>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: dragging ? "#60a5fa" : "#d4d4d8" }}>
                Drop your {sourceSystem} export here
              </div>
              <div style={{ fontSize: "0.68rem", color: "#52525b", marginTop: "3px" }}>
                or click to browse · .zip files only
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Demo fixture button */}
      <div style={{ marginBottom: "16px", padding: "12px 14px", borderRadius: "10px", background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.35)" }}>
        <div style={{ fontSize: "0.65rem", color: "#52525b", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Demo Mode
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: "0.73rem", color: "#a1a1aa" }}>
            Load Avimark 847-patient fixture (SC-INT-004)
          </div>
          <button
            onClick={handleSeedAvimark}
            disabled={seedLoading || isRunning}
            style={{
              padding: "7px 14px", borderRadius: "8px",
              background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.35)",
              color: "#60a5fa", fontSize: "0.72rem", fontWeight: 700,
              cursor: seedLoading || isRunning ? "not-allowed" : "pointer",
              display: "flex", alignItems: "center", gap: "6px",
              opacity: seedLoading || isRunning ? 0.6 : 1,
              transition: "all 0.15s ease",
            }}
          >
            {seedLoading ? <Loader size={11} style={{ animation: "spin 1s linear infinite" }} /> : <Play size={11} />}
            Run Demo
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          marginBottom: "12px", padding: "10px 14px", borderRadius: "8px",
          background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.25)",
          color: "#f87171", fontSize: "0.73rem", display: "flex", alignItems: "center", gap: "7px",
        }}>
          <AlertTriangle size={13} /> {error}
        </div>
      )}

      {/* Migration run status */}
      {run && (
        <div style={{
          padding: "14px", borderRadius: "12px",
          background: isDone ? "rgba(52,211,153,0.04)" : isFailed ? "rgba(248,113,113,0.04)" : "rgba(39,39,42,0.5)",
          border: `1px solid ${isDone ? "rgba(52,211,153,0.2)" : isFailed ? "rgba(248,113,113,0.2)" : "rgba(63,63,70,0.4)"}`,
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {isRunning && <Loader size={13} color="#818cf8" style={{ animation: "spin 1s linear infinite" }} />}
              {isDone && <CheckCircle2 size={13} color="#34d399" />}
              {isFailed && <AlertTriangle size={13} color="#f87171" />}
              <span style={{ fontSize: "0.78rem", fontWeight: 700, color: isDone ? "#34d399" : isFailed ? "#f87171" : "#d4d4d8" }}>
                {isDone ? "Migration Complete" : isFailed ? "Migration Failed" : `Importing ${run.phase}…`}
              </span>
            </div>
            <span style={{ fontSize: "0.63rem", color: "#52525b" }}>
              {run.source_system?.toUpperCase()}
            </span>
          </div>

          {run.error_message && (
            <div style={{ fontSize: "0.7rem", color: "#f87171", marginTop: "4px" }}>{run.error_message}</div>
          )}

          <PhaseBar run={run} />

          {isDone && <MigrationReport run={run} flags={flags} />}
        </div>
      )}

      {/* Running indicator with live counts */}
      {run && isRunning && (
        <div style={{ marginTop: "12px", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
          {[
            { label: "Owners", val: run.imported_owners },
            { label: "Patients", val: run.imported_patients },
            { label: "Visits", val: run.imported_visits },
          ].map(s => (
            <div key={s.label} style={{
              padding: "8px", borderRadius: "7px", textAlign: "center",
              background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.35)",
            }}>
              <div style={{ fontSize: "1rem", fontWeight: 800, color: "#818cf8" }}>
                {(s.val ?? 0).toLocaleString()}
              </div>
              <div style={{ fontSize: "0.6rem", color: "#52525b" }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
