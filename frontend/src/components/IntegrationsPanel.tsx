"use client";

import { useState, useEffect, useRef } from "react";
import {
  Wifi, WifiOff, Clock, Shield, Trash2, FlaskConical, Radio,
  ChevronDown, ChevronUp, Settings, CheckCircle2, AlertTriangle,
  RefreshCw, Eye, EyeOff, Loader, Plus, XCircle
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: React.ReactNode; label: string; color: string; bg: string; border: string }> = {
    connected:    { icon: <Wifi size={10} />,      label: "Connected",     color: "#34d399", bg: "rgba(52,211,153,0.12)",  border: "rgba(52,211,153,0.3)"  },
    degraded:     { icon: <AlertTriangle size={10}/>, label: "Degraded",   color: "#fbbf24", bg: "rgba(251,191,36,0.12)", border: "rgba(251,191,36,0.3)"  },
    disconnected: { icon: <WifiOff size={10} />,   label: "Disconnected",  color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.3)" },
    unconfigured: { icon: <Clock size={10} />,     label: "Not Configured",color: "#71717a", bg: "rgba(113,113,122,0.1)",  border: "rgba(113,113,122,0.2)" },
  };
  const c = config[status] ?? config.unconfigured;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "4px",
      padding: "2px 8px", borderRadius: "10px", fontSize: "0.62rem", fontWeight: 700,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
    }}>
      {c.icon}{c.label}
    </span>
  );
}

// ── Module colour map ─────────────────────────────────────────────────────────

const MODULE_COLORS: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  labs:      { color: "#818cf8", bg: "rgba(129,140,248,0.1)",  icon: <FlaskConical size={14} /> },
  imaging:   { color: "#c084fc", bg: "rgba(192,132,252,0.1)", icon: <Radio size={14} />       },
  comms:     { color: "#34d399", bg: "rgba(52,211,153,0.1)",  icon: <Wifi size={14} />        },
  payments:  { color: "#fbbf24", bg: "rgba(251,191,36,0.1)",  icon: <Shield size={14} />      },
  migration: { color: "#60a5fa", bg: "rgba(96,165,250,0.1)",  icon: <Settings size={14} />    },
  core:      { color: "#a1a1aa", bg: "rgba(161,161,170,0.1)", icon: <Settings size={14} />    },
};

// ── Credential form ───────────────────────────────────────────────────────────

function CredentialForm({
  integration,
  onSave,
  onCancel,
}: {
  integration: any;
  onSave: (creds: Record<string, string>) => void;
  onCancel: () => void;
}) {
  const [fields, setFields] = useState<Record<string, string>>(
    Object.fromEntries((integration.required_keys ?? []).map((k: string) => [k, ""]))
  );
  const [show, setShow] = useState<Record<string, boolean>>({});

  const handleChange = (key: string, val: string) =>
    setFields((prev) => ({ ...prev, [key]: val }));

  const toggleShow = (key: string) =>
    setShow((prev) => ({ ...prev, [key]: !prev[key] }));

  const allFilled = Object.values(fields).every((v) => v.trim().length > 0);

  return (
    <div style={{
      marginTop: "10px", padding: "14px", borderRadius: "10px",
      background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
      display: "flex", flexDirection: "column", gap: "10px",
    }}>
      <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#818cf8", textTransform: "uppercase", letterSpacing: "0.07em" }}>
        Configure {integration.name}
      </div>

      {(integration.required_keys ?? []).map((key: string) => (
        <div key={key} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "0.65rem", color: "#71717a", fontWeight: 600 }}>{key}</label>
          <div style={{ position: "relative" }}>
            <input
              type={show[key] ? "text" : "password"}
              value={fields[key] ?? ""}
              onChange={(e) => handleChange(key, e.target.value)}
              placeholder={`Enter ${key}`}
              style={{
                width: "100%", padding: "7px 36px 7px 10px", borderRadius: "7px",
                background: "#18181b", border: "1px solid rgba(63,63,70,0.6)",
                color: "#f4f4f5", fontSize: "0.75rem", outline: "none",
                boxSizing: "border-box",
              }}
            />
            <button
              onClick={() => toggleShow(key)}
              style={{
                position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)",
                background: "transparent", border: "none", cursor: "pointer", color: "#52525b",
                display: "flex", alignItems: "center",
              }}
            >
              {show[key] ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          </div>
        </div>
      ))}

      {(integration.required_keys ?? []).length === 0 && (
        <div style={{ fontSize: "0.73rem", color: "#71717a" }}>
          No credentials required — file upload only.
        </div>
      )}

      <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
        {(integration.required_keys ?? []).length > 0 && (
          <button
            onClick={() => allFilled && onSave(fields)}
            disabled={!allFilled}
            style={{
              flex: 1, padding: "8px", borderRadius: "8px",
              background: allFilled ? "rgba(129,140,248,0.2)" : "rgba(63,63,70,0.2)",
              border: `1px solid ${allFilled ? "rgba(129,140,248,0.4)" : "rgba(63,63,70,0.3)"}`,
              color: allFilled ? "#a5b4fc" : "#52525b",
              fontSize: "0.73rem", fontWeight: 700, cursor: allFilled ? "pointer" : "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
              transition: "all 0.15s ease",
            }}
          >
            <CheckCircle2 size={13} /> Save &amp; Test
          </button>
        )}
        <button
          onClick={onCancel}
          style={{
            padding: "8px 16px", borderRadius: "8px", background: "transparent",
            border: "1px solid rgba(63,63,70,0.4)", color: "#71717a",
            fontSize: "0.73rem", cursor: "pointer",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Integration card ──────────────────────────────────────────────────────────

function IntegrationCard({
  integration,
  onRefresh,
  onLog,
}: {
  integration: any;
  onRefresh: () => void;
  onLog: (msg: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [inline, setInline] = useState<{ type: "error" | "success"; msg: string } | null>(null);

  const mod = MODULE_COLORS[integration.module] ?? MODULE_COLORS.core;
  const isConfigured = integration.status !== "unconfigured";

  const handleSave = async (creds: Record<string, string>) => {
    setTesting(true);
    setInline(null);
    try {
      const res = await fetch(`${API}/api/integrations/${integration.id}/configure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credentials: creds }),
      });
      const data = await res.json();
      if (data.status === "connected") {
        setInline({ type: "success", msg: `Connected · ${data.latency_ms}ms` });
        onLog(`CREDENTIALS AGENT: ${integration.name} configured · connectivity test passed`);
      } else {
        setInline({ type: "error", msg: data.error_message || "Connection failed" });
        onLog(`CREDENTIALS AGENT: ${integration.name} — ${data.error_message}`);
      }
      setConfiguring(false);
    } catch {
      setInline({ type: "error", msg: "Network error — check backend" });
    }
    setTesting(false);
    onRefresh();
  };

  const handleTest = async () => {
    setTesting(true);
    setInline(null);
    try {
      const res = await fetch(`${API}/api/integrations/${integration.id}/test`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        setInline({ type: "error", msg: err.detail || "Test failed" });
      } else {
        const data = await res.json();
        if (data.status === "connected") {
          setInline({ type: "success", msg: `Connected · ${data.latency_ms}ms` });
        } else {
          setInline({ type: "error", msg: data.error_message || "Test failed" });
        }
        onLog(`HEALTH AGENT: ${integration.name} test — ${data.status}`);
      }
    } catch {
      setInline({ type: "error", msg: "Network error" });
    }
    setTesting(false);
    onRefresh();
  };

  const handleDelete = async () => {
    if (!window.confirm(`Remove ${integration.name} credentials?`)) return;
    setDeleting(true);
    try {
      await fetch(`${API}/api/integrations/${integration.id}/credentials`, { method: "DELETE" });
      onLog(`CREDENTIALS AGENT: ${integration.name} credentials removed`);
      onRefresh();
    } catch {}
    setDeleting(false);
  };

  return (
    <div style={{
      background: "linear-gradient(160deg, #18181b 0%, #0f0f11 100%)",
      border: `1px solid ${integration.status === "connected"
        ? "rgba(52,211,153,0.2)"
        : integration.status === "disconnected"
        ? "rgba(248,113,113,0.2)"
        : "rgba(63,63,70,0.5)"}`,
      borderRadius: "12px", overflow: "hidden",
      transition: "border-color 0.2s ease",
    }}>
      {/* Module colour strip */}
      <div style={{ height: "2px", background: mod.color, opacity: 0.7 }} />

      {/* Header row */}
      <div
        onClick={() => setExpanded((p) => !p)}
        style={{
          padding: "12px 14px", display: "flex", alignItems: "center",
          gap: "12px", cursor: "pointer",
        }}
      >
        {/* Icon */}
        <div style={{
          width: "32px", height: "32px", borderRadius: "8px",
          background: mod.bg, border: `1px solid ${mod.color}30`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: mod.color, flexShrink: 0,
        }}>
          {mod.icon}
        </div>

        {/* Name + module */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#f4f4f5" }}>
            {integration.name}
          </div>
          <div style={{ fontSize: "0.65rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {integration.module}
          </div>
        </div>

        {/* Status + chevron */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <StatusBadge status={integration.status} />
          {expanded ? <ChevronUp size={13} color="#52525b" /> : <ChevronDown size={13} color="#52525b" />}
        </div>
      </div>

      {/* Expanded area */}
      {expanded && (
        <div style={{
          padding: "0 14px 14px",
          borderTop: "1px solid rgba(63,63,70,0.3)",
        }}>
          {/* Stats row */}
          {integration.last_checked_at && (
            <div style={{ padding: "8px 0 0", fontSize: "0.65rem", color: "#52525b", display: "flex", gap: "16px" }}>
              {integration.latency_ms > 0 && <span>Latency: {integration.latency_ms}ms</span>}
              <span>Last checked: {new Date(integration.last_checked_at).toLocaleTimeString()}</span>
            </div>
          )}

          {/* Required keys list */}
          {(integration.required_keys ?? []).length > 0 && (
            <div style={{ marginTop: "10px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {(integration.required_keys ?? []).map((k: string) => (
                <span key={k} style={{
                  fontSize: "0.6rem", padding: "2px 7px", borderRadius: "4px",
                  background: "rgba(39,39,42,0.8)", color: "#71717a",
                  border: "1px solid rgba(63,63,70,0.4)", fontFamily: "monospace",
                }}>
                  {k}
                </span>
              ))}
            </div>
          )}

          {/* Error message */}
          {integration.error_message && (
            <div style={{
              marginTop: "8px", padding: "7px 10px", borderRadius: "7px",
              background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)",
              color: "#f87171", fontSize: "0.7rem", display: "flex", alignItems: "center", gap: "6px",
            }}>
              <XCircle size={11} />{integration.error_message}
            </div>
          )}

          {/* Inline result */}
          {inline && (
            <div style={{
              marginTop: "8px", padding: "7px 10px", borderRadius: "7px",
              background: inline.type === "error" ? "rgba(248,113,113,0.08)" : "rgba(52,211,153,0.08)",
              border: `1px solid ${inline.type === "error" ? "rgba(248,113,113,0.25)" : "rgba(52,211,153,0.25)"}`,
              color: inline.type === "error" ? "#f87171" : "#34d399",
              fontSize: "0.73rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px",
            }}>
              {inline.type === "error" ? <XCircle size={12} /> : <CheckCircle2 size={12} />}
              {inline.msg}
            </div>
          )}

          {/* Configure form */}
          {configuring && !testing && (
            <CredentialForm
              integration={integration}
              onSave={handleSave}
              onCancel={() => setConfiguring(false)}
            />
          )}

          {/* Loading */}
          {testing && (
            <div style={{
              marginTop: "10px", padding: "10px", borderRadius: "8px",
              background: "rgba(39,39,42,0.5)", display: "flex", alignItems: "center", gap: "8px",
              color: "#71717a", fontSize: "0.73rem",
            }}>
              <Loader size={13} style={{ animation: "spin 1s linear infinite" }} />
              Running connectivity test…
            </div>
          )}

          {/* Action buttons */}
          {!configuring && !testing && (
            <div style={{ marginTop: "12px", display: "flex", gap: "7px", flexWrap: "wrap" }}>
              {!isConfigured ? (
                <button
                  onClick={() => setConfiguring(true)}
                  style={{
                    flex: 1, padding: "7px 12px", borderRadius: "8px",
                    background: "rgba(129,140,248,0.15)", border: "1px solid rgba(129,140,248,0.35)",
                    color: "#a5b4fc", fontSize: "0.73rem", fontWeight: 700, cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.25)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(129,140,248,0.15)"; }}
                >
                  <Plus size={12} /> Configure
                </button>
              ) : (
                <>
                  <button
                    onClick={handleTest}
                    style={{
                      flex: 1, padding: "7px 12px", borderRadius: "8px",
                      background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.25)",
                      color: "#34d399", fontSize: "0.73rem", fontWeight: 700, cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(52,211,153,0.18)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(52,211,153,0.1)"; }}
                  >
                    <RefreshCw size={12} /> Test Connection
                  </button>
                  <button
                    onClick={() => setConfiguring(true)}
                    style={{
                      padding: "7px 12px", borderRadius: "8px",
                      background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.4)",
                      color: "#a1a1aa", fontSize: "0.73rem", fontWeight: 600, cursor: "pointer",
                      display: "flex", alignItems: "center", gap: "5px",
                    }}
                  >
                    <Settings size={11} /> Reconfigure
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    style={{
                      padding: "7px 10px", borderRadius: "8px",
                      background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)",
                      color: "#f87171", fontSize: "0.73rem", cursor: deleting ? "not-allowed" : "pointer",
                      display: "flex", alignItems: "center", gap: "4px",
                    }}
                  >
                    <Trash2 size={11} />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Module section ────────────────────────────────────────────────────────────

function ModuleSection({
  module,
  integrations,
  onRefresh,
  onLog,
}: {
  module: string;
  integrations: any[];
  onRefresh: () => void;
  onLog: (msg: string) => void;
}) {
  const mod = MODULE_COLORS[module] ?? MODULE_COLORS.core;
  const connectedCount = integrations.filter((i) => i.status === "connected").length;

  return (
    <div style={{ marginBottom: "24px" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        marginBottom: "10px", paddingBottom: "8px",
        borderBottom: "1px solid rgba(63,63,70,0.3)",
      }}>
        <div style={{ color: mod.color }}>{mod.icon}</div>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#d4d4d8", textTransform: "capitalize" }}>
          {module}
        </span>
        <span style={{ fontSize: "0.65rem", color: "#52525b" }}>
          {connectedCount}/{integrations.length} connected
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {integrations.map((int) => (
          <IntegrationCard key={int.id} integration={int} onRefresh={onRefresh} onLog={onLog} />
        ))}
      </div>
    </div>
  );
}

// ── Main IntegrationsPanel component ─────────────────────────────────────────

interface Props {
  onLog?: (msg: string) => void;
}

export default function IntegrationsPanel({ onLog }: Props) {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [healthSummary, setHealthSummary] = useState<any>(null);

  const fetchIntegrations = async () => {
    try {
      const res = await fetch(`${API}/api/integrations`);
      if (res.ok) setIntegrations(await res.json());
    } catch {}
    setLoading(false);
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API}/api/integrations/health/summary`);
      if (res.ok) setHealthSummary(await res.json());
    } catch {}
  };

  useEffect(() => {
    fetchIntegrations();
    fetchHealth();
  }, []);

  const handleRefresh = () => {
    fetchIntegrations();
    fetchHealth();
  };

  // Group by module
  const modules = [...new Set(integrations.map((i) => i.module))];
  const byModule = Object.fromEntries(
    modules.map((m) => [m, integrations.filter((i) => i.module === m)])
  );

  const log = (msg: string) => onLog?.(msg);

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800, color: "#f4f4f5" }}>
              Integrations
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: "0.72rem", color: "#71717a" }}>
              Configure practice software integrations and credentials
            </p>
          </div>
          <button
            onClick={handleRefresh}
            style={{
              padding: "7px 12px", borderRadius: "8px",
              background: "rgba(39,39,42,0.7)", border: "1px solid rgba(63,63,70,0.5)",
              color: "#a1a1aa", fontSize: "0.72rem", cursor: "pointer",
              display: "flex", alignItems: "center", gap: "6px",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(63,63,70,0.5)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(39,39,42,0.7)"; }}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        {/* Health summary banner */}
        {healthSummary?.any_disconnected && (
          <div style={{
            padding: "8px 12px", borderRadius: "8px",
            background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.25)",
            display: "flex", alignItems: "center", gap: "8px",
            color: "#f87171", fontSize: "0.73rem", fontWeight: 600,
          }}>
            <AlertTriangle size={13} />
            {healthSummary.disconnected_count} integration{healthSummary.disconnected_count > 1 ? "s" : ""} disconnected
          </div>
        )}
        {!loading && !healthSummary?.any_disconnected && integrations.some(i => i.status === "connected") && (
          <div style={{
            padding: "8px 12px", borderRadius: "8px",
            background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
            display: "flex", alignItems: "center", gap: "8px",
            color: "#34d399", fontSize: "0.73rem", fontWeight: 600,
          }}>
            <CheckCircle2 size={13} />
            All configured integrations healthy
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ color: "#52525b", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "7px" }}>
          <Loader size={13} style={{ animation: "spin 1s linear infinite" }} /> Loading integrations…
        </div>
      ) : (
        modules.map((module) => (
          <ModuleSection
            key={module}
            module={module}
            integrations={byModule[module] ?? []}
            onRefresh={handleRefresh}
            onLog={log}
          />
        ))
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
