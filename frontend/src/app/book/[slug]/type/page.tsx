'use client';
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking, API } from '../../BookingContext';
import {
  ProgressBar, PageTitle, BookingCard, PrimaryButton, SecondaryButton,
  InlineError, LoadingSpinner, UrgencySelector,
} from '../../components';

interface AppointmentType {
  id: string;
  name: string;
  duration_minutes: number;
  intake_question_set: string;
  description: string;
}

export default function AppointmentTypePage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const {
    selectedPet, ownerId, clinicSlug, clinicPhone,
    setAppointmentType, setUrgency, setClientNotes,
    urgency, clientNotes, appointmentTypeSlug,
  } = useBooking();

  const [types, setTypes] = useState<AppointmentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<AppointmentType | null>(null);
  const [notes, setNotes] = useState(clientNotes);
  const [localUrgency, setLocalUrgency] = useState(urgency);

  // Guard
  useEffect(() => {
    if (!ownerId || !selectedPet) {
      router.replace(`/book/${params.slug}/identify`);
    }
  }, [ownerId, selectedPet, params.slug, router]);

  useEffect(() => {
    if (!params.slug) return;
    setLoading(true);
    fetch(`${API}/public/clinics/${params.slug}/appointment-types`)
      .then(async res => {
        if (res.status === 403) throw new Error('Online booking is currently disabled for this clinic.');
        if (res.status === 404) throw new Error('Clinic not found.');
        if (!res.ok) throw new Error('Failed to load appointment types.');
        return res.json();
      })
      .then(data => {
        const apptTypes: AppointmentType[] = data.appointment_types || [];
        setTypes(apptTypes);
        // Restore previous selection if any
        if (appointmentTypeSlug) {
          const prev = apptTypes.find(t => t.id === appointmentTypeSlug);
          if (prev) setSelectedType(prev);
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.slug, appointmentTypeSlug]);

  if (!ownerId || !selectedPet) return <LoadingSpinner />;

  const handleContinue = () => {
    if (!selectedType) { setError('Please select an appointment type.'); return; }
    setAppointmentType(selectedType.name, selectedType.id, selectedType.duration_minutes);
    setUrgency(localUrgency);
    setClientNotes(notes);
    router.push(`/book/${params.slug}/slot`);
  };

  return (
    <div>
      <ProgressBar step={3} total={4} />
      <PageTitle
        title="What type of visit?"
        subtitle={`For ${selectedPet.name} · ${selectedPet.breed || selectedPet.species}`}
      />

      {/* Emergency alert */}
      {localUrgency === 'emergency' && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: '10px', padding: '14px 16px', marginBottom: '16px',
          display: 'flex', alignItems: 'flex-start', gap: '10px',
        }}>
          <span style={{ fontSize: '1.2rem' }}>🚨</span>
          <div>
            <p style={{ margin: '0 0 4px', fontWeight: 700, color: '#fca5a5', fontSize: '0.88rem' }}>
              Pet Emergency — Call Immediately
            </p>
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#fca5a5' }}>
              For emergencies, please call us directly rather than booking online.
            </p>
            {clinicPhone && (
              <a href={`tel:${clinicPhone}`} style={{
                display: 'block', marginTop: '6px', color: '#f87171',
                fontWeight: 700, fontSize: '1rem', textDecoration: 'none',
              }}>{clinicPhone}</a>
            )}
          </div>
        </div>
      )}

      {/* Appointment types */}
      {loading ? (
        <LoadingSpinner />
      ) : types.length === 0 && !error ? (
        <BookingCard style={{ marginBottom: '16px' }}>
          <p style={{ color: '#71717a', textAlign: 'center', margin: 0 }}>
            No appointment types are currently available for online booking. Please call us.
          </p>
          {clinicPhone && (
            <a href={`tel:${clinicPhone}`} style={{
              display: 'block', marginTop: '10px', textAlign: 'center',
              color: '#a5b4fc', fontWeight: 700, textDecoration: 'none',
            }}>{clinicPhone}</a>
          )}
        </BookingCard>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
          {types.map(t => {
            const selected = selectedType?.id === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => { setSelectedType(t); setError(null); }}
                style={{
                  width: '100%', textAlign: 'left', padding: '16px',
                  background: selected ? 'rgba(99,102,241,0.12)' : 'rgba(24,24,27,0.6)',
                  border: `1px solid ${selected ? 'rgba(99,102,241,0.5)' : 'rgba(63,63,70,0.4)'}`,
                  borderRadius: '12px', cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'all 0.2s ease', minHeight: '68px',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px',
                }}
              >
                <div>
                  <p style={{ margin: 0, fontWeight: 700, fontSize: '0.95rem', color: '#e4e4e7' }}>{t.name}</p>
                  <p style={{ margin: '3px 0 0', fontSize: '0.72rem', color: '#71717a' }}>
                    {t.duration_minutes} min
                    {t.description ? ` · ${t.description}` : ''}
                  </p>
                </div>
                {selected && <span style={{ color: '#a5b4fc', fontSize: '1.2rem', flexShrink: 0 }}>✓</span>}
              </button>
            );
          })}
        </div>
      )}

      {/* Urgency selector */}
      <BookingCard style={{ marginBottom: '14px' }}>
        <p style={{ margin: '0 0 12px', fontSize: '0.82rem', fontWeight: 600, color: '#e4e4e7' }}>
          How urgent is this visit?
        </p>
        <UrgencySelector value={localUrgency} onChange={setLocalUrgency} />
      </BookingCard>

      {/* Notes */}
      <BookingCard style={{ marginBottom: '14px' }}>
        <label
          htmlFor="notes"
          style={{ display: 'block', fontSize: '0.78rem', color: '#71717a', marginBottom: '8px', fontWeight: 500 }}
        >
          Notes for the vet (optional)
        </label>
        <textarea
          id="notes"
          value={notes}
          onChange={e => setNotes(e.target.value.slice(0, 300))}
          placeholder="Describe symptoms, concerns, or anything the vet should know…"
          maxLength={300}
          rows={3}
          style={{
            width: '100%', boxSizing: 'border-box',
            background: 'rgba(39,39,42,0.6)',
            border: '1px solid rgba(63,63,70,0.5)',
            borderRadius: '8px', padding: '11px 14px',
            color: '#e4e4e7', fontSize: '0.85rem',
            outline: 'none', fontFamily: 'inherit',
            resize: 'vertical', minHeight: '80px',
          }}
        />
        <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: '#52525b', textAlign: 'right' }}>
          {notes.length}/300
        </p>
      </BookingCard>

      <InlineError message={error} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
        <PrimaryButton onClick={handleContinue} disabled={!selectedType || localUrgency === 'emergency'}>
          {localUrgency === 'emergency' ? 'Please call for emergencies' : 'See Available Times →'}
        </PrimaryButton>
        <SecondaryButton onClick={() => router.push(`/book/${params.slug}/pet`)}>
          ← Back
        </SecondaryButton>
      </div>
    </div>
  );
}
