'use client';
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking } from '../../BookingContext';
import {
  ProgressBar, PageTitle, BookingCard, PrimaryButton, SecondaryButton,
  InlineError, PetCard, LoadingSpinner,
} from '../../components';

export default function PetSelectionPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const { pets, selectedPet, ownerName, ownerId, setSelectedPet } = useBooking();

  const [localSelected, setLocalSelected] = useState(selectedPet);
  const [showAddMessage, setShowAddMessage] = useState(false);

  // Guard: if no owner in context, redirect back
  useEffect(() => {
    if (!ownerId) {
      router.replace(`/book/${params.slug}/identify`);
    }
  }, [ownerId, params.slug, router]);

  if (!ownerId) return <LoadingSpinner />;

  const handleContinue = () => {
    if (!localSelected) return;
    setSelectedPet(localSelected);
    router.push(`/book/${params.slug}/type`);
  };

  return (
    <div>
      <ProgressBar step={2} total={4} />
      <PageTitle
        title={ownerName ? `Hi, ${ownerName}!` : 'Select a pet'}
        subtitle="Which pet is this appointment for?"
      />

      {pets.length === 0 ? (
        <BookingCard>
          <p style={{ color: '#71717a', textAlign: 'center', margin: 0 }}>
            No pets on file. Please call the clinic to add your pet.
          </p>
        </BookingCard>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
          {pets.map(pet => (
            <PetCard
              key={pet.id}
              pet={pet}
              selected={localSelected?.id === pet.id}
              onClick={() => setLocalSelected(pet)}
            />
          ))}
        </div>
      )}

      {/* Add a different pet */}
      <BookingCard style={{ marginBottom: '16px', borderStyle: 'dashed' }}>
        <button
          type="button"
          onClick={() => setShowAddMessage(!showAddMessage)}
          style={{
            width: '100%', background: 'transparent', border: 'none',
            color: '#71717a', cursor: 'pointer', fontFamily: 'inherit',
            fontSize: '0.82rem', textAlign: 'left', padding: 0,
            display: 'flex', alignItems: 'center', gap: '8px',
          }}
        >
          <span style={{ fontSize: '1.2rem' }}>➕</span>
          Add a different pet or new patient
        </button>
        {showAddMessage && (
          <div style={{
            marginTop: '12px', padding: '12px', borderRadius: '8px',
            background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
          }}>
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#a5b4fc' }}>
              To add a new pet to your account, please call us directly. Our team will add your pet
              before your appointment.
            </p>
          </div>
        )}
      </BookingCard>

      <InlineError message={!localSelected && pets.length > 0 ? null : null} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <PrimaryButton
          onClick={handleContinue}
          disabled={!localSelected}
        >
          Continue with {localSelected?.name || '…'} →
        </PrimaryButton>
        <SecondaryButton onClick={() => router.push(`/book/${params.slug}/identify`)}>
          ← Back
        </SecondaryButton>
      </div>
    </div>
  );
}
