'use client';
import React, { createContext, useContext, useState, ReactNode } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export { API };

interface Pet {
  id: string;
  name: string;
  species: string;
  breed: string;
  dob?: string;
}

interface BookingState {
  clinicSlug: string;
  clinicName: string;
  clinicPhone: string;
  emergencyPhone: string;
  onlineBookingEnabled: boolean;
  cancellationPolicy: string;
  ownerId: string | null;
  ownerName: string;
  pets: Pet[];
  selectedPet: Pet | null;
  appointmentType: string;
  appointmentTypeSlug: string;
  durationMin: number;
  urgency: 'wellness' | 'routine' | 'urgent' | 'emergency';
  clientNotes: string;
  selectedSlot: {
    slotId: string;
    resourceId: string;
    resourceName: string;
    startDatetime: string;
    endDatetime: string;
  } | null;
  holdId: string | null;
  holdExpiresAt: string | null;
  smsConsent: boolean;
  sessionToken: string;
}

interface BookingContextType extends BookingState {
  setClinic: (data: Partial<BookingState>) => void;
  setOwner: (ownerId: string, name: string, pets: Pet[]) => void;
  setSelectedPet: (pet: Pet) => void;
  setAppointmentType: (name: string, slug: string, duration: number) => void;
  setUrgency: (urgency: BookingState['urgency']) => void;
  setClientNotes: (notes: string) => void;
  setSelectedSlot: (slot: BookingState['selectedSlot']) => void;
  setHold: (holdId: string, expiresAt: string) => void;
  setSmsConsent: (consent: boolean) => void;
  resetBooking: () => void;
}

const defaultState: BookingState = {
  clinicSlug: '',
  clinicName: '',
  clinicPhone: '',
  emergencyPhone: '',
  onlineBookingEnabled: true,
  cancellationPolicy: '',
  ownerId: null,
  ownerName: '',
  pets: [],
  selectedPet: null,
  appointmentType: '',
  appointmentTypeSlug: '',
  durationMin: 30,
  urgency: 'routine',
  clientNotes: '',
  selectedSlot: null,
  holdId: null,
  holdExpiresAt: null,
  smsConsent: false,
  sessionToken: typeof crypto !== 'undefined' ? crypto.randomUUID() : Math.random().toString(36),
};

const BookingContext = createContext<BookingContextType>({
  ...defaultState,
  setClinic: () => {},
  setOwner: () => {},
  setSelectedPet: () => {},
  setAppointmentType: () => {},
  setUrgency: () => {},
  setClientNotes: () => {},
  setSelectedSlot: () => {},
  setHold: () => {},
  setSmsConsent: () => {},
  resetBooking: () => {},
});

export function BookingProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<BookingState>(defaultState);

  const setClinic = (data: Partial<BookingState>) =>
    setState(s => ({ ...s, ...data }));
  const setOwner = (ownerId: string, name: string, pets: Pet[]) =>
    setState(s => ({ ...s, ownerId, ownerName: name, pets }));
  const setSelectedPet = (pet: Pet) =>
    setState(s => ({ ...s, selectedPet: pet }));
  const setAppointmentType = (name: string, slug: string, duration: number) =>
    setState(s => ({ ...s, appointmentType: name, appointmentTypeSlug: slug, durationMin: duration }));
  const setUrgency = (urgency: BookingState['urgency']) =>
    setState(s => ({ ...s, urgency }));
  const setClientNotes = (clientNotes: string) =>
    setState(s => ({ ...s, clientNotes }));
  const setSelectedSlot = (selectedSlot: BookingState['selectedSlot']) =>
    setState(s => ({ ...s, selectedSlot }));
  const setHold = (holdId: string, holdExpiresAt: string) =>
    setState(s => ({ ...s, holdId, holdExpiresAt }));
  const setSmsConsent = (smsConsent: boolean) =>
    setState(s => ({ ...s, smsConsent }));
  const resetBooking = () => setState(defaultState);

  return (
    <BookingContext.Provider value={{
      ...state, setClinic, setOwner, setSelectedPet, setAppointmentType,
      setUrgency, setClientNotes, setSelectedSlot, setHold, setSmsConsent, resetBooking,
    }}>
      {children}
    </BookingContext.Provider>
  );
}

export function useBooking() {
  return useContext(BookingContext);
}
