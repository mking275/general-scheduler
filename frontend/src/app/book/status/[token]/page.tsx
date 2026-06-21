'use client';
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { API } from '../../BookingContext';
import { BookingCard, LoadingSpinner, InlineError } from '../../components';

interface BookingStatus {
  booking_token: string;
  lifecycle_state: string;
  clinic_name: string;
  clinic_phone?: string;
  patient_name: string;
  owner_name: string;
  appointment_type: string;
  start_datetime: string;
  end_datetime: string;
  vet_name?: string;
  status: string;
  intake_token?: string;
  booked_via: string;
}

const LIFECYCLE_STEPS = [
  { key: 'booked', label: 'Booked', icon: '📋' },
  { key: 'intake_sent', label: 'Intake Form Sent', icon: '📨' },
  { key: 'intake_complete', label: 'Intake Completed', icon: '✅' },
  { key: 'confirmed', label: 'Confirmed', icon: '✔️' },
  { key: 'in_progress', label: 'In Progress', icon: '🩺' },
  { key: 'complete', label: 'Visit Complete', icon: '🎉' },
];

function stepIndex(state: string): number {
  return LIFECYCLE_STEPS.findIndex(s => s.key === state);
}

export default function StatusPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const [booking, setBooking] = useState<BookingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.token) return;
    setLoading(true);
    fetch(`${API}/public/status/${params.token}`)
      .then(async res => {
        if (res.status === 404) throw new Error('Booking not found. Please check your link.');
        if (!res.ok) throw new Error('Unable to load appointment status.');
        return res.json();
      })
      .then(setBooking)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.token]);

  if (loading) return <LoadingSpinner />;

  if (error || !booking) {
    return (
      <div style={{ paddingTop: '24px' }}>
        <BookingCard>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>❓</div>
            <p style={{ color: '#fca5a5', fontWeight: 600, marginBottom: '8px' }}>{error || 'Booking not found'}</p>
          </div>
        </BookingCard>
      </div>
    );
  }

  const start = new Date(booking.start_datetime);
  const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  const currentStep = stepIndex(booking.lifecycle_state);

  const isCancelled = booking.status === 'cancelled';
  const isComplete = booking.lifecycle_state === 'complete' || booking.lifecycle_state === 'follow_up_sent';

  return (
    <div style={{ paddingTop: '8px' }}>
      {/* Success / status header */}
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '8px' }}>
          {isCancelled ? '❌' : isComplete ? '🎉' : '✅'}
        </div>
        <h1 style={{ margin: '0 0 6px', fontSize: '1.4rem', fontWeight: 800, color: '#f4f4f5' }}>
          {isCancelled ? 'Appointment Cancelled' : isComplete ? 'Visit Complete!' : 'Appointment Confirmed'}
        </h1>
        <p style={{ margin: 0, fontSize: '0.82rem', color: '#71717a' }}>
          {isCancelled
            ? 'This appointment has been cancelled.'
            : `${booking.clinic_name} · Ref: ${params.token.slice(0, 8).toUpperCase()}`}
        </p>
      </div>

      {/* Intake banner */}
      {booking.intake_token && !isComplete && !isCancelled && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15))',
          border: '1px solid rgba(99,102,241,0.4)',
          borderRadius: '12px', padding: '16px',
          marginBottom: '16px',
        }}>
          <p style={{ margin: '0 0 4px', fontWeight: 700, fontSize: '0.92rem', color: '#a5b4fc' }}>
            📋 Complete your pre-visit check-in
          </p>
          <p style={{ margin: '0 0 12px', fontSize: '0.78rem', color: '#71717a' }}>
            Help us prepare for {booking.patient_name}'s visit by answering a few quick questions.
          </p>
          <button
            onClick={() => router.push(`/book/intake/${booking.intake_token}`)}
            style={{
              padding: '10px 20px', borderRadius: '8px', border: 'none',
              background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
              color: '#fff', fontWeight: 700, cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '0.85rem', minHeight: '44px',
            }}
          >
            Start Check-In →
          </button>
        </div>
      )}

      {/* Appointment details */}
      <BookingCard style={{ marginBottom: '14px' }}>
        <p style={{ margin: '0 0 12px', fontSize: '0.68rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Appointment Details
        </p>
        {[
          { label: '🐾 Patient', value: booking.patient_name },
          { label: '👤 Owner', value: booking.owner_name },
          { label: '📅 Date', value: dateStr },
          { label: '🕐 Time', value: timeStr },
          { label: '🏥 Clinic', value: booking.clinic_name },
          ...(booking.vet_name ? [{ label: '🩺 Veterinarian', value: booking.vet_name }] : []),
          { label: '📋 Type', value: booking.appointment_type },
        ].map(({ label, value }) => (
          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(63,63,70,0.2)' }}>
            <span style={{ fontSize: '0.78rem', color: '#71717a' }}>{label}</span>
            <span style={{ fontSize: '0.80rem', color: '#e4e4e7', fontWeight: 600 }}>{value}</span>
          </div>
        ))}
        {booking.clinic_phone && (
          <div style={{ paddingTop: '12px' }}>
            <a href={`tel:${booking.clinic_phone}`} style={{ color: '#a5b4fc', fontSize: '0.82rem', textDecoration: 'none' }}>
              📞 {booking.clinic_phone}
            </a>
          </div>
        )}
      </BookingCard>

      {/* Lifecycle progress */}
      {!isCancelled && (
        <BookingCard style={{ marginBottom: '14px' }}>
          <p style={{ margin: '0 0 14px', fontSize: '0.68rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Appointment Progress
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
            {LIFECYCLE_STEPS.map((step, idx) => {
              const done = idx <= currentStep;
              const current = idx === currentStep;
              return (
                <div key={step.key} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: idx < LIFECYCLE_STEPS.length - 1 ? '0' : '0' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: done
                        ? (current ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : 'rgba(99,102,241,0.3)')
                        : 'rgba(63,63,70,0.3)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: done ? '0.75rem' : '0.65rem',
                      border: current ? '2px solid #6366f1' : 'none',
                      flexShrink: 0,
                    }}>
                      {done ? step.icon : '○'}
                    </div>
                    {idx < LIFECYCLE_STEPS.length - 1 && (
                      <div style={{
                        width: 2, height: 20,
                        background: idx < currentStep ? 'rgba(99,102,241,0.4)' : 'rgba(63,63,70,0.3)',
                      }} />
                    )}
                  </div>
                  <div style={{ paddingTop: '4px', paddingBottom: idx < LIFECYCLE_STEPS.length - 1 ? '20px' : '0' }}>
                    <p style={{
                      margin: 0, fontSize: '0.82rem',
                      fontWeight: current ? 700 : 400,
                      color: done ? '#e4e4e7' : '#52525b',
                    }}>
                      {step.label}
                    </p>
                    {current && (
                      <p style={{ margin: '2px 0 0', fontSize: '0.7rem', color: '#6366f1' }}>← Current status</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </BookingCard>
      )}

      <InlineError message={null} />

      {/* CTA */}
      <div style={{ textAlign: 'center', marginTop: '8px' }}>
        <button
          onClick={() => {
            const slug = window.location.pathname.split('/')[2] || '';
            if (slug && slug !== 'status') {
              router.push(`/book/${slug}`);
            } else {
              router.push('/book');
            }
          }}
          style={{
            background: 'transparent', border: '1px solid rgba(63,63,70,0.5)',
            borderRadius: '8px', padding: '10px 20px',
            color: '#71717a', cursor: 'pointer', fontFamily: 'inherit',
            fontSize: '0.82rem', minHeight: '44px',
          }}
        >
          Book Another Appointment
        </button>
      </div>
    </div>
  );
}
