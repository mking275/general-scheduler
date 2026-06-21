'use client';
import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBooking, API } from '../../BookingContext';
import {
  ProgressBar, PageTitle, BookingCard, PrimaryButton, SecondaryButton,
  InlineError, InputField,
} from '../../components';

export default function IdentifyPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const { setOwner, clinicName } = useBooking();

  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Registration form state
  const [mode, setMode] = useState<'lookup' | 'register'>('lookup');
  const [notFound, setNotFound] = useState(false);
  const [regForm, setRegForm] = useState({
    first_name: '', last_name: '', phone: '', email: '',
    pet_name: '', pet_species: 'dog', pet_breed: '', pet_dob: '',
    sms_consent: false,
  });
  const [clinicId, setClinicId] = useState<string | null>(null);

  const handleLookup = async () => {
    if (!phone.trim() && !email.trim()) {
      setError('Please enter your phone number or email address.');
      return;
    }
    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      // First get clinic_id from slug
      const clinicRes = await fetch(`${API}/public/clinics/${params.slug}`);
      if (!clinicRes.ok) throw new Error('Clinic not found.');
      const clinicData = await clinicRes.json();
      const cId = clinicData.clinic_id;
      setClinicId(cId);

      const res = await fetch(`${API}/public/owners/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ clinic_id: cId, phone: phone.trim(), email: email.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Lookup failed. Please try again.');
      }

      const data = await res.json();
      if (data.found) {
        setOwner(data.owner_id, data.display_name, data.pets || []);
        router.push(`/book/${params.slug}/pet`);
      } else {
        setNotFound(true);
        // Pre-fill phone/email into reg form
        setRegForm(f => ({ ...f, phone: phone.trim(), email: email.trim() }));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!regForm.first_name || !regForm.last_name || !regForm.phone || !regForm.pet_name) {
      setError('Please fill in all required fields.');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      // Get clinic_id if we don't have it yet
      let cId = clinicId;
      if (!cId) {
        const clinicRes = await fetch(`${API}/public/clinics/${params.slug}`);
        if (!clinicRes.ok) throw new Error('Clinic not found.');
        const clinicData = await clinicRes.json();
        cId = clinicData.clinic_id;
        setClinicId(cId);
      }

      const res = await fetch(`${API}/public/owners/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          clinic_id: cId,
          first_name: regForm.first_name.trim(),
          last_name: regForm.last_name.trim(),
          phone: regForm.phone.trim(),
          email: regForm.email.trim(),
          sms_consent: regForm.sms_consent,
          pet: {
            name: regForm.pet_name.trim(),
            species: regForm.pet_species,
            breed: regForm.pet_breed.trim(),
            dob_approx: regForm.pet_dob || undefined,
          },
        }),
      });

      if (res.status === 409) {
        const data = await res.json();
        setError(data.detail || 'An account already exists. Please use the returning client flow above.');
        setMode('lookup');
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Registration failed.');
      }

      const data = await res.json();
      setOwner(
        data.owner_id,
        `${regForm.first_name} ${regForm.last_name}`,
        [{
          id: data.patient_id,
          name: regForm.pet_name,
          species: regForm.pet_species,
          breed: regForm.pet_breed,
        }],
      );
      router.push(`/book/${params.slug}/pet`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', boxSizing: 'border-box',
    background: 'rgba(39,39,42,0.6)',
    border: '1px solid rgba(63,63,70,0.5)',
    borderRadius: '8px', padding: '11px 14px',
    color: '#e4e4e7', fontSize: '0.88rem',
    outline: 'none', fontFamily: 'inherit',
    minHeight: '44px',
  };

  if (mode === 'register') {
    return (
      <div>
        <ProgressBar step={1} total={4} />
        <PageTitle title="Create your account" subtitle="New client? We'll get you set up quickly." />

        <BookingCard style={{ marginBottom: '14px' }}>
          <p style={{ margin: '0 0 16px', fontSize: '0.82rem', fontWeight: 600, color: '#a5b4fc' }}>Your information</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <InputField label="First name" id="reg-first" value={regForm.first_name}
              onChange={v => setRegForm(f => ({ ...f, first_name: v }))} required />
            <InputField label="Last name" id="reg-last" value={regForm.last_name}
              onChange={v => setRegForm(f => ({ ...f, last_name: v }))} required />
          </div>
          <InputField label="Phone number" id="reg-phone" type="tel" value={regForm.phone}
            onChange={v => setRegForm(f => ({ ...f, phone: v }))}
            placeholder="(555) 123-4567" required />
          <InputField label="Email address" id="reg-email" type="email" value={regForm.email}
            onChange={v => setRegForm(f => ({ ...f, email: v }))} placeholder="you@example.com" />

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginTop: '4px', marginBottom: '4px' }}>
            <input
              type="checkbox"
              checked={regForm.sms_consent}
              onChange={e => setRegForm(f => ({ ...f, sms_consent: e.target.checked }))}
              style={{ width: '18px', height: '18px', accentColor: '#6366f1' }}
            />
            <span style={{ fontSize: '0.75rem', color: '#71717a' }}>
              I consent to receive appointment reminders via SMS
            </span>
          </label>
        </BookingCard>

        <BookingCard style={{ marginBottom: '14px' }}>
          <p style={{ margin: '0 0 16px', fontSize: '0.82rem', fontWeight: 600, color: '#a5b4fc' }}>About your pet</p>
          <InputField label="Pet's name" id="reg-pet-name" value={regForm.pet_name}
            onChange={v => setRegForm(f => ({ ...f, pet_name: v }))} required />
          <div style={{ marginBottom: '14px' }}>
            <label htmlFor="reg-species" style={{ display: 'block', fontSize: '0.72rem', color: '#71717a', marginBottom: '5px' }}>
              Species <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <select
              id="reg-species"
              value={regForm.pet_species}
              onChange={e => setRegForm(f => ({ ...f, pet_species: e.target.value }))}
              style={{ ...inputStyle, appearance: 'none', backgroundImage: 'none' }}
            >
              {['dog', 'cat', 'bird', 'rabbit', 'reptile', 'other'].map(s => (
                <option key={s} value={s} style={{ background: '#18181b' }}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <InputField label="Breed (optional)" id="reg-breed" value={regForm.pet_breed}
            onChange={v => setRegForm(f => ({ ...f, pet_breed: v }))} />
          <InputField label="Date of birth (approx.)" id="reg-dob" type="date" value={regForm.pet_dob}
            onChange={v => setRegForm(f => ({ ...f, pet_dob: v }))} />
        </BookingCard>

        <InlineError message={error} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '14px' }}>
          <PrimaryButton onClick={handleRegister} loading={loading}>
            Create Account & Continue →
          </PrimaryButton>
          <SecondaryButton onClick={() => { setMode('lookup'); setError(null); }}>
            ← Back to returning client
          </SecondaryButton>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProgressBar step={1} total={4} />
      <PageTitle
        title="Welcome back"
        subtitle={clinicName ? `Let's find your account at ${clinicName}` : "Let's find your account"}
      />

      <BookingCard style={{ marginBottom: '14px' }}>
        <p style={{ margin: '0 0 16px', fontSize: '0.82rem', color: '#71717a' }}>
          Enter your phone number or email address to look up your account.
        </p>
        <InputField
          label="Phone number"
          id="phone"
          type="tel"
          value={phone}
          onChange={setPhone}
          placeholder="(555) 123-4567"
        />
        <div style={{ textAlign: 'center', color: '#52525b', fontSize: '0.75rem', margin: '4px 0' }}>or</div>
        <InputField
          label="Email address"
          id="email"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="you@example.com"
        />
        <InlineError message={error} />
      </BookingCard>

      {notFound && (
        <BookingCard style={{ marginBottom: '14px', borderColor: 'rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.05)' }}>
          <p style={{ margin: '0 0 12px', fontSize: '0.85rem', fontWeight: 600, color: '#fbbf24' }}>
            No account found
          </p>
          <p style={{ margin: '0 0 14px', fontSize: '0.78rem', color: '#71717a' }}>
            We couldn't find an account matching that phone/email. You can create a new client account to continue.
          </p>
          <PrimaryButton onClick={() => { setMode('register'); setError(null); }}>
            New Client? Register Here →
          </PrimaryButton>
        </BookingCard>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <PrimaryButton onClick={handleLookup} loading={loading} disabled={!phone.trim() && !email.trim()}>
          Find My Account →
        </PrimaryButton>
        <SecondaryButton onClick={() => router.push(`/book/${params.slug}`)}>
          ← Back to clinic page
        </SecondaryButton>
      </div>
    </div>
  );
}
