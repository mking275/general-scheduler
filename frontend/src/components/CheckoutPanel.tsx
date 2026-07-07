"use client";

import { useState, useEffect } from "react";
import { Receipt, Send, CreditCard, Printer, Plus, Trash2, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

interface LineItem {
  description: string;
  amount_cents: number;
}

interface VisitInvoice {
  id: string;
  timeblock_id: string;
  patient_id: string | null;
  owner_id: string | null;
  clinic_id: string | null;
  invoice_number: string;
  line_items: LineItem[];
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  status: "draft" | "sent" | "paid" | "void";
  notes: string;
  created_at: string;
  sent_at: string | null;
  paid_at: string | null;
}

interface CheckoutPanelProps {
  timeblockId: string;
  patientName?: string;
  ownerName?: string;
  onLogEntry?: (entry: string) => void;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; icon: string }> = {
  draft:  { label: "Draft",   color: "#f59e0b", bg: "rgba(245,158,11,0.1)",  border: "rgba(245,158,11,0.25)", icon: "📝" },
  sent:   { label: "Sent",    color: "#60a5fa", bg: "rgba(96,165,250,0.1)",  border: "rgba(96,165,250,0.25)", icon: "📧" },
  paid:   { label: "Paid",    color: "#10b981", bg: "rgba(16,185,129,0.1)",  border: "rgba(16,185,129,0.25)", icon: "✓" },
  void:   { label: "Void",    color: "#71717a", bg: "rgba(113,113,122,0.1)", border: "rgba(113,113,122,0.25)", icon: "✕" },
};

function formatCents(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export default function CheckoutPanel({ timeblockId, patientName, ownerName, onLogEntry }: CheckoutPanelProps) {
  const [invoice, setInvoice] = useState<VisitInvoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState("");
  const [addingItem, setAddingItem] = useState(false);
  const [newItemDesc, setNewItemDesc] = useState("");
  const [newItemAmount, setNewItemAmount] = useState("");

  // Fetch invoice for this timeblock
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API}/api/appointments/${timeblockId}/invoice`)
      .then(r => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`Failed to load invoice (${r.status})`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        if (data) {
          // Parse line_items if it's a string
          if (typeof data.line_items === "string") {
            data.line_items = JSON.parse(data.line_items);
          }
          setInvoice(data);
          setNotesValue(data.notes || "");
        }
        setLoading(false);
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [timeblockId]);

  const handleSendInvoice = async () => {
    if (!invoice) return;
    setActionLoading("send");
    try {
      const res = await fetch(`${API}/api/visit-invoices/${invoice.id}/send`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        if (typeof updated.line_items === "string") updated.line_items = JSON.parse(updated.line_items);
        setInvoice(updated);
        onLogEntry?.(`VERA (Billing): Invoice ${invoice.invoice_number} sent to ${ownerName || "client"}`);
      }
    } catch { /* ignore */ }
    setActionLoading(null);
  };

  const handleMarkPaid = async () => {
    if (!invoice) return;
    setActionLoading("paid");
    try {
      const res = await fetch(`${API}/api/visit-invoices/${invoice.id}/mark-paid`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        if (typeof updated.line_items === "string") updated.line_items = JSON.parse(updated.line_items);
        setInvoice(updated);
        onLogEntry?.(`VERA (Billing): Invoice ${invoice.invoice_number} — payment collected (${formatCents(updated.total_cents)})`);
      }
    } catch { /* ignore */ }
    setActionLoading(null);
  };

  const handleSaveNotes = async () => {
    if (!invoice) return;
    try {
      const res = await fetch(`${API}/api/visit-invoices/${invoice.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: notesValue }),
      });
      if (res.ok) {
        const updated = await res.json();
        if (typeof updated.line_items === "string") updated.line_items = JSON.parse(updated.line_items);
        setInvoice(updated);
      }
    } catch { /* ignore */ }
    setEditingNotes(false);
  };

  const handleAddItem = async () => {
    if (!invoice || !newItemDesc.trim() || !newItemAmount.trim()) return;
    const amountCents = Math.round(parseFloat(newItemAmount) * 100);
    if (isNaN(amountCents) || amountCents <= 0) return;

    const updatedItems = [...invoice.line_items, { description: newItemDesc.trim(), amount_cents: amountCents }];
    const newSubtotal = updatedItems.reduce((s, li) => s + li.amount_cents, 0);

    try {
      const res = await fetch(`${API}/api/visit-invoices/${invoice.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          line_items: JSON.stringify(updatedItems),
          subtotal_cents: newSubtotal,
          total_cents: newSubtotal + (invoice.tax_cents || 0),
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        if (typeof updated.line_items === "string") updated.line_items = JSON.parse(updated.line_items);
        setInvoice(updated);
        onLogEntry?.(`VERA (Billing): Added "${newItemDesc.trim()}" (${formatCents(amountCents)}) to invoice ${invoice.invoice_number}`);
      }
    } catch { /* ignore */ }
    setNewItemDesc("");
    setNewItemAmount("");
    setAddingItem(false);
  };

  const handleRemoveItem = async (index: number) => {
    if (!invoice || invoice.status !== "draft") return;
    const updatedItems = invoice.line_items.filter((_, i) => i !== index);
    const newSubtotal = updatedItems.reduce((s, li) => s + li.amount_cents, 0);

    try {
      const res = await fetch(`${API}/api/visit-invoices/${invoice.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          line_items: JSON.stringify(updatedItems),
          subtotal_cents: newSubtotal,
          total_cents: newSubtotal + (invoice.tax_cents || 0),
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        if (typeof updated.line_items === "string") updated.line_items = JSON.parse(updated.line_items);
        setInvoice(updated);
      }
    } catch { /* ignore */ }
  };

  // --- Render ---

  if (loading) {
    return (
      <div style={{
        marginTop: "12px", padding: "16px", background: "rgba(39,39,42,0.4)",
        borderRadius: "12px", border: "1px solid rgba(63,63,70,0.3)",
        display: "flex", alignItems: "center", gap: "8px", color: "#71717a", fontSize: "0.78rem",
      }}>
        <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
        Loading invoice…
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div style={{
        marginTop: "12px", padding: "14px 16px", background: "rgba(39,39,42,0.3)",
        borderRadius: "12px", border: "1px solid rgba(63,63,70,0.3)",
        display: "flex", alignItems: "center", gap: "8px", color: "#52525b", fontSize: "0.78rem",
      }}>
        <Receipt size={14} />
        {error ? `Invoice error: ${error}` : "No invoice generated for this visit."}
      </div>
    );
  }

  const sc = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.draft;
  const isDraft = invoice.status === "draft";
  const isSent = invoice.status === "sent";
  const isPaid = invoice.status === "paid";

  return (
    <div style={{
      marginTop: "12px",
      background: "linear-gradient(160deg, rgba(24,24,27,0.95) 0%, rgba(9,9,11,0.95) 100%)",
      borderRadius: "14px",
      border: `1px solid ${sc.border}`,
      overflow: "hidden",
      transition: "border-color 0.3s ease",
    }}>
      {/* Header bar */}
      <div style={{
        padding: "12px 16px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: `1px solid ${sc.border}`,
        background: sc.bg,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Receipt size={15} color={sc.color} />
          <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "#e4e4e7" }}>
            {invoice.invoice_number}
          </span>
          <span style={{
            fontSize: "0.65rem", fontWeight: 700, padding: "2px 8px",
            borderRadius: "12px", background: sc.bg, color: sc.color,
            border: `1px solid ${sc.border}`, letterSpacing: "0.04em",
          }}>
            {sc.icon} {sc.label.toUpperCase()}
          </span>
        </div>
        <span style={{ fontSize: "0.7rem", color: "#71717a" }}>
          {new Date(invoice.created_at).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}
        </span>
      </div>

      {/* Line items */}
      <div style={{ padding: "12px 16px" }}>
        {/* Patient / Owner header */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginBottom: "10px", paddingBottom: "8px",
          borderBottom: "1px solid rgba(63,63,70,0.3)",
        }}>
          <span style={{ fontSize: "0.75rem", color: "#a1a1aa" }}>
            {patientName && <><strong style={{ color: "#d4d4d8" }}>{patientName}</strong> · </>}
            {ownerName || "Client"}
          </span>
          {isPaid && invoice.paid_at && (
            <span style={{ fontSize: "0.68rem", color: "#10b981", display: "flex", alignItems: "center", gap: "4px" }}>
              <CheckCircle2 size={11} />
              Paid {new Date(invoice.paid_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>

        {/* Items list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "10px" }}>
          {invoice.line_items.map((li, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "7px 10px", borderRadius: "8px",
              background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.3)",
              fontSize: "0.78rem",
            }}>
              <span style={{ color: "#d4d4d8", flex: 1 }}>{li.description}</span>
              <span style={{ color: "#e4e4e7", fontWeight: 600, fontVariantNumeric: "tabular-nums", marginLeft: "12px" }}>
                {formatCents(li.amount_cents)}
              </span>
              {isDraft && invoice.line_items.length > 1 && (
                <button
                  onClick={() => handleRemoveItem(i)}
                  title="Remove item"
                  style={{
                    marginLeft: "8px", padding: "2px", background: "transparent",
                    border: "none", color: "#52525b", cursor: "pointer",
                    borderRadius: "4px", display: "flex", alignItems: "center",
                    transition: "color 0.15s",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                  onMouseLeave={e => (e.currentTarget.style.color = "#52525b")}
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add item (draft only) */}
        {isDraft && (
          addingItem ? (
            <div style={{
              display: "flex", gap: "6px", marginBottom: "10px", alignItems: "center",
            }}>
              <input
                value={newItemDesc}
                onChange={e => setNewItemDesc(e.target.value)}
                placeholder="Description"
                autoFocus
                style={{
                  flex: 1, padding: "6px 10px", borderRadius: "6px", fontSize: "0.75rem",
                  background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                  color: "#e4e4e7", outline: "none", fontFamily: "inherit",
                }}
              />
              <input
                value={newItemAmount}
                onChange={e => setNewItemAmount(e.target.value)}
                placeholder="$0.00"
                type="number"
                step="0.01"
                min="0"
                style={{
                  width: "80px", padding: "6px 8px", borderRadius: "6px", fontSize: "0.75rem",
                  background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                  color: "#e4e4e7", outline: "none", fontFamily: "inherit", textAlign: "right",
                }}
              />
              <button
                onClick={handleAddItem}
                style={{
                  padding: "5px 10px", borderRadius: "6px", fontSize: "0.72rem", fontWeight: 600,
                  background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)",
                  color: "#10b981", cursor: "pointer", fontFamily: "inherit",
                }}
              >
                Add
              </button>
              <button
                onClick={() => { setAddingItem(false); setNewItemDesc(""); setNewItemAmount(""); }}
                style={{
                  padding: "5px 8px", borderRadius: "6px", fontSize: "0.72rem",
                  background: "transparent", border: "1px solid rgba(63,63,70,0.4)",
                  color: "#71717a", cursor: "pointer", fontFamily: "inherit",
                }}
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={() => setAddingItem(true)}
              style={{
                display: "flex", alignItems: "center", gap: "5px",
                marginBottom: "10px", padding: "5px 10px", borderRadius: "6px",
                background: "transparent", border: "1px dashed rgba(63,63,70,0.5)",
                color: "#52525b", cursor: "pointer", fontSize: "0.72rem", fontFamily: "inherit",
                transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.color = "#a1a1aa"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.8)"; }}
              onMouseLeave={e => { e.currentTarget.style.color = "#52525b"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.5)"; }}
            >
              <Plus size={12} /> Add line item
            </button>
          )
        )}

        {/* Totals */}
        <div style={{
          borderTop: "1px solid rgba(63,63,70,0.4)", paddingTop: "10px",
          display: "flex", flexDirection: "column", gap: "4px",
        }}>
          {invoice.tax_cents > 0 && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#71717a" }}>
                <span>Subtotal</span>
                <span>{formatCents(invoice.subtotal_cents)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#71717a" }}>
                <span>Tax</span>
                <span>{formatCents(invoice.tax_cents)}</span>
              </div>
            </>
          )}
          <div style={{
            display: "flex", justifyContent: "space-between",
            fontSize: "0.92rem", fontWeight: 800, color: "#f4f4f5",
            paddingTop: invoice.tax_cents > 0 ? "6px" : "0",
            borderTop: invoice.tax_cents > 0 ? "1px solid rgba(63,63,70,0.4)" : "none",
          }}>
            <span>Total</span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>{formatCents(invoice.total_cents)}</span>
          </div>
        </div>

        {/* Notes */}
        {(isDraft || invoice.notes) && (
          <div style={{ marginTop: "10px" }}>
            {editingNotes ? (
              <div style={{ display: "flex", gap: "6px", alignItems: "flex-start" }}>
                <textarea
                  value={notesValue}
                  onChange={e => setNotesValue(e.target.value)}
                  placeholder="Add notes (e.g., payment method, discounts applied)…"
                  rows={2}
                  autoFocus
                  style={{
                    flex: 1, padding: "8px 10px", borderRadius: "8px", fontSize: "0.75rem",
                    background: "rgba(39,39,42,0.6)", border: "1px solid rgba(63,63,70,0.5)",
                    color: "#d4d4d8", outline: "none", fontFamily: "inherit", resize: "vertical",
                  }}
                />
                <button
                  onClick={handleSaveNotes}
                  style={{
                    padding: "6px 10px", borderRadius: "6px", fontSize: "0.72rem", fontWeight: 600,
                    background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.3)",
                    color: "#60a5fa", cursor: "pointer", fontFamily: "inherit",
                  }}
                >
                  Save
                </button>
              </div>
            ) : (
              <button
                onClick={() => setEditingNotes(true)}
                style={{
                  width: "100%", textAlign: "left", padding: "6px 10px", borderRadius: "6px",
                  background: "transparent", border: "1px dashed rgba(63,63,70,0.4)",
                  color: invoice.notes ? "#a1a1aa" : "#52525b", cursor: "pointer",
                  fontSize: "0.72rem", fontFamily: "inherit",
                }}
              >
                {invoice.notes || "✏️ Add notes…"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      {!isPaid && (
        <div style={{
          padding: "10px 16px 14px", borderTop: "1px solid rgba(63,63,70,0.3)",
          display: "flex", gap: "8px",
        }}>
          {isDraft && (
            <button
              onClick={handleSendInvoice}
              disabled={actionLoading === "send"}
              style={{
                flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                padding: "9px 14px", borderRadius: "8px", fontSize: "0.78rem", fontWeight: 600,
                background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.3)",
                color: "#60a5fa", cursor: actionLoading ? "wait" : "pointer",
                fontFamily: "inherit", transition: "background 0.15s",
                opacity: actionLoading === "send" ? 0.6 : 1,
              }}
              onMouseEnter={e => { if (!actionLoading) e.currentTarget.style.background = "rgba(96,165,250,0.18)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(96,165,250,0.1)"; }}
            >
              {actionLoading === "send" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Send size={14} />}
              Send to Client
            </button>
          )}

          {(isDraft || isSent) && (
            <button
              onClick={handleMarkPaid}
              disabled={actionLoading === "paid"}
              style={{
                flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
                padding: "9px 14px", borderRadius: "8px", fontSize: "0.78rem", fontWeight: 600,
                background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)",
                color: "#10b981", cursor: actionLoading ? "wait" : "pointer",
                fontFamily: "inherit", transition: "background 0.15s",
                opacity: actionLoading === "paid" ? 0.6 : 1,
              }}
              onMouseEnter={e => { if (!actionLoading) e.currentTarget.style.background = "rgba(16,185,129,0.18)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(16,185,129,0.1)"; }}
            >
              {actionLoading === "paid" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <CreditCard size={14} />}
              {isSent ? "Collect Payment" : "Mark Paid"}
            </button>
          )}

          <button
            onClick={() => window.print()}
            title="Print receipt"
            style={{
              padding: "9px 12px", borderRadius: "8px",
              background: "rgba(39,39,42,0.5)", border: "1px solid rgba(63,63,70,0.4)",
              color: "#71717a", cursor: "pointer", display: "flex", alignItems: "center",
              transition: "all 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.color = "#a1a1aa"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.7)"; }}
            onMouseLeave={e => { e.currentTarget.style.color = "#71717a"; e.currentTarget.style.borderColor = "rgba(63,63,70,0.4)"; }}
          >
            <Printer size={14} />
          </button>
        </div>
      )}

      {/* Paid confirmation banner */}
      {isPaid && (
        <div style={{
          padding: "10px 16px", borderTop: "1px solid rgba(16,185,129,0.2)",
          background: "rgba(16,185,129,0.06)",
          display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
          color: "#10b981", fontSize: "0.78rem", fontWeight: 600,
        }}>
          <CheckCircle2 size={14} />
          Payment collected — {formatCents(invoice.total_cents)}
        </div>
      )}
    </div>
  );
}
