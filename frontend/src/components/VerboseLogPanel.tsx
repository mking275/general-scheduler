'use client';

import { useState } from 'react';
import { Terminal, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * VerboseLogPanel — floating verbose log drawer for the onboarding pages.
 * Sits at the bottom-right corner and can be expanded/collapsed.
 * Uses only vanilla CSS inline styles to avoid conflicts with the main app's CSS.
 */
export default function VerboseLogPanel({ logs }: { logs: string[] }) {
  const [open, setOpen] = useState(false);

  const getColor = (log: string) => {
    if (log.includes('VERA (Onboarding)')) return '#a78bfa'; // purple
    if (log.includes('Error') || log.includes('error')) return '#f87171'; // red
    if (log.includes('confirmed')) return '#4ade80'; // green
    if (log.includes('corrected')) return '#fbbf24'; // amber
    return '#71717a'; // default zinc
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '1rem',
        right: '1rem',
        width: open ? '340px' : '200px',
        background: '#09090b',
        border: '1px solid rgba(63,63,70,0.6)',
        borderRadius: '10px',
        zIndex: 9999,
        fontFamily: 'monospace',
        fontSize: '0.75rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 12px',
          background: 'rgba(15,15,17,0.9)',
          border: 'none',
          borderBottom: open ? '1px solid rgba(63,63,70,0.5)' : 'none',
          color: '#10b981',
          cursor: 'pointer',
          justifyContent: 'space-between',
        }}
        aria-label={open ? 'Collapse Vera log' : 'Expand Vera log'}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Terminal size={13} />
          <span style={{ fontWeight: 700, letterSpacing: '0.05em', fontSize: '0.72rem' }}>
            VERA LOG
          </span>
          {logs.length > 0 && (
            <span
              style={{
                background: '#6C63FF',
                color: 'white',
                borderRadius: '999px',
                padding: '0px 5px',
                fontSize: '0.65rem',
                fontWeight: 700,
              }}
            >
              {logs.length}
            </span>
          )}
        </span>
        {open ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
      </button>

      {/* Log entries */}
      {open && (
        <div
          style={{
            maxHeight: '240px',
            overflowY: 'auto',
            padding: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          {logs.length === 0 && (
            <div style={{ color: '#3f3f46', fontStyle: 'italic', padding: '8px', textAlign: 'center' }}>
              Awaiting Vera actions...
            </div>
          )}
          {logs.map((log, i) => (
            <div
              key={i}
              style={{
                color: getColor(log),
                padding: '4px 6px',
                borderRadius: '4px',
                background: 'rgba(255,255,255,0.02)',
                borderLeft: `2px solid ${getColor(log)}`,
                lineHeight: 1.4,
                wordBreak: 'break-word',
              }}
            >
              {log}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
