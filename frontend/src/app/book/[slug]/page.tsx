'use client';
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking, API } from '../BookingContext';
import { BookingCard, PageTitle, PrimaryButton, InlineError, LoadingSpinner } from '../components';

interface ClinicData {
  clinic_id: string;
  name: string;
  slug: string;
  address: string;
  phone: string;
  email: string;
  timezone: string;
  booking_config: {
    online_booking_enabled: boolean;
    emergency_phone: string;
    emergency_message: string;
    cancellation_policy: string;
    advance_booking_days: number;
  };
}

export default function ClinicLandingPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const { setClinic } = useBooking();

  const [clinic, setClinicData] = useState<ClinicData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.slug) return;
    setLoading(true);
    fetch(`${API}/public/clinics/${params.slug}`)
      .then(async res => {
        if (res.status === 404) throw new Error('Clinic not found. Please check your booking link.');
        if (!res.ok) throw new Error('Unable to load clinic information. Please try again.');
        return res.json();
      })
      .then((data: ClinicData) => {
        setClinicData(data);
        setClinic({
          clinicSlug: data.slug,
          clinicName: data.name,
          clinicPhone: data.phone,
          emergencyPhone: data.booking_config.emergency_phone || '',
          onlineBookingEnabled: data.booking_config.online_booking_enabled,
          cancellationPolicy: data.booking_config.cancellation_policy || '',
        });
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.slug, setClinic]);

  if (loading) return <LoadingSpinner />;
  if (error) {
    return (
      <div style={{ paddingTop: '24px' }}>
        <BookingCard>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🐾</div>
            <p style={{ color: '#fca5a5', fontWeight: 600, marginBottom: '8px' }}>{error}</p>
            <p style={{ color: '#52525b', fontSize: '0.78rem', margin: 0 }}>
              If you believe this is an error, please contact the clinic directly.
            </p>
          </div>
        </BookingCard>
      </div>
    );
  }
  if (!clinic) return null;

  const { booking_config: cfg } = clinic;

  return (
    <div style={{ paddingTop: '8px' }}>
      {/* Emergency banner */}
      {cfg.emergency_phone && (
        <div style={{
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: '10px', padding: '12px 16px',
          marginBottom: '16px',
          display: 'flex', alignItems: 'flex-start', gap: '10px',
        }}>
          <span style={{ fontSize: '1.1rem' }}>🚨</span>
          <div>
            <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 700, color: '#fca5a5' }}>
              Pet Emergency? Call immediately:
            </p>
            <a
              href={`tel:${cfg.emergency_phone}`}
              style={{ color: '#f87171', fontWeight: 700, fontSize: '1rem', textDecoration: 'none' }}
            >
              {cfg.emergency_phone}
            </a>
            {cfg.emergency_message && (
              <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: '#fca5a5' }}>{cfg.emergency_message}</p>
            )}
          </div>
        </div>
      )}

      {/* Clinic hero card */}
      <BookingCard style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.5rem', flexShrink: 0,
          }}>🏥</div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#f4f4f5' }}>{clinic.name}</h2>
            {clinic.address && (
              <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: '#71717a' }}>{clinic.address}</p>
            )}
          </div>
        </div>

        {/* Contact info */}
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
          {clinic.phone && (
            <div>
              <p style={{ margin: 0, fontSize: '0.65rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Phone</p>
              <a href={`tel:${clinic.phone}`} style={{ color: '#a5b4fc', fontSize: '0.82rem', textDecoration: 'none' }}>
                {clinic.phone}
              </a>
            </div>
          )}
          {clinic.email && (
            <div>
              <p style={{ margin: 0, fontSize: '0.65rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Email</p>
              <a href={`mailto:${clinic.email}`} style={{ color: '#a5b4fc', fontSize: '0.82rem', textDecoration: 'none' }}>
                {clinic.email}
              </a>
            </div>
          )}
        </div>

        {/* Feature bullets */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px' }}>
          {[
            { icon: '📅', text: `Book up to ${cfg.advance_booking_days || 30} days in advance` },
            { icon: '✅', text: 'Instant confirmation' },
            { icon: '📱', text: 'Pre-visit intake form sent after booking' },
          ].map(({ icon, text }) => (
            <div key={text} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1rem' }}>{icon}</span>
              <span style={{ fontSize: '0.8rem', color: '#a1a1aa' }}>{text}</span>
            </div>
          ))}
        </div>

        {cfg.online_booking_enabled ? (
          <PrimaryButton onClick={() => router.push(`/book/${params.slug}/identify`)}>
            Book an Appointment →
          </PrimaryButton>
        ) : (
          <div style={{
            background: 'rgba(63,63,70,0.2)', border: '1px solid rgba(63,63,70,0.4)',
            borderRadius: '10px', padding: '14px 16px', textAlign: 'center',
          }}>
            <p style={{ margin: 0, color: '#71717a', fontSize: '0.85rem' }}>
              Online booking is currently unavailable. Please call us to schedule.
            </p>
            {clinic.phone && (
              <a href={`tel:${clinic.phone}`} style={{
                display: 'block', marginTop: '8px', color: '#a5b4fc',
                fontWeight: 700, fontSize: '1rem', textDecoration: 'none',
              }}>{clinic.phone}</a>
            )}
          </div>
        )}
      </BookingCard>

      {/* Track existing appointment */}
      <div style={{ textAlign: 'center' }}>
        <button
          onClick={() => {
            const token = window.prompt('Enter your booking token to track your appointment:');
            if (token?.trim()) router.push(`/book/status/${token.trim()}`);
          }}
          style={{
            background: 'transparent', border: 'none', color: '#52525b',
            fontSize: '0.78rem', cursor: 'pointer', textDecoration: 'underline',
            fontFamily: 'inherit', padding: '8px',
          }}
        >
          Track an existing appointment
        </button>
      </div>

      <InlineError message={null} />
    </div>
  );
}
