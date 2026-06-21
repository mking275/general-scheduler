'use client';
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { API } from '../../BookingContext';
import { BookingCard, PrimaryButton, LoadingSpinner, InlineError } from '../../components';

interface IntakeQuestion {
  id: string;
  text: string;
  type: 'text' | 'choice' | 'yes_no' | 'scale';
  options?: string[];
  required: boolean;
}

interface IntakeData {
  intake_token_id: string;
  status: string;
  already_submitted: boolean;
  patient_name: string;
  appointment_type: string;
  clinic_name: string;
  questions: IntakeQuestion[];
  completed_at?: string;
}

export default function IntakePage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();

  const [intake, setIntake] = useState<IntakeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!params.token) return;
    setLoading(true);
    fetch(`${API}/public/intake/${params.token}`)
      .then(async res => {
        if (res.status === 404) throw new Error('Intake form not found. The link may have expired.');
        if (!res.ok) throw new Error('Failed to load intake form.');
        return res.json();
      })
      .then((data: IntakeData) => {
        setIntake(data);
        if (data.already_submitted || data.status === 'complete') {
          setDone(true);
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.token]);

  const handleAnswer = (questionId: string, answer: string) => {
    setAnswers(a => ({ ...a, [questionId]: answer }));
  };

  const handleSubmit = async () => {
    if (!intake) return;
    setSubmitting(true);
    setError(null);
    try {
      const responses = intake.questions.map(q => ({
        question_id: q.id,
        question_text: q.text,
        answer: answers[q.id] || '',
        skipped: !answers[q.id],
      }));

      const res = await fetch(`${API}/public/intake/${params.token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses }),
      });

      if (res.status === 409) {
        setDone(true);
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Submission failed. Please try again.');
      }
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  // Already submitted / completion screen
  if (done || !intake) {
    return (
      <div style={{ paddingTop: '24px', textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>🎉</div>
        <h1 style={{ margin: '0 0 8px', fontSize: '1.4rem', fontWeight: 800, color: '#f4f4f5' }}>
          Thank you!
        </h1>
        <p style={{ margin: '0 0 24px', fontSize: '0.85rem', color: '#71717a' }}>
          {intake?.already_submitted
            ? 'Your pre-visit check-in was already submitted.'
            : 'Your pre-visit check-in is complete. The vet team will review your responses before the appointment.'}
        </p>
        {intake && (
          <BookingCard style={{ textAlign: 'left', marginBottom: '20px' }}>
            <p style={{ margin: '0 0 6px', fontSize: '0.75rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              For your appointment
            </p>
            <p style={{ margin: 0, fontWeight: 700, color: '#e4e4e7' }}>{intake.patient_name}</p>
            <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#71717a' }}>
              {intake.appointment_type} · {intake.clinic_name}
            </p>
          </BookingCard>
        )}
        <p style={{ margin: 0, fontSize: '0.75rem', color: '#52525b' }}>
          You can close this page. We'll see you at your appointment!
        </p>
      </div>
    );
  }

  // Error state
  if (error && !intake) {
    return (
      <div style={{ paddingTop: '24px' }}>
        <BookingCard>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>⚠️</div>
            <InlineError message={error} />
          </div>
        </BookingCard>
      </div>
    );
  }

  const questions = intake.questions || [];
  const totalQ = questions.length;
  const question = questions[currentQ];
  const isLast = currentQ === totalQ - 1;
  const currentAnswer = question ? answers[question.id] || '' : '';

  if (totalQ === 0) {
    return (
      <div style={{ paddingTop: '24px', textAlign: 'center' }}>
        <BookingCard>
          <p style={{ color: '#71717a', margin: 0 }}>No intake questions configured for this appointment type.</p>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              marginTop: '16px', padding: '12px 24px', borderRadius: '8px', border: 'none',
              background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
              color: '#fff', fontWeight: 700, cursor: submitting ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit', fontSize: '0.88rem', minHeight: '44px',
            }}
          >
            {submitting ? 'Submitting…' : 'Complete Check-In'}
          </button>
        </BookingCard>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: '8px' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.68rem', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Pre-Visit Check-In
          </span>
          <span style={{ fontSize: '0.68rem', color: '#52525b' }}>·</span>
          <span style={{ fontSize: '0.68rem', color: '#52525b' }}>{intake.patient_name}</span>
        </div>
        <h1 style={{ margin: '0 0 4px', fontSize: '1.2rem', fontWeight: 700, color: '#f4f4f5' }}>
          {intake.appointment_type}
        </h1>
        <p style={{ margin: 0, fontSize: '0.78rem', color: '#71717a' }}>{intake.clinic_name}</p>
      </div>

      {/* Progress */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
          {questions.map((_, i) => (
            <div
              key={i}
              style={{
                flex: 1, height: '4px', borderRadius: '2px',
                background: i <= currentQ
                  ? 'linear-gradient(90deg, #6366f1, #8b5cf6)'
                  : 'rgba(63,63,70,0.4)',
                transition: 'all 0.3s ease',
              }}
            />
          ))}
        </div>
        <p style={{ margin: 0, fontSize: '0.7rem', color: '#71717a' }}>
          Question {currentQ + 1} of {totalQ}
        </p>
      </div>

      {/* Question card */}
      {question && (
        <BookingCard style={{ marginBottom: '16px' }}>
          <p style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 600, color: '#f4f4f5', lineHeight: 1.4 }}>
            {question.text}
            {question.required && <span style={{ color: '#ef4444', marginLeft: '4px' }}>*</span>}
          </p>

          {question.type === 'yes_no' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {['Yes', 'No'].map(opt => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => handleAnswer(question.id, opt)}
                  style={{
                    padding: '14px', borderRadius: '10px',
                    border: `1px solid ${currentAnswer === opt ? 'rgba(99,102,241,0.5)' : 'rgba(63,63,70,0.4)'}`,
                    background: currentAnswer === opt ? 'rgba(99,102,241,0.15)' : 'transparent',
                    color: currentAnswer === opt ? '#a5b4fc' : '#71717a',
                    fontWeight: currentAnswer === opt ? 700 : 400,
                    cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.95rem',
                    minHeight: '52px', transition: 'all 0.2s ease',
                  }}
                >
                  {opt === 'Yes' ? '✓ Yes' : '✗ No'}
                </button>
              ))}
            </div>
          )}

          {question.type === 'choice' && question.options && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {question.options.map(opt => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => handleAnswer(question.id, opt)}
                  style={{
                    padding: '12px 16px', borderRadius: '10px', textAlign: 'left',
                    border: `1px solid ${currentAnswer === opt ? 'rgba(99,102,241,0.5)' : 'rgba(63,63,70,0.4)'}`,
                    background: currentAnswer === opt ? 'rgba(99,102,241,0.12)' : 'transparent',
                    color: currentAnswer === opt ? '#a5b4fc' : '#a1a1aa',
                    cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.88rem',
                    minHeight: '48px', transition: 'all 0.2s ease',
                    display: 'flex', alignItems: 'center', gap: '10px',
                  }}
                >
                  <span style={{
                    width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                    border: `2px solid ${currentAnswer === opt ? '#6366f1' : 'rgba(63,63,70,0.5)'}`,
                    background: currentAnswer === opt ? '#6366f1' : 'transparent',
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.6rem', color: '#fff',
                  }}>
                    {currentAnswer === opt ? '✓' : ''}
                  </span>
                  {opt}
                </button>
              ))}
            </div>
          )}

          {question.type === 'scale' && (
            <div>
              <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => handleAnswer(question.id, String(n))}
                    style={{
                      flex: 1, padding: '10px 0', borderRadius: '6px', border: 'none',
                      background: currentAnswer === String(n) ? '#6366f1' : 'rgba(63,63,70,0.3)',
                      color: currentAnswer === String(n) ? '#fff' : '#71717a',
                      fontWeight: currentAnswer === String(n) ? 700 : 400,
                      cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.82rem',
                      minHeight: '44px', transition: 'all 0.2s ease',
                    }}
                  >{n}</button>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#52525b' }}>
                <span>Not at all</span><span>Extremely</span>
              </div>
            </div>
          )}

          {question.type === 'text' && (
            <textarea
              value={currentAnswer}
              onChange={e => handleAnswer(question.id, e.target.value)}
              placeholder="Type your answer here…"
              rows={4}
              style={{
                width: '100%', boxSizing: 'border-box',
                background: 'rgba(39,39,42,0.6)',
                border: '1px solid rgba(63,63,70,0.5)',
                borderRadius: '8px', padding: '11px 14px',
                color: '#e4e4e7', fontSize: '0.88rem',
                outline: 'none', fontFamily: 'inherit',
                resize: 'vertical', minHeight: '100px',
              }}
            />
          )}
        </BookingCard>
      )}

      <InlineError message={error} />

      {/* Navigation */}
      <div style={{ display: 'flex', gap: '10px' }}>
        {currentQ > 0 && (
          <button
            type="button"
            onClick={() => setCurrentQ(q => q - 1)}
            style={{
              flex: 1, padding: '12px', borderRadius: '10px',
              background: 'transparent',
              border: '1px solid rgba(63,63,70,0.5)',
              color: '#71717a', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '0.88rem',
              minHeight: '48px',
            }}
          >
            ← Previous
          </button>
        )}

        {isLast ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || (question?.required && !currentAnswer)}
            style={{
              flex: 2, padding: '12px', borderRadius: '10px', border: 'none',
              background: submitting || (question?.required && !currentAnswer)
                ? 'rgba(99,102,241,0.2)'
                : 'linear-gradient(135deg, #6366f1, #7c3aed)',
              color: submitting || (question?.required && !currentAnswer) ? '#6366f1' : '#fff',
              fontWeight: 700, cursor: submitting ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit', fontSize: '0.92rem',
              minHeight: '48px', transition: 'all 0.2s ease',
            }}
          >
            {submitting ? 'Submitting…' : 'Submit Check-In ✓'}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setCurrentQ(q => q + 1)}
            disabled={question?.required && !currentAnswer}
            style={{
              flex: 2, padding: '12px', borderRadius: '10px', border: 'none',
              background: question?.required && !currentAnswer
                ? 'rgba(99,102,241,0.2)'
                : 'linear-gradient(135deg, #6366f1, #7c3aed)',
              color: question?.required && !currentAnswer ? '#6366f1' : '#fff',
              fontWeight: 700,
              cursor: question?.required && !currentAnswer ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit', fontSize: '0.92rem',
              minHeight: '48px', transition: 'all 0.2s ease',
            }}
          >
            Next →
          </button>
        )}
      </div>

      {/* Skip option for optional questions */}
      {question && !question.required && (
        <div style={{ textAlign: 'center', marginTop: '12px' }}>
          <button
            type="button"
            onClick={() => {
              handleAnswer(question.id, '');
              if (isLast) handleSubmit();
              else setCurrentQ(q => q + 1);
            }}
            style={{
              background: 'transparent', border: 'none', color: '#52525b',
              cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.75rem',
              textDecoration: 'underline', padding: '8px',
            }}
          >
            Skip this question
          </button>
        </div>
      )}
    </div>
  );
}
