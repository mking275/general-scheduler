'use client';
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking, API } from '../../BookingContext';
import {
  PageTitle, BookingCard, PrimaryButton, SecondaryButton,
  InlineError, LoadingSpinner,
} from '../../components';

function Countdown({ expiresAt }: { expiresAt: string }) {
  const [secs, setSecs] = useState<number>(() => {
    const diff = Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000);
    return Math.max(0, diff);
  });

  useEffect(() => {
    if (secs <= 0) return;
    const t = setInterval(() => setSecs(s => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [secs]);

  const mins = Math.floor(secs / 60);
  const s = secs % 60;
  const isLow = secs < 120;

  return (
    <div style={{
      background: isLow ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.08)',
      border: `1px solid ${isLow ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.25)'}`,
      borderRadius: '8px', padding: '10px 14px',
      fontSize: '0.78rem', color: isLow ? '#fca5a5' : '#fbbf24',
      display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px',
    }}>
      <span style={{ fontSize: '1rem' }}>⏱</span>
      {secs > 0
        ? `Slot held for ${mins}:${s.toString().padStart(2, '0')} — confirm before it expires`
        : 'Hold expired — please go back and select a new slot'
      }
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(63,63,70,0.25)' }}>
      <span style={{ fontSize: '0.78rem', color: '#71717a' }}>{label}</span>
      <span style={{ fontSize: '0.82rem', color: '#e4e4e7', fontWeight: 600, textAlign: 'right', maxWidth: '60%' }}>{value}</span>
    </div>
  );
}

export default function ConfirmPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const {
    ownerId, ownerName, selectedPet, appointmentType,
    clinicName, clinicPhone, selectedSlot, holdExpiresAt,
    urgency, clientNotes, cancellationPolicy,
    smsConsent, setSmsConsent,
    holdId, sessionToken,
  } = useBooking();

  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guard
  useEffect(() => {
    if (!ownerId || !selectedSlot) {
      router.replace(`/book/${params.slug}/identify`);
    }
  }, [ownerId, selectedSlot, params.slug, router]);

  if (!ownerId || !selectedSlot || !selectedPet) return <LoadingSpinner />;

  const start = new Date(selectedSlot.startDatetime);
  const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      const res = await fetch(`${API}/public/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          clinic_slug: params.slug,
          owner_id: ownerId,
          patient_id: selectedPet.id,
          appointment_type_id: appointmentType,
          slot_id: selectedSlot.slotId,
          resource_id: selectedSlot.resourceId,
          start_datetime: selectedSlot.startDatetime,
          end_datetime: selectedSlot.endDatetime,
          urgency,
          client_notes: clientNotes,
          sms_consent: smsConsent,
          hold_id: holdId,
          session_token: sessionToken,
        }),
      });

      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        if (res.status === 409) {
          setError('Your hold expired. Please go back and select a new slot.');
        } else {
          throw new Error(d.detail || 'Booking failed. Please try again.');
        }
        return;
      }

      const data = await res.json();
      const token = data.booking_token || data.token;
      if (token) {
        router.push(`/book/status/${token}`);
      } else {
        setError('Booking created but no confirmation token received. Please contact the clinic.');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Booking failed.');
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: '#f4f4f5' }}>
          Review & Confirm
        </h1>
        <p style={{ margin: '6px 0 0', fontSize: '0.82rem', color: '#71717a' }}>
          Almost done — check the details below
        </p>
      </div>

      {/* Hold countdown */}
      {holdExpiresAt && <Countdown expiresAt={holdExpiresAt} />}

      {/* Appointment summary */}
      <BookingCard style={{ marginBottom: '14px' }}>
        <p style={{ margin: '0 0 4px', fontSize: '0.68rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Appointment Summary
        </p>
        <SummaryRow label="Clinic" value={clinicName || params.slug} />
        <SummaryRow label="Pet" value={`${selectedPet.name} · ${selectedPet.breed || selectedPet.species}`} />
        <SummaryRow label="Owner" value={ownerName} />
        <SummaryRow label="Appointment" value={appointmentType} />
        <SummaryRow label="Date" value={dateStr} />
        <SummaryRow label="Time" value={timeStr} />
        {selectedSlot.resourceName && (
          <SummaryRow label="Veterinarian" value={selectedSlot.resourceName} />
        )}
        <SummaryRow label="Urgency" value={urgency.charAt(0).toUpperCase() + urgency.slice(1)} />
        {clientNotes && (
          <div style={{ paddingTop: '10px' }}>
            <p style={{ margin: '0 0 4px', fontSize: '0.72rem', color: '#71717a' }}>Your notes:</p>
            <p style={{ margin: 0, fontSize: '0.80rem', color: '#a1a1aa', fontStyle: 'italic' }}>"{clientNotes}"</p>
          </div>
        )}
      </BookingCard>

      {/* Cancellation policy */}
      {cancellationPolicy && (
        <BookingCard style={{ marginBottom: '14px', background: 'rgba(18,18,21,0.6)' }}>
          <p style={{ margin: '0 0 6px', fontSize: '0.68rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Cancellation Policy
          </p>
          <p style={{ margin: 0, fontSize: '0.78rem', color: '#71717a', lineHeight: 1.5 }}>
            {cancellationPolicy}
          </p>
        </BookingCard>
      )}

      {/* SMS consent */}
      <BookingCard style={{ marginBottom: '16px' }}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', cursor: 'pointer' }}>
          <input
            id="sms-consent"
            type="checkbox"
            checked={smsConsent}
            onChange={e => setSmsConsent(e.target.checked)}
            style={{ width: '20px', height: '20px', accentColor: '#6366f1', marginTop: '2px', flexShrink: 0 }}
          />
          <span style={{ fontSize: '0.78rem', color: '#a1a1aa', lineHeight: 1.5 }}>
            I consent to receive appointment reminders and pre-visit intake forms via SMS.
            Message &amp; data rates may apply. Reply STOP to opt out.
          </span>
        </label>
      </BookingCard>

      <InlineError message={error} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
        <PrimaryButton onClick={handleConfirm} loading={confirming}>
          Confirm Appointment ✓
        </PrimaryButton>
        <SecondaryButton onClick={() => router.push(`/book/${params.slug}/slot`)}>
          ← Choose a different time
        </SecondaryButton>
      </div>

      <p style={{ textAlign: 'center', fontSize: '0.68rem', color: '#52525b', marginTop: '16px' }}>
        By confirming, you agree to our cancellation policy above.
        {clinicPhone && ` Questions? Call ${clinicPhone}.`}
      </p>
    </div>
  );
}
