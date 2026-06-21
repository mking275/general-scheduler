import { BookingProvider } from './BookingContext';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Book an Appointment | VetAgent',
  description: 'Book your veterinary appointment online.',
};

export default function BookingLayout({ children }: { children: React.ReactNode }) {
  return (
    <BookingProvider>
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #09090b 0%, #0f0f12 50%, #09090b 100%)',
        fontFamily: "'Inter', -apple-system, sans-serif",
        color: '#e4e4e7',
      }}>
        {/* Top bar */}
        <div style={{
          background: 'rgba(18,18,21,0.95)',
          borderBottom: '1px solid rgba(63,63,70,0.4)',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: '7px',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '14px', fontWeight: 700, color: '#fff',
          }}>V</div>
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#a5b4fc' }}>VetAgent</span>
        </div>

        {/* Page content */}
        <div style={{ maxWidth: '520px', margin: '0 auto', padding: '24px 16px 80px' }}>
          {children}
        </div>

        {/* Vera footer */}
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0,
          background: 'rgba(9,9,11,0.95)',
          borderTop: '1px solid rgba(63,63,70,0.3)',
          padding: '8px 16px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
          fontSize: '0.68rem', color: '#52525b',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 14, height: 14, borderRadius: '50%',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            fontSize: '7px', fontWeight: 700, color: '#fff',
          }}>V</span>
          <span>Powered by <strong style={{ color: '#71717a' }}>Vera</strong> — AI Chief of Staff for veterinary practices</span>
        </div>
      </div>
    </BookingProvider>
  );
}
