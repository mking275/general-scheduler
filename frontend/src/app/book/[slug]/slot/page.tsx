'use client';
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking, API } from '../../BookingContext';
import {
  ProgressBar, PageTitle, BookingCard, SecondaryButton,
  InlineError, LoadingSpinner, SlotCard, Toast, SlotType,
} from '../../components';


interface AvailabilityResponse {
  slots: SlotType[];
  total_available: number;
  showing_top: number;
  has_more: boolean;
  waitlist_available: boolean;
}

export default function SlotSelectionPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const {
    ownerId, selectedPet, appointmentType, appointmentTypeSlug,
    urgency, clinicSlug, setSelectedSlot, setHold,
  } = useBooking();

  const [data, setData] = useState<AvailabilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [bookingSlotId, setBookingSlotId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Guard
  useEffect(() => {
    if (!ownerId || !selectedPet || !appointmentTypeSlug) {
      router.replace(`/book/${params.slug}/identify`);
    }
  }, [ownerId, selectedPet, appointmentTypeSlug, params.slug, router]);

  const fetchSlots = useCallback(async () => {
    if (!appointmentTypeSlug) return;
    setLoading(true);
    setError(null);
    try {
      const url = new URL(`${API}/public/clinics/${params.slug}/availability`);
      url.searchParams.set('appointment_type_id', appointmentTypeSlug);
      url.searchParams.set('urgency', urgency);
      const res = await fetch(url.toString());
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Failed to load available times.');
      }
      const json: AvailabilityResponse = await res.json();
      setData(json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load slots.');
    } finally {
      setLoading(false);
    }
  }, [appointmentTypeSlug, params.slug, urgency]);

  useEffect(() => { fetchSlots(); }, [fetchSlots]);

  const handleBook = async (slot: SlotType) => {
    setBookingSlotId(slot.slot_id);
    setError(null);
    try {
      const res = await fetch(`${API}/public/bookings/hold`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          clinic_slug: params.slug,
          slot_id: slot.slot_id,
          resource_id: slot.resource_id,
          start_datetime: slot.start_datetime,
          end_datetime: slot.end_datetime,
        }),
      });

      if (res.status === 409) {
        setToast('That slot was just taken. Refreshing available times…');
        setTimeout(() => setToast(null), 4000);
        await fetchSlots();
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Failed to hold slot.');
      }

      const holdData = await res.json();
      setSelectedSlot({
        slotId: slot.slot_id,
        resourceId: slot.resource_id || '',
        resourceName: slot.vet_display_name || slot.vet_name || slot.resource_name || '',
        startDatetime: slot.start_datetime,
        endDatetime: slot.end_datetime,
      });
      setHold(holdData.hold_id, holdData.expires_at);
      router.push(`/book/${params.slug}/confirm`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to hold slot.');
    } finally {
      setBookingSlotId(null);
    }
  };

  if (!ownerId || !selectedPet || !appointmentTypeSlug) return <LoadingSpinner />;

  return (
    <div>
      <Toast message={toast} />
      <ProgressBar step={4} total={4} />
      <PageTitle
        title="Pick a time"
        subtitle={`${appointmentType} · ${selectedPet?.name}`}
      />

      {loading ? (
        <div>
          <LoadingSpinner />
          <p style={{ textAlign: 'center', color: '#52525b', fontSize: '0.78rem' }}>
            Finding available slots…
          </p>
        </div>
      ) : error ? (
        <BookingCard>
          <InlineError message={error} />
          <button
            onClick={fetchSlots}
            style={{
              marginTop: '12px', background: 'rgba(99,102,241,0.15)',
              border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px',
              padding: '10px 16px', color: '#a5b4fc', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '0.82rem', width: '100%', minHeight: '44px',
            }}
          >
            Try Again
          </button>
        </BookingCard>
      ) : !data || data.slots.length === 0 ? (
        <BookingCard style={{ marginBottom: '14px' }}>
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📅</div>
            <p style={{ margin: '0 0 8px', fontWeight: 600, color: '#e4e4e7' }}>No slots available</p>
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#71717a' }}>
              There are no available times for this appointment type in the next 30 days.
              Please call us or check back later.
            </p>
          </div>
          {data?.waitlist_available && (
            <div style={{
              marginTop: '16px', padding: '12px', borderRadius: '8px',
              background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
            }}>
              <p style={{ margin: '0 0 6px', fontSize: '0.82rem', color: '#a5b4fc', fontWeight: 600 }}>
                Join the waitlist
              </p>
              <p style={{ margin: 0, fontSize: '0.75rem', color: '#71717a' }}>
                We'll notify you as soon as a slot opens up.
              </p>
            </div>
          )}
        </BookingCard>
      ) : (
        <>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: '12px',
          }}>
            <p style={{ margin: 0, fontSize: '0.75rem', color: '#71717a' }}>
              {data.total_available} slot{data.total_available !== 1 ? 's' : ''} available
              {data.has_more ? ` · showing first ${data.showing_top}` : ''}
            </p>
            <button
              onClick={fetchSlots}
              style={{
                background: 'transparent', border: 'none', color: '#6366f1',
                cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.75rem', padding: '4px 8px',
              }}
            >
              ↻ Refresh
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
            {data.slots.map(slot => (
              <SlotCard
                key={slot.slot_id}
                slot={slot}
                onBook={handleBook}
                loading={bookingSlotId === slot.slot_id}
              />
            ))}
          </div>

          {data.has_more && (
            <p style={{ textAlign: 'center', fontSize: '0.75rem', color: '#52525b', marginBottom: '16px' }}>
              More slots available — call us or check back to see additional times.
            </p>
          )}

          <InlineError message={error} />
        </>
      )}

      <SecondaryButton onClick={() => router.push(`/book/${params.slug}/type`)}>
        ← Back to appointment type
      </SecondaryButton>
    </div>
  );
}
