'use client';
import React from 'react';

// ── ProgressBar ──────────────────────────────────────────────────────────
export function ProgressBar({ step, total }: { step: number; total: number }) {
  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '8px' }}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: '4px',
              borderRadius: '2px',
              background: i < step
                ? 'linear-gradient(90deg, #6366f1, #8b5cf6)'
                : 'rgba(63,63,70,0.4)',
              transition: 'all 0.3s ease',
            }}
          />
        ))}
      </div>
      <p style={{ fontSize: '0.7rem', color: '#71717a', margin: 0 }}>Step {step} of {total}</p>
    </div>
  );
}

// ── BookingCard ──────────────────────────────────────────────────────────
export function BookingCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: 'rgba(24,24,27,0.8)',
      border: '1px solid rgba(63,63,70,0.4)',
      borderRadius: '14px',
      padding: '20px',
      backdropFilter: 'blur(12px)',
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── PageTitle ────────────────────────────────────────────────────────────
export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: '#f4f4f5', lineHeight: 1.2 }}>
        {title}
      </h1>
      {subtitle && (
        <p style={{ margin: '6px 0 0', fontSize: '0.82rem', color: '#71717a' }}>{subtitle}</p>
      )}
    </div>
  );
}

// ── PrimaryButton ────────────────────────────────────────────────────────
export function PrimaryButton({
  children, onClick, disabled, loading, type = 'button',
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit';
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        width: '100%', padding: '14px 20px',
        borderRadius: '10px', border: 'none',
        background: disabled || loading
          ? 'rgba(99,102,241,0.2)'
          : 'linear-gradient(135deg, #6366f1, #7c3aed)',
        color: disabled || loading ? '#6366f1' : '#fff',
        fontSize: '0.92rem', fontWeight: 700,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        fontFamily: 'inherit',
        minHeight: '48px',
        transition: 'all 0.2s ease',
      }}
    >
      {loading ? 'Please wait…' : children}
    </button>
  );
}

// ── SecondaryButton ──────────────────────────────────────────────────────
export function SecondaryButton({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'transparent',
        border: '1px solid rgba(63,63,70,0.5)',
        borderRadius: '8px', padding: '10px 16px',
        color: '#71717a', cursor: 'pointer',
        fontSize: '0.8rem', fontFamily: 'inherit',
        minHeight: '44px', width: '100%',
      }}
    >
      {children}
    </button>
  );
}

// ── InlineError ──────────────────────────────────────────────────────────
export function InlineError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div style={{
      background: 'rgba(239,68,68,0.08)',
      border: '1px solid rgba(239,68,68,0.25)',
      borderRadius: '8px', padding: '10px 14px',
      fontSize: '0.78rem', color: '#fca5a5', marginTop: '12px',
    }}>
      {message}
    </div>
  );
}

// ── LoadingSpinner ───────────────────────────────────────────────────────
export function LoadingSpinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        border: '3px solid rgba(99,102,241,0.2)',
        borderTopColor: '#6366f1',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── UrgencySelector ──────────────────────────────────────────────────────
const URGENCY_OPTIONS = [
  { value: 'wellness', label: 'Wellness', color: '#22c55e', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.3)' },
  { value: 'routine', label: 'Routine', color: '#6366f1', bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)' },
  { value: 'urgent', label: 'Urgent', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)' },
  { value: 'emergency', label: 'Emergency', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)' },
];

export function UrgencySelector({
  value, onChange,
}: {
  value: string;
  onChange: (v: 'wellness' | 'routine' | 'urgent' | 'emergency') => void;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
      {URGENCY_OPTIONS.map(opt => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value as 'wellness' | 'routine' | 'urgent' | 'emergency')}
          style={{
            padding: '10px 4px',
            borderRadius: '8px',
            border: `1px solid ${value === opt.value ? opt.border : 'rgba(63,63,70,0.4)'}`,
            background: value === opt.value ? opt.bg : 'transparent',
            color: value === opt.value ? opt.color : '#71717a',
            fontSize: '0.72rem', fontWeight: 600,
            cursor: 'pointer', fontFamily: 'inherit',
            minHeight: '44px',
            transition: 'all 0.2s ease',
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ── PetCard ──────────────────────────────────────────────────────────────
const SPECIES_EMOJI: Record<string, string> = {
  dog: '🐶', cat: '🐱', rabbit: '🐰', bird: '🐦', reptile: '🦎',
};

function calcAge(dob?: string): string {
  if (!dob) return '';
  const birth = new Date(dob);
  const now = new Date();
  const years = now.getFullYear() - birth.getFullYear();
  return `${years} yr${years !== 1 ? 's' : ''}`;
}

export function PetCard({
  pet, selected, onClick,
}: {
  pet: { id: string; name: string; species: string; breed: string; dob?: string };
  selected: boolean;
  onClick: () => void;
}) {
  const emoji = SPECIES_EMOJI[pet.species?.toLowerCase()] || '🐾';
  const age = calcAge(pet.dob);
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: '100%', textAlign: 'left',
        background: selected ? 'rgba(99,102,241,0.12)' : 'rgba(24,24,27,0.6)',
        border: `1px solid ${selected ? 'rgba(99,102,241,0.5)' : 'rgba(63,63,70,0.4)'}`,
        borderRadius: '12px', padding: '16px',
        cursor: 'pointer', fontFamily: 'inherit',
        transition: 'all 0.2s ease',
        minHeight: '80px',
        display: 'flex', alignItems: 'center', gap: '14px',
      }}
    >
      <span style={{ fontSize: '2rem' }}>{emoji}</span>
      <div>
        <p style={{ margin: 0, fontWeight: 700, fontSize: '0.95rem', color: '#e4e4e7' }}>{pet.name}</p>
        <p style={{ margin: '2px 0 0', fontSize: '0.72rem', color: '#71717a' }}>
          {pet.breed || pet.species}{age ? ` · ${age}` : ''}
        </p>
      </div>
      {selected && (
        <div style={{ marginLeft: 'auto', color: '#a5b4fc', fontSize: '1.1rem' }}>✓</div>
      )}
    </button>
  );
}

// ── SlotCard ─────────────────────────────────────────────────────────────
export interface SlotType {
  slot_id: string;
  resource_id?: string;
  resource_name?: string;
  vet_name?: string;
  vet_display_name?: string;
  start_datetime: string;
  end_datetime: string;
  duration_minutes: number;
  rank?: number;
  rank_label?: string;
}

export function SlotCard({
  slot, onBook, loading,
}: {
  slot: SlotType;
  onBook: (slot: SlotType) => void;
  loading: boolean;
}) {
  const start = new Date(slot.start_datetime);
  const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  const vetName = slot.vet_display_name || slot.resource_name || 'Any Vet';
  return (
    <div style={{
      background: 'rgba(24,24,27,0.7)',
      border: '1px solid rgba(63,63,70,0.4)',
      borderRadius: '12px', padding: '16px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <p style={{ margin: 0, fontWeight: 700, fontSize: '0.95rem', color: '#f4f4f5' }}>{dateStr}</p>
          <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: '#a5b4fc' }}>
            {timeStr} · {slot.duration_minutes} min · {vetName}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onBook(slot)}
          disabled={loading}
          style={{
            padding: '8px 16px', borderRadius: '8px', border: 'none',
            background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
            color: '#fff', fontSize: '0.78rem', fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit', minHeight: '44px', minWidth: '100px',
            opacity: loading ? 0.6 : 1, flexShrink: 0,
          }}
        >
          {loading ? '…' : 'Book This'}
        </button>
      </div>
    </div>
  );
}

// ── InputField ───────────────────────────────────────────────────────────
export function InputField({
  label, id, type = 'text', value, onChange, placeholder, required, maxLength,
}: {
  label: string;
  id: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  maxLength?: number;
}) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <label
        htmlFor={id}
        style={{ display: 'block', fontSize: '0.72rem', color: '#71717a', marginBottom: '5px', fontWeight: 500 }}
      >
        {label}{required && <span style={{ color: '#ef4444', marginLeft: '2px' }}>*</span>}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        required={required}
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'rgba(39,39,42,0.6)',
          border: '1px solid rgba(63,63,70,0.5)',
          borderRadius: '8px', padding: '11px 14px',
          color: '#e4e4e7', fontSize: '0.88rem',
          outline: 'none', fontFamily: 'inherit',
          minHeight: '44px',
        }}
      />
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────────────────
export function Toast({ message, type = 'error' }: { message: string | null; type?: 'error' | 'success' }) {
  if (!message) return null;
  const isError = type === 'error';
  return (
    <div style={{
      position: 'fixed', top: '24px', right: '16px', left: '16px',
      maxWidth: '480px', margin: '0 auto',
      background: isError ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)',
      border: `1px solid ${isError ? 'rgba(239,68,68,0.35)' : 'rgba(34,197,94,0.35)'}`,
      borderRadius: '10px', padding: '12px 16px',
      fontSize: '0.82rem', color: isError ? '#fca5a5' : '#86efac',
      zIndex: 200, backdropFilter: 'blur(8px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      animation: 'slideDown 0.25s ease',
    }}>
      <style>{`@keyframes slideDown { from { transform: translateY(-10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }`}</style>
      {message}
    </div>
  );
}
