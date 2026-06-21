"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

// ── Types ────────────────────────────────────────────────────────────────────

interface AccountData {
  id: string;
  name: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  plan_tier: string;
  status: string;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  active_module_count: number;
  stripe_customer_id: string;
}

interface ModuleData {
  module_id: string;
  name: string;
  description: string;
  price_cents: number;
  billing_interval: string;
  tier_required: string;
  licensed: boolean;
  license_status: string | null;
  purchased_at: string | null;
}

interface InvoiceData {
  id: string;
  invoice_number: string;
  period_start: string;
  period_end: string;
  line_items: Array<{ description: string; amount_cents: number }>;
  subtotal_cents: number;
  total_cents: number;
  status: string;
  paid_at: string | null;
  created_at: string;
}

interface ClinicRow {
  id: string;
  name: string;
  color_hex: string;
  address: string;
  is_active: boolean;
  account_id: string;
}

interface PlanData {
  current_tier: string;
  current_price_cents: number;
  upgrade_options: Array<{
    tier: string;
    price_cents: number;
    delta_cents: number;
    features: string[];
  }>;
  downgrade_options: Array<{
    tier: string;
    price_cents: number;
    delta_cents: number;
    note: string;
  }>;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const TIER_COLORS: Record<string, string> = {
  starter: "#10b981",
  professional: "#6366f1",
  enterprise: "#f59e0b",
};

const STATUS_COLORS: Record<string, string> = {
  trial: "#f59e0b",
  active: "#10b981",
  past_due: "#ef4444",
  suspended: "#ef4444",
  cancelled: "#71717a",
};

const fmtCents = (cents: number) => `$${(cents / 100).toFixed(0)}/mo`;
const fmtDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "—";

// ── Sub-components ─────────────────────────────────────────────────────────────

function TabBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "8px 16px",
        borderRadius: "8px",
        border: "none",
        background: active ? "rgba(99,102,241,0.2)" : "transparent",
        color: active ? "#a5b4fc" : "#71717a",
        cursor: "pointer",
        fontSize: "0.78rem",
        fontWeight: active ? 700 : 500,
        transition: "all 0.15s ease",
        fontFamily: "inherit",
        borderBottom: active ? "2px solid rgba(129,140,248,0.7)" : "2px solid transparent",
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.color = "#a1a1aa"; }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.color = "#71717a"; }}
    >
      {label}
    </button>
  );
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "rgba(24,24,27,0.8)",
      border: "1px solid rgba(63,63,70,0.4)",
      borderRadius: "14px",
      padding: "20px",
      ...style,
    }}>
      {children}
    </div>
  );
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "20px",
      fontSize: "0.7rem",
      fontWeight: 700,
      background: `${color}22`,
      color,
      border: `1px solid ${color}44`,
      textTransform: "uppercase",
      letterSpacing: "0.04em",
    }}>
      {label}
    </span>
  );
}

function SectionTitle({ title, sub }: { title: string; sub?: string }) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "#e4e4e7" }}>{title}</h3>
      {sub && <p style={{ margin: "4px 0 0", fontSize: "0.75rem", color: "#71717a" }}>{sub}</p>}
    </div>
  );
}

// ── Overview Tab (T044) ────────────────────────────────────────────────────────

function OverviewTab({ account, onEdit }: { account: AccountData; onEdit: () => void }) {
  const tier = account.plan_tier;
  const tierColor = TIER_COLORS[tier] ?? "#6366f1";
  const statusColor = STATUS_COLORS[account.status] ?? "#71717a";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
      {/* Account info card */}
      <Card style={{ gridColumn: "1 / -1" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <SectionTitle title={account.name} sub="Account Overview" />
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "12px" }}>
              <Pill label={`${tier} plan`} color={tierColor} />
              <Pill label={account.status} color={statusColor} />
              {account.status === "trial" && (
                <Pill label={`${account.trial_days_remaining}d left`} color="#f59e0b" />
              )}
            </div>
          </div>
          <button
            onClick={onEdit}
            style={{
              padding: "6px 14px", borderRadius: "8px", fontSize: "0.75rem", fontWeight: 600,
              background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.35)",
              color: "#a5b4fc", cursor: "pointer", fontFamily: "inherit",
            }}
          >
            ✏️ Edit
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
          {[
            { label: "Contact", value: account.contact_name },
            { label: "Email", value: account.contact_email },
            { label: "Phone", value: account.contact_phone || "—" },
            { label: "Address", value: account.address || "—" },
            { label: "Trial Ends", value: account.trial_ends_at ? fmtDate(account.trial_ends_at) : "N/A" },
            { label: "Active Modules", value: `${account.active_module_count} / 9` },
          ].map(({ label, value }) => (
            <div key={label}>
              <p style={{ margin: 0, fontSize: "0.67rem", color: "#52525b", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
              <p style={{ margin: "2px 0 0", fontSize: "0.85rem", color: "#d4d4d8" }}>{value}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Stripe info card */}
      <Card>
        <SectionTitle title="Billing Identity" />
        <p style={{ margin: 0, fontSize: "0.78rem", color: "#71717a" }}>Customer ID:</p>
        <code style={{ fontSize: "0.75rem", color: "#a5b4fc" }}>{account.stripe_customer_id || "—"}</code>
        <p style={{ margin: "12px 0 0", fontSize: "0.75rem", color: "#52525b" }}>
          Payments processed via Stripe (demo mode — no real charges)
        </p>
      </Card>

      {/* Quick stats */}
      <Card>
        <SectionTitle title="Plan Stats" />
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
            <span style={{ color: "#71717a" }}>Plan tier</span>
            <span style={{ color: tierColor, fontWeight: 700, textTransform: "capitalize" }}>{tier}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
            <span style={{ color: "#71717a" }}>Monthly base</span>
            <span style={{ color: "#d4d4d8" }}>
              {tier === "starter" ? "$99" : tier === "professional" ? "$249" : "$599"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
            <span style={{ color: "#71717a" }}>Active modules</span>
            <span style={{ color: "#d4d4d8" }}>{account.active_module_count}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ── Edit Account Modal ─────────────────────────────────────────────────────────

function EditAccountModal({ account, onClose, onSaved }: { account: AccountData; onClose: () => void; onSaved: (a: AccountData) => void }) {
  const [form, setForm] = useState({
    name: account.name,
    contact_name: account.contact_name,
    contact_email: account.contact_email,
    contact_phone: account.contact_phone,
    address: account.address,
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/api/account`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      const updated = await res.json();
      onSaved(updated);
      onClose();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={onClose}>
      <div
        style={{
          background: "#18181b", border: "1px solid rgba(63,63,70,0.5)",
          borderRadius: "16px", padding: "28px", width: "min(480px, 90vw)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.8)",
        }}
        onClick={e => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 20px", color: "#e4e4e7" }}>Edit Account Details</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {(["name", "contact_name", "contact_email", "contact_phone", "address"] as const).map(field => (
            <div key={field}>
              <label style={{ display: "block", fontSize: "0.72rem", color: "#71717a", marginBottom: "4px", textTransform: "capitalize" }}>
                {field.replace("_", " ")}
              </label>
              <input
                value={form[field]}
                onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                style={{
                  width: "100%", background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                  borderRadius: "8px", padding: "8px 12px", color: "#e4e4e7", fontSize: "0.85rem",
                  outline: "none", fontFamily: "inherit", boxSizing: "border-box",
                }}
              />
            </div>
          ))}
        </div>
        {err && <p style={{ color: "#f87171", fontSize: "0.75rem", margin: "8px 0 0" }}>{err}</p>}
        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "20px" }}>
          <button onClick={onClose} style={{
            padding: "8px 16px", borderRadius: "8px", background: "transparent",
            border: "1px solid rgba(63,63,70,0.5)", color: "#71717a", cursor: "pointer", fontFamily: "inherit",
          }}>Cancel</button>
          <button onClick={save} disabled={saving} style={{
            padding: "8px 18px", borderRadius: "8px",
            background: "linear-gradient(135deg, rgba(99,102,241,0.8) 0%, rgba(79,70,229,0.8) 100%)",
            border: "1px solid rgba(129,140,248,0.4)", color: "#fff",
            cursor: saving ? "not-allowed" : "pointer", fontWeight: 600,
            opacity: saving ? 0.7 : 1, fontFamily: "inherit",
          }}>{saving ? "Saving…" : "Save Changes"}</button>
        </div>
      </div>
    </div>
  );
}

// ── Modules Tab (T045) ─────────────────────────────────────────────────────────

function ModulesTab({ modules, planTier, onRefresh }: { modules: ModuleData[]; planTier: string; onRefresh: () => void }) {
  const [loading, setLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const activate = async (modId: string) => {
    setLoading(modId);
    try {
      const res = await fetch(`${API}/api/account/modules/${modId}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Error");
      showToast(`✅ ${modId} activated!`);
      onRefresh();
    } catch (e: any) {
      showToast(`❌ ${e.message}`);
    } finally {
      setLoading(null);
    }
  };

  const deactivate = async (modId: string) => {
    setLoading(modId);
    try {
      const res = await fetch(`${API}/api/account/modules/${modId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Error");
      showToast(`🚫 ${modId} cancelled`);
      onRefresh();
    } catch (e: any) {
      showToast(`❌ ${e.message}`);
    } finally {
      setLoading(null);
    }
  };

  const PLAN_ORDER = ["starter", "professional", "enterprise"];

  return (
    <div>
      {toast && (
        <div style={{
          position: "fixed", top: "24px", right: "24px", zIndex: 300,
          background: "rgba(24,24,27,0.97)", border: "1px solid rgba(99,102,241,0.4)",
          borderRadius: "10px", padding: "10px 18px", fontSize: "0.82rem",
          color: "#e4e4e7", boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          animation: "fadeIn 0.2s ease",
        }}>{toast}</div>
      )}
      <SectionTitle title="Module Licenses" sub="Add or remove add-on modules for this account" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(290px,1fr))", gap: "12px" }}>
        {modules.map(mod => {
          const active = mod.licensed && mod.license_status === "active";
          const planLocked = PLAN_ORDER.indexOf(planTier) < PLAN_ORDER.indexOf(mod.tier_required);
          const isLoading = loading === mod.module_id;
          return (
            <Card key={mod.module_id} style={{
              borderColor: active ? "rgba(99,102,241,0.35)" : "rgba(63,63,70,0.3)",
              background: active ? "rgba(99,102,241,0.05)" : "rgba(24,24,27,0.7)",
              transition: "all 0.2s ease",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                <div>
                  <p style={{ margin: 0, fontWeight: 700, fontSize: "0.88rem", color: "#e4e4e7" }}>{mod.name}</p>
                  <p style={{ margin: "2px 0 0", fontSize: "0.68rem", color: "#71717a", textTransform: "uppercase", letterSpacing: "0.05em" }}>{mod.module_id}</p>
                </div>
                {active ? (
                  <Pill label="Active" color="#10b981" />
                ) : planLocked ? (
                  <Pill label={`${mod.tier_required} only`} color="#71717a" />
                ) : (
                  <Pill label="Available" color="#6366f1" />
                )}
              </div>
              <p style={{ margin: "0 0 12px", fontSize: "0.78rem", color: "#71717a", lineHeight: 1.5 }}>{mod.description}</p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#a5b4fc", fontWeight: 700, fontSize: "0.85rem" }}>{fmtCents(mod.price_cents)}</span>
                {active ? (
                  <button
                    onClick={() => deactivate(mod.module_id)}
                    disabled={isLoading}
                    style={{
                      padding: "5px 12px", borderRadius: "7px", fontSize: "0.72rem", fontWeight: 600,
                      background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                      color: "#fca5a5", cursor: isLoading ? "not-allowed" : "pointer", fontFamily: "inherit",
                      opacity: isLoading ? 0.6 : 1,
                    }}
                  >
                    {isLoading ? "…" : "Cancel"}
                  </button>
                ) : (
                  <button
                    onClick={() => !planLocked && activate(mod.module_id)}
                    disabled={isLoading || planLocked}
                    title={planLocked ? `Requires ${mod.tier_required} plan` : undefined}
                    style={{
                      padding: "5px 12px", borderRadius: "7px", fontSize: "0.72rem", fontWeight: 600,
                      background: planLocked ? "rgba(63,63,70,0.2)" : "rgba(99,102,241,0.2)",
                      border: `1px solid ${planLocked ? "rgba(63,63,70,0.3)" : "rgba(99,102,241,0.4)"}`,
                      color: planLocked ? "#52525b" : "#a5b4fc",
                      cursor: (isLoading || planLocked) ? "not-allowed" : "pointer",
                      fontFamily: "inherit", opacity: isLoading ? 0.6 : 1,
                    }}
                  >
                    {isLoading ? "…" : planLocked ? "🔒 Locked" : "Activate"}
                  </button>
                )}
              </div>
              {active && mod.purchased_at && (
                <p style={{ margin: "8px 0 0", fontSize: "0.68rem", color: "#52525b" }}>
                  Activated {fmtDate(mod.purchased_at)}
                </p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Invoices Tab (T046) ────────────────────────────────────────────────────────

function InvoicesTab({ invoices }: { invoices: InvoiceData[] }) {
  const [selected, setSelected] = useState<InvoiceData | null>(null);

  const STATUS_BADGE: Record<string, string> = {
    paid: "#10b981", pending: "#f59e0b", failed: "#ef4444", void: "#71717a",
  };

  return (
    <div>
      <SectionTitle title="Invoice History" sub="Billing records, newest first" />
      {invoices.length === 0 ? (
        <Card><p style={{ color: "#52525b", textAlign: "center", margin: 0 }}>No invoices yet.</p></Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {invoices.map(inv => (
            <Card
              key={inv.id}
              style={{ cursor: "pointer", transition: "all 0.15s ease" }}
            >
              <div
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                onClick={() => setSelected(selected?.id === inv.id ? null : inv)}
              >
                <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                  <span style={{ fontWeight: 700, color: "#e4e4e7", fontSize: "0.88rem" }}>{inv.invoice_number}</span>
                  <span style={{ fontSize: "0.75rem", color: "#71717a" }}>{inv.period_start} → {inv.period_end}</span>
                  <Pill label={inv.status} color={STATUS_BADGE[inv.status] ?? "#71717a"} />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontWeight: 700, color: "#a5b4fc" }}>${(inv.total_cents / 100).toFixed(2)}</span>
                  <span style={{ color: "#52525b", fontSize: "0.75rem" }}>{selected?.id === inv.id ? "▲" : "▼"}</span>
                </div>
              </div>
              {selected?.id === inv.id && (
                <div style={{ marginTop: "14px", borderTop: "1px solid rgba(63,63,70,0.3)", paddingTop: "14px" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", fontSize: "0.7rem", color: "#71717a", fontWeight: 600, paddingBottom: "6px" }}>Description</th>
                        <th style={{ textAlign: "right", fontSize: "0.7rem", color: "#71717a", fontWeight: 600, paddingBottom: "6px" }}>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inv.line_items.map((li, i) => (
                        <tr key={i}>
                          <td style={{ fontSize: "0.8rem", color: "#a1a1aa", paddingBottom: "4px" }}>{li.description}</td>
                          <td style={{ fontSize: "0.8rem", color: "#a5b4fc", textAlign: "right", paddingBottom: "4px" }}>${(li.amount_cents / 100).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ borderTop: "1px solid rgba(63,63,70,0.3)" }}>
                        <td style={{ fontWeight: 700, color: "#e4e4e7", fontSize: "0.85rem", paddingTop: "8px" }}>Total</td>
                        <td style={{ fontWeight: 700, color: "#a5b4fc", textAlign: "right", fontSize: "0.85rem", paddingTop: "8px" }}>${(inv.total_cents / 100).toFixed(2)}</td>
                      </tr>
                    </tfoot>
                  </table>
                  {inv.paid_at && (
                    <p style={{ margin: "10px 0 0", fontSize: "0.7rem", color: "#52525b" }}>
                      Paid {fmtDate(inv.paid_at)}
                    </p>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Clinics Tab (T047) ────────────────────────────────────────────────────────

function ClinicsTab({ clinics, planTier, onRefresh }: { clinics: ClinicRow[]; planTier: string; onRefresh: () => void }) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", address: "", color_hex: "#6C63FF" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const addClinic = async () => {
    setSaving(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/api/account/clinics`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, timezone: "America/Los_Angeles", id: `clinic-${Date.now()}`, is_active: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Error");
      setAdding(false);
      setForm({ name: "", address: "", color_hex: "#6C63FF" });
      onRefresh();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  };

  const canAdd = planTier !== "starter";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <SectionTitle title="Clinic Locations" sub={`${clinics.length} location${clinics.length !== 1 ? "s" : ""} linked to this account`} />
        <button
          onClick={() => canAdd ? setAdding(v => !v) : undefined}
          title={!canAdd ? "Requires Professional or Enterprise plan" : undefined}
          style={{
            padding: "7px 14px", borderRadius: "8px", fontSize: "0.75rem", fontWeight: 600,
            background: canAdd ? "rgba(99,102,241,0.2)" : "rgba(63,63,70,0.1)",
            border: `1px solid ${canAdd ? "rgba(99,102,241,0.4)" : "rgba(63,63,70,0.3)"}`,
            color: canAdd ? "#a5b4fc" : "#52525b",
            cursor: canAdd ? "pointer" : "not-allowed", fontFamily: "inherit",
          }}
        >
          {canAdd ? "+ Add Location" : "🔒 Pro Only"}
        </button>
      </div>

      {adding && (
        <Card style={{ marginBottom: "16px", borderColor: "rgba(99,102,241,0.3)" }}>
          <h4 style={{ margin: "0 0 14px", color: "#e4e4e7", fontSize: "0.88rem" }}>New Location</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {[{ field: "name", label: "Clinic Name" }, { field: "address", label: "Address" }].map(({ field, label }) => (
              <div key={field}>
                <label style={{ display: "block", fontSize: "0.7rem", color: "#71717a", marginBottom: "4px" }}>{label}</label>
                <input
                  value={(form as any)[field]}
                  onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                  style={{
                    width: "100%", background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                    borderRadius: "8px", padding: "8px 12px", color: "#e4e4e7", fontSize: "0.82rem",
                    outline: "none", fontFamily: "inherit", boxSizing: "border-box",
                  }}
                />
              </div>
            ))}
            <div>
              <label style={{ display: "block", fontSize: "0.7rem", color: "#71717a", marginBottom: "4px" }}>Color</label>
              <input type="color" value={form.color_hex} onChange={e => setForm(f => ({ ...f, color_hex: e.target.value }))}
                style={{ width: "48px", height: "32px", borderRadius: "6px", border: "none", cursor: "pointer", background: "none" }} />
            </div>
          </div>
          {err && <p style={{ color: "#f87171", fontSize: "0.75rem", margin: "6px 0 0" }}>{err}</p>}
          <div style={{ display: "flex", gap: "8px", marginTop: "14px" }}>
            <button onClick={() => setAdding(false)} style={{
              padding: "6px 14px", borderRadius: "7px", background: "transparent",
              border: "1px solid rgba(63,63,70,0.4)", color: "#71717a", cursor: "pointer", fontFamily: "inherit", fontSize: "0.8rem",
            }}>Cancel</button>
            <button onClick={addClinic} disabled={saving || !form.name} style={{
              padding: "6px 14px", borderRadius: "7px", fontWeight: 600,
              background: "rgba(99,102,241,0.25)", border: "1px solid rgba(99,102,241,0.4)",
              color: "#a5b4fc", cursor: saving || !form.name ? "not-allowed" : "pointer",
              fontFamily: "inherit", fontSize: "0.8rem",
            }}>{saving ? "Adding…" : "Add Clinic"}</button>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px,1fr))", gap: "12px" }}>
        {clinics.map(c => (
          <Card key={c.id} style={{ borderLeft: `3px solid ${c.color_hex}`, borderColor: `${c.color_hex}55` }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <span style={{ fontWeight: 700, color: "#e4e4e7", fontSize: "0.88rem" }}>{c.name}</span>
              <Pill label={c.is_active ? "Active" : "Inactive"} color={c.is_active ? "#10b981" : "#71717a"} />
            </div>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "#71717a" }}>{c.address || "No address on file"}</p>
            <p style={{ margin: "6px 0 0", fontSize: "0.67rem", color: "#52525b" }}>
              ID: <code style={{ color: "#a5b4fc" }}>{c.id}</code>
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Plan Tab (T048) ────────────────────────────────────────────────────────────

function PlanTab({ plan, onUpgrade }: { plan: PlanData; onUpgrade: (tier: string) => void }) {
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const doUpgrade = async (tier: string) => {
    setUpgrading(tier);
    setResult(null);
    try {
      const res = await fetch(`${API}/api/account/plan/upgrade`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_tier: tier }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Error");
      setResult(`✅ ${data.message}`);
      onUpgrade(tier);
    } catch (e: any) {
      setResult(`❌ ${e.message}`);
    } finally {
      setUpgrading(null);
    }
  };

  const tierColor = TIER_COLORS[plan.current_tier] ?? "#6366f1";

  return (
    <div>
      <SectionTitle title="Plan & Pricing" sub="Upgrade or downgrade your subscription tier" />

      {/* Current plan banner */}
      <Card style={{ marginBottom: "20px", borderColor: `${tierColor}44`, background: `${tierColor}08` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <p style={{ margin: 0, fontSize: "0.72rem", color: "#71717a", textTransform: "uppercase", letterSpacing: "0.06em" }}>Current Plan</p>
            <p style={{ margin: "4px 0 0", fontSize: "1.3rem", fontWeight: 800, color: tierColor, textTransform: "capitalize" }}>{plan.current_tier}</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800, color: "#e4e4e7" }}>${(plan.current_price_cents / 100).toFixed(0)}</p>
            <p style={{ margin: "2px 0 0", fontSize: "0.72rem", color: "#71717a" }}>per month</p>
          </div>
        </div>
      </Card>

      {result && (
        <div style={{
          padding: "10px 16px", borderRadius: "10px", marginBottom: "16px",
          background: result.startsWith("✅") ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
          border: `1px solid ${result.startsWith("✅") ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
          color: result.startsWith("✅") ? "#6ee7b7" : "#fca5a5",
          fontSize: "0.82rem",
        }}>{result}</div>
      )}

      {plan.upgrade_options.length > 0 && (
        <>
          <h4 style={{ margin: "0 0 12px", color: "#a1a1aa", fontSize: "0.82rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Upgrade Options
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
            {plan.upgrade_options.map(opt => (
              <Card key={opt.tier} style={{ borderColor: `${TIER_COLORS[opt.tier] ?? "#6366f1"}44` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 700, fontSize: "0.95rem", color: TIER_COLORS[opt.tier] ?? "#a5b4fc", textTransform: "capitalize" }}>
                      {opt.tier}
                    </p>
                    <ul style={{ margin: "6px 0 0", padding: "0 0 0 16px", color: "#71717a", fontSize: "0.75rem" }}>
                      {opt.features.map(f => <li key={f}>{f}</li>)}
                    </ul>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ margin: 0, fontWeight: 800, fontSize: "1.1rem", color: "#e4e4e7" }}>
                      ${(opt.price_cents / 100).toFixed(0)}/mo
                    </p>
                    <p style={{ margin: "2px 0 8px", fontSize: "0.7rem", color: "#71717a" }}>
                      +${(opt.delta_cents / 100).toFixed(0)}/mo
                    </p>
                    <button
                      onClick={() => doUpgrade(opt.tier)}
                      disabled={upgrading === opt.tier}
                      style={{
                        padding: "6px 14px", borderRadius: "8px", fontWeight: 700,
                        background: `linear-gradient(135deg, ${TIER_COLORS[opt.tier] ?? "#6366f1"}44 0%, ${TIER_COLORS[opt.tier] ?? "#6366f1"}22 100%)`,
                        border: `1px solid ${TIER_COLORS[opt.tier] ?? "#6366f1"}55`,
                        color: TIER_COLORS[opt.tier] ?? "#a5b4fc",
                        cursor: upgrading === opt.tier ? "not-allowed" : "pointer",
                        fontFamily: "inherit", fontSize: "0.78rem",
                      }}
                    >
                      {upgrading === opt.tier ? "Upgrading…" : `Upgrade to ${opt.tier}`}
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {plan.downgrade_options.length > 0 && (
        <>
          <h4 style={{ margin: "0 0 12px", color: "#71717a", fontSize: "0.78rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Downgrade Options
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {plan.downgrade_options.map(opt => (
              <Card key={opt.tier} style={{ background: "rgba(18,18,21,0.5)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ margin: 0, color: "#71717a", fontSize: "0.85rem", textTransform: "capitalize", fontWeight: 600 }}>{opt.tier}</p>
                    <p style={{ margin: "4px 0 0", fontSize: "0.72rem", color: "#52525b" }}>{opt.note}</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ margin: 0, fontWeight: 700, color: "#71717a" }}>${(opt.price_cents / 100).toFixed(0)}/mo</p>
                    <button
                      onClick={() => doUpgrade(opt.tier)}
                      disabled={upgrading === opt.tier}
                      style={{
                        marginTop: "6px", padding: "5px 12px", borderRadius: "7px",
                        background: "transparent", border: "1px solid rgba(63,63,70,0.4)",
                        color: "#71717a", cursor: upgrading === opt.tier ? "not-allowed" : "pointer",
                        fontFamily: "inherit", fontSize: "0.72rem",
                      }}
                    >
                      {upgrading === opt.tier ? "Changing…" : "Downgrade"}
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Users Tab (Gap 5) ────────────────────────────────────────────────────────────────────────────────

interface UserRow {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

function UsersTab({ onRefresh }: { onRefresh: () => void }) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "member" });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/account/users`);
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch { setUsers([]); } finally { setLoading(false); }
  };

  useEffect(() => { fetchUsers(); }, []);

  const addUser = async () => {
    if (!form.name || !form.email) { setErr("Name and email are required."); return; }
    setSaving(true); setErr(null);
    try {
      const res = await fetch(`${API}/api/account/users`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Error");
      showToast(`✅ ${form.email} added`);
      setAdding(false); setForm({ name: "", email: "", role: "member" });
      fetchUsers(); onRefresh();
    } catch (e: any) { setErr(e.message); } finally { setSaving(false); }
  };

  const removeUser = async (userId: string, email: string) => {
    const admins = users.filter(u => u.role === "admin");
    const target = users.find(u => u.id === userId);
    if (admins.length === 1 && target?.role === "admin") {
      showToast("❌ Cannot remove the last admin"); return;
    }
    try {
      await fetch(`${API}/api/account/users/${userId}`, { method: "DELETE" });
      showToast(`🚫 ${email} removed`);
      fetchUsers(); onRefresh();
    } catch { showToast("❌ Failed to remove user"); }
  };

  return (
    <div>
      {toast && (
        <div style={{
          position: "fixed", top: "24px", right: "24px", zIndex: 300,
          background: "rgba(24,24,27,0.97)", border: "1px solid rgba(99,102,241,0.4)",
          borderRadius: "10px", padding: "10px 18px", fontSize: "0.82rem",
          color: "#e4e4e7", boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>{toast}</div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <SectionTitle title="Team Members" sub={`${users.length} user${users.length !== 1 ? "s" : ""} on this account`} />
        <button
          onClick={() => setAdding(v => !v)}
          style={{
            padding: "7px 14px", borderRadius: "8px", fontSize: "0.75rem", fontWeight: 600,
            background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.4)",
            color: "#a5b4fc", cursor: "pointer", fontFamily: "inherit",
          }}
        >+ Invite User</button>
      </div>

      {adding && (
        <Card style={{ marginBottom: "16px", borderColor: "rgba(99,102,241,0.3)" }}>
          <h4 style={{ margin: "0 0 14px", color: "#e4e4e7", fontSize: "0.88rem" }}>Invite Team Member</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {([{ field: "name", label: "Full Name" }, { field: "email", label: "Email Address" }] as const).map(({ field, label }) => (
              <div key={field}>
                <label style={{ display: "block", fontSize: "0.7rem", color: "#71717a", marginBottom: "4px" }}>{label}</label>
                <input
                  value={(form as any)[field]}
                  onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                  style={{
                    width: "100%", background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                    borderRadius: "8px", padding: "8px 12px", color: "#e4e4e7", fontSize: "0.82rem",
                    outline: "none", fontFamily: "inherit", boxSizing: "border-box" as const,
                  }}
                />
              </div>
            ))}
            <div>
              <label style={{ display: "block", fontSize: "0.7rem", color: "#71717a", marginBottom: "4px" }}>Role</label>
              <select
                value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                style={{
                  width: "100%", background: "rgba(39,39,42,0.9)", border: "1px solid rgba(63,63,70,0.5)",
                  borderRadius: "8px", padding: "8px 12px", color: "#e4e4e7", fontSize: "0.82rem",
                  outline: "none", fontFamily: "inherit",
                }}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          {err && <p style={{ color: "#f87171", fontSize: "0.75rem", margin: "6px 0 0" }}>{err}</p>}
          <div style={{ display: "flex", gap: "8px", marginTop: "14px" }}>
            <button onClick={() => { setAdding(false); setErr(null); }} style={{
              padding: "6px 14px", borderRadius: "7px", background: "transparent",
              border: "1px solid rgba(63,63,70,0.4)", color: "#71717a", cursor: "pointer", fontFamily: "inherit", fontSize: "0.8rem",
            }}>Cancel</button>
            <button onClick={addUser} disabled={saving} style={{
              padding: "6px 14px", borderRadius: "7px", fontWeight: 600,
              background: "rgba(99,102,241,0.25)", border: "1px solid rgba(99,102,241,0.4)",
              color: "#a5b4fc", cursor: saving ? "not-allowed" : "pointer",
              fontFamily: "inherit", fontSize: "0.8rem",
            }}>{saving ? "Adding…" : "Send Invite"}</button>
          </div>
        </Card>
      )}

      {loading ? (
        <Card><p style={{ color: "#52525b", textAlign: "center", margin: 0 }}>Loading…</p></Card>
      ) : users.length === 0 ? (
        <Card><p style={{ color: "#52525b", textAlign: "center", margin: 0 }}>No users found.</p></Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {users.map(u => (
            <Card key={u.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: "0.88rem", color: "#e4e4e7" }}>{u.name}</p>
                <p style={{ margin: "2px 0 0", fontSize: "0.75rem", color: "#71717a" }}>{u.email}</p>
                <p style={{ margin: "4px 0 0", fontSize: "0.67rem", color: "#52525b" }}>Joined {fmtDate(u.created_at)}</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Pill label={u.role} color={u.role === "admin" ? "#6366f1" : "#71717a"} />
                <button
                  onClick={() => removeUser(u.id, u.email)}
                  style={{
                    padding: "4px 10px", borderRadius: "6px", fontSize: "0.7rem",
                    background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                    color: "#fca5a5", cursor: "pointer", fontFamily: "inherit",
                  }}
                >Remove</button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main AccountPortal ─────────────────────────────────────────────────────────

export default function AccountPortal({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState<"overview" | "modules" | "invoices" | "clinics" | "plan" | "users">("overview");
  const [account, setAccount] = useState<AccountData | null>(null);
  const [modules, setModules] = useState<ModuleData[]>([]);
  const [invoices, setInvoices] = useState<InvoiceData[]>([]);
  const [clinics, setClinics] = useState<ClinicRow[]>([]);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [acc, mods, invs, clins, pln] = await Promise.all([
        fetch(`${API}/api/account`).then(r => r.json()),
        fetch(`${API}/api/account/modules`).then(r => r.json()),
        fetch(`${API}/api/account/invoices`).then(r => r.json()),
        fetch(`${API}/api/account/clinics`).then(r => r.json()),
        fetch(`${API}/api/account/plan`).then(r => r.json()),
      ]);
      setAccount(acc);
      setModules(Array.isArray(mods) ? mods : []);
      setInvoices(Array.isArray(invs) ? invs : []);
      setClinics(Array.isArray(clins) ? clins : []);
      setPlan(pln);
    } catch (e) {
      console.error("AccountPortal fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const tabs: Array<{ id: typeof tab; label: string }> = [
    { id: "overview", label: "📋 Overview" },
    { id: "modules", label: "🧩 Modules" },
    { id: "invoices", label: "🧾 Invoices" },
    { id: "clinics", label: "🏥 Clinics" },
    { id: "plan", label: "💳 Plan" },
    { id: "users", label: "👥 Users" },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "#09090b", color: "#f4f4f5" }}>
      {/* Portal header */}
      <div style={{
        padding: "12px 20px",
        borderBottom: "1px solid rgba(63,63,70,0.4)",
        display: "flex", alignItems: "center", gap: "12px",
        flexShrink: 0,
        background: "rgba(14,14,17,0.95)",
        backdropFilter: "blur(8px)",
      }}>
        <button
          onClick={onBack}
          style={{
            padding: "5px 10px", borderRadius: "8px",
            background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.4)",
            color: "#71717a", cursor: "pointer", fontSize: "0.75rem", fontFamily: "inherit",
          }}
        >
          ← Back
        </button>
        <div>
          <h2 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700, color: "#e4e4e7" }}>
            Account & Billing
          </h2>
          {account && (
            <p style={{ margin: "1px 0 0", fontSize: "0.7rem", color: "#52525b" }}>
              {account.name} · {account.plan_tier} plan
            </p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", gap: "2px", padding: "8px 16px",
        borderBottom: "1px solid rgba(63,63,70,0.3)",
        background: "rgba(9,9,11,0.6)", flexShrink: 0,
        overflowX: "auto",
      }}>
        {tabs.map(t => (
          <TabBtn key={t.id} label={t.label} active={tab === t.id} onClick={() => setTab(t.id)} />
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "200px", color: "#52525b" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", marginBottom: "8px", animation: "spin 1s linear infinite", display: "inline-block" }}>⚙</div>
              <p style={{ margin: 0, fontSize: "0.8rem" }}>Loading account data…</p>
            </div>
          </div>
        ) : (
          <>
            {tab === "overview" && account && (
              <OverviewTab account={account} onEdit={() => setEditOpen(true)} />
            )}
            {tab === "modules" && account && (
              <ModulesTab modules={modules} planTier={account.plan_tier} onRefresh={fetchAll} />
            )}
            {tab === "invoices" && (
              <InvoicesTab invoices={invoices} />
            )}
            {tab === "clinics" && account && (
              <ClinicsTab clinics={clinics} planTier={account.plan_tier} onRefresh={fetchAll} />
            )}
            {tab === "plan" && plan && (
              <PlanTab plan={plan} onUpgrade={(tier) => { fetchAll(); }} />
            )}
            {tab === "users" && (
              <UsersTab onRefresh={fetchAll} />
            )}
          </>
        )}
      </div>

      {/* Edit modal */}
      {editOpen && account && (
        <EditAccountModal
          account={account}
          onClose={() => setEditOpen(false)}
          onSaved={(updated: any) => { setAccount(updated); }}
        />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}
