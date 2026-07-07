'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import './welcome.css';

const DEMO_TEXT = [
  "I'm Vera, your Chief of Staff.",
  "Not a veterinarian. Not your attorney.",
  "I run the practice so your DVMs can focus on medicine.",
  "Let me show you.",
];

export default function WelcomePage() {
  const router = useRouter();
  const [lineIdx, setLineIdx] = useState(0);
  const [displayed, setDisplayed] = useState('');
  const [charIdx, setCharIdx] = useState(0);
  const [done, setDone] = useState(false);

  // Typewriter effect
  useEffect(() => {
    if (done) return;
    const line = DEMO_TEXT[lineIdx] ?? '';
    if (charIdx < line.length) {
      const t = setTimeout(() => {
        setDisplayed((prev) => prev + line[charIdx]);
        setCharIdx((c) => c + 1);
      }, 30);
      return () => clearTimeout(t);
    } else {
      // Pause before next line
      if (lineIdx < DEMO_TEXT.length - 1) {
        const t = setTimeout(() => {
          setLineIdx((l) => l + 1);
          setDisplayed('');
          setCharIdx(0);
        }, 1200);
        return () => clearTimeout(t);
      } else {
        setDone(true);
      }
    }
  }, [charIdx, lineIdx, done]);

  const handleStart = async () => {
    try {
      const res = await fetch('/api/onboarding/session/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.session_id) {
        // Store session_id in sessionStorage for client-side access
        sessionStorage.setItem('onboarding_session_id', data.session_id);
        sessionStorage.setItem('onboarding_session_token', data.session_token);
        router.push('/onboarding');
      }
    } catch {
      // If API down, still navigate (session will be created on first load)
      router.push('/onboarding');
    }
  };

  const skipTypewriter = () => {
    setDisplayed(DEMO_TEXT[DEMO_TEXT.length - 1]);
    setLineIdx(DEMO_TEXT.length - 1);
    setCharIdx(DEMO_TEXT[DEMO_TEXT.length - 1].length);
    setDone(true);
  };

  const lineLabel = DEMO_TEXT[lineIdx] ?? '';

  return (
    <div className="welcome-page" onClick={!done ? skipTypewriter : undefined}>
      <div className="welcome-vera-avatar">V</div>

      <h1 className="welcome-title">
        {done ? DEMO_TEXT[DEMO_TEXT.length - 1] : (
          <>
            {displayed}
            <span className="vera-cursor" aria-hidden="true" />
          </>
        )}
      </h1>

      {done && (
        <p className="welcome-intro">
          In 90 seconds, your Harmony demo becomes your real practice.
          Two questions. Your data. Your call.
        </p>
      )}

      {done && (
        <div className="welcome-actions">
          <button className="btn-primary" onClick={handleStart}>
            Start setup →
          </button>
          <button
            className="btn-ghost"
            onClick={() => router.push('/onboarding?demo=true')}
          >
            Just show me the demo first
          </button>
        </div>
      )}

      {!done && (
        <p style={{ fontSize: '0.78rem', color: '#55557a', marginTop: '2rem' }}>
          Click anywhere to skip
        </p>
      )}
    </div>
  );
}
