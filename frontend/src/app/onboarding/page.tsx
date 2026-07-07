'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import VerboseLogPanel from '@/components/VerboseLogPanel';
import '../onboarding/onboarding.css';

// ── Types ──────────────────────────────────────────────────────
type Phase = 0 | 1 | 2 | 3 | 4 | 5 | 6;

interface SessionState {
  session_id: string;
  session_token: string;
  phase: Phase;
  persona_role: string | null;
  practice_name: string | null;
  track: string;
  state_json: Record<string, unknown>;
  email_anchor: string | null;
}

interface Message {
  id: string;
  role: 'vera' | 'user';
  content: string;
  element?: React.ReactNode;
}

interface ExtractedEntity {
  entity_id: string;
  entity_type: string;
  display: string;
  confidence: number;
  confidence_label: 'high' | 'medium' | 'low';
  source_text: string;
  extracted_fields: Record<string, string>;
  confirmed?: boolean;
}

interface LogoState {
  logo_asset_id: string;
  source_type: string;
  image_url: string | null;
  fallback_type: string;
  initials: string | null;
}

interface GoLiveResult {
  clinic_id: string;
  practice_name: string;
  first_action_targets: string[];
  boundary_statement: string;
  verbose_log: string[];
}

// ── Utility ────────────────────────────────────────────────────
const uid = () => Math.random().toString(36).slice(2, 10);

const API = (path: string) => `/api${path}`;

// ── Typewriter hook ─────────────────────────────────────────────
function useTypewriter(text: string, speed = 22, onDone?: () => void) {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);
  const ref = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDisplayed('');
    setDone(false);
    let i = 0;
    const tick = () => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
        ref.current = setTimeout(tick, speed);
      } else {
        setDone(true);
        onDone?.();
      }
    };
    ref.current = setTimeout(tick, speed);
    return () => { if (ref.current) clearTimeout(ref.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  const skip = useCallback(() => {
    if (ref.current) clearTimeout(ref.current);
    setDisplayed(text);
    setDone(true);
    onDone?.();
  }, [text, onDone]);

  return { displayed, done, skip };
}

// ── VeraMessage ─────────────────────────────────────────────────
function VeraMessage({
  content,
  element,
  onSkip,
}: {
  content: string;
  element?: React.ReactNode;
  onSkip?: () => void;
}) {
  const { displayed, done, skip } = useTypewriter(content, 18, onSkip);

  return (
    <div className="message vera">
      <div className="vera-avatar-sm" aria-hidden="true">V</div>
      <div>
        <div className="message-bubble">
          {displayed}
          {!done && <span className="vera-cursor" aria-hidden="true" />}
        </div>
        {!done && (
          <button className="message-skip-btn" onClick={skip}>
            skip ↓
          </button>
        )}
        {done && element && <div style={{ marginTop: '0.5rem' }}>{element}</div>}
      </div>
    </div>
  );
}

// ── UserMessage ─────────────────────────────────────────────────
function UserMessage({ content }: { content: string }) {
  return (
    <div className="message user">
      <div className="message-bubble">{content}</div>
    </div>
  );
}

// ── RoleSelector ────────────────────────────────────────────────
function RoleSelector({ onSelect }: { onSelect: (role: string) => void }) {
  const roles = [
    { key: 'owner', title: 'Practice Owner', desc: "It's your practice" },
    { key: 'manager', title: 'Practice Manager', desc: 'Day-to-day operations' },
    { key: 'associate', title: 'Associate Vet', desc: "You're part of the team" },
    { key: 'proxy', title: 'Setting this up for someone else', desc: 'On their behalf' },
  ];
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="role-selector">
      {roles.map((r) => (
        <button
          key={r.key}
          className={`role-card ${selected === r.key ? 'selected' : ''}`}
          onClick={() => {
            setSelected(r.key);
            onSelect(r.key);
          }}
          disabled={selected !== null}
        >
          <div className="role-card-title">{r.title}</div>
          <div className="role-card-desc">{r.desc}</div>
        </button>
      ))}
    </div>
  );
}

// ── MagicLinkPrompt ─────────────────────────────────────────────
function MagicLinkPrompt({
  sessionId,
  onSent,
  onSkip,
}: {
  sessionId: string;
  onSent: (email: string) => void;
  onSkip: () => void;
}) {
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const send = async () => {
    if (!email.includes('@')) return;
    setSending(true);
    try {
      const res = await fetch(API('/onboarding/magic-link'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, email }),
      });
      await res.json();
      setSent(true);
      onSent(email);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="magic-link-prompt">
      <div className="magic-link-prompt-title">
        Drop your email — I&apos;ll send a link so you can pick up from any device.
      </div>
      {sent ? (
        <div className="magic-link-sent">✓ Link sent to {email}</div>
      ) : (
        <div className="magic-link-input-row">
          <input
            className="magic-link-input"
            type="email"
            placeholder="you@yourpractice.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            autoFocus
          />
          <button
            className="btn-send-link"
            onClick={send}
            disabled={sending || !email.includes('@')}
          >
            {sending ? '...' : 'Send link'}
          </button>
        </div>
      )}
      <button className="magic-link-skip" onClick={onSkip}>
        Skip for now
      </button>
    </div>
  );
}

// ── EntityRow ───────────────────────────────────────────────────
function EntityRow({
  entity,
  onConfirm,
  onCorrect,
}: {
  entity: ExtractedEntity;
  onConfirm: (id: string) => void;
  onCorrect: (id: string, field: string, value: string) => void;
}) {
  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState(entity.display);

  const submitRename = () => {
    onCorrect(entity.entity_id, 'name', renameVal);
    setRenaming(false);
  };

  const badgeClass = `badge badge-${entity.confidence_label}`;
  const label = entity.confidence_label === 'high' ? '✅' :
    entity.confidence_label === 'medium' ? '⚠️' : '❓';

  return (
    <div className="entity-row">
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span className="entity-name">{entity.display}</span>
          {entity.extracted_fields?.role && (
            <span className="entity-role">· {entity.extracted_fields.role}</span>
          )}
        </div>
        {renaming && (
          <div className="rename-input-row">
            <input
              className="rename-input"
              value={renameVal}
              onChange={(e) => setRenameVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitRename()}
              autoFocus
            />
            <button className="rename-submit-btn" onClick={submitRename}>✓</button>
          </div>
        )}
      </div>
      <span className={badgeClass} title={`Confidence: ${Math.round(entity.confidence * 100)}%`}>
        {label}
      </span>
      <div className="entity-actions">
        {!entity.confirmed && (
          <>
            <button
              className={`confirm-btn ${entity.confirmed ? 'confirmed' : ''}`}
              onClick={() => onConfirm(entity.entity_id)}
              disabled={entity.confirmed}
            >
              ✓ Keep
            </button>
            <button className="rename-btn" onClick={() => setRenaming(r => !r)}>
              ✎ Fix
            </button>
          </>
        )}
        {entity.confirmed && (
          <span style={{ fontSize: '0.75rem', color: '#22c55e' }}>✓</span>
        )}
      </div>
    </div>
  );
}

// ── LogoConfirmCard ─────────────────────────────────────────────
function LogoConfirmCard({
  logo,
  onConfirm,
  onTryNext,
  onUpload,
}: {
  logo: LogoState;
  onConfirm: () => void;
  onTryNext: () => void;
  onUpload: () => void;
}) {
  return (
    <div className="logo-confirmation-card">
      {logo.image_url ? (
        <div className="logo-preview">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={logo.image_url} alt="Practice logo candidate" />
        </div>
      ) : (
        <div className="logo-monogram">{logo.initials || 'V'}</div>
      )}
      <div className="logo-actions">
        <button className="btn-logo-confirm" onClick={onConfirm}>
          ✓ Use this logo
        </button>
        <button className="btn-logo-try-next" onClick={onTryNext}>
          Try a different one
        </button>
        <button className="btn-logo-upload" onClick={onUpload}>
          Upload my own
        </button>
      </div>
    </div>
  );
}

// ── FirstActionsCard ─────────────────────────────────────────────
function FirstActionsCard({ targets }: { targets: string[] }) {
  return (
    <div className="first-actions">
      {targets.map((t, i) => (
        <div key={t} className="first-action-item">
          <span className="first-action-number">#{i + 1}</span>
          {t}
        </div>
      ))}
    </div>
  );
}

// ── Live Panel (Schedule Preview) ───────────────────────────────
function LivePanel({
  practiceName,
  logo,
  providers,
  rooms,
  replacing,
  onGoLive,
  sessionReady,
}: {
  practiceName: string | null;
  logo: LogoState | null;
  providers: Array<{ name: string; role?: string }>;
  rooms: Array<{ name: string }>;
  replacing: boolean;
  onGoLive: () => void;
  sessionReady: boolean;
}) {
  const [activeRoom, setActiveRoom] = useState(0);

  const displayName = practiceName || 'Harmony Animal Hospital';
  const displayProviders = providers.length
    ? providers
    : [{ name: 'Dr. Morgan', role: 'DVM' }, { name: 'Dr. Reyes', role: 'DVM' }, { name: 'Dr. Park', role: 'DVM' }];
  const displayRooms = rooms.length
    ? rooms
    : [{ name: 'Exam 1' }, { name: 'Exam 2' }, { name: 'Surgical Suite' }];

  // Demo schedule slots
  const timeSlots = ['8:00', '8:30', '9:00', '9:30', '10:00', '10:30', '11:00', '11:30', '12:00'];
  const bookedSlots: Record<string, boolean> = {
    '8:00-0': true, '9:00-1': true, '10:30-0': true, '11:00-2': true,
  };

  return (
    <div className={`live-panel ${replacing ? 'replace-container replacing' : 'replace-container'}`}>
      <div className="live-panel-header">
        {logo ? (
          logo.image_url ? (
            <div className="practice-logo">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={logo.image_url} alt="Practice logo" />
            </div>
          ) : (
            <div className="practice-logo">{logo.initials || 'V'}</div>
          )
        ) : (
          <div className="practice-logo" style={{ background: '#6C63FF' }}>
            {displayName.split(' ').map(w => w[0]).join('').slice(0, 3)}
          </div>
        )}

        <span className={practiceName ? 'practice-name-header' : 'practice-name-header practice-name-placeholder'}>
          {displayName}
        </span>

        {sessionReady && (
          <div className="live-panel-go-live">
            <button className="btn-go-live" onClick={onGoLive}>
              Go Live →
            </button>
          </div>
        )}
      </div>

      <div className="live-panel-tabs">
        {displayRooms.map((r, i) => (
          <button
            key={r.name}
            className={`room-tab ${i === activeRoom ? 'active' : ''}`}
            onClick={() => setActiveRoom(i)}
          >
            {r.name}
          </button>
        ))}
      </div>

      <div className="live-panel-schedule">
        {displayProviders.length === 0 ? (
          <div className="schedule-empty">
            <span>Your schedule will appear here</span>
            <span style={{ fontSize: '0.8rem' }}>
              Tell Vera about your team and she&apos;ll build it
            </span>
          </div>
        ) : (
          <div
            className="schedule-grid"
            style={{ '--provider-count': displayProviders.length } as React.CSSProperties}
          >
            <div className="schedule-header-cell"></div>
            {displayProviders.map((p) => (
              <div key={p.name} className="schedule-header-cell">{p.name}</div>
            ))}
            {timeSlots.map((time) => (
              <React.Fragment key={`row-${time}`}>
                <div className="schedule-time-cell">{time}</div>
                {displayProviders.map((_, pi) => (
                  <div
                    key={`slot-${time}-${pi}`}
                    className={`schedule-slot ${bookedSlots[`${time}-${pi}`] ? 'booked' : ''}`}
                  />
                ))}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Onboarding Shell ───────────────────────────────────────
export default function OnboardingPage() {
  const searchParams = useSearchParams();
  const [session, setSession] = useState<SessionState | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [inputDisabled, setInputDisabled] = useState(true);
  const [verboseLogs, setVerboseLogs] = useState<string[]>([]);
  const [practiceName, setPracticeName] = useState<string | null>(null);
  const [providers, setProviders] = useState<Array<{ name: string; role?: string }>>([]);
  const [rooms, setRooms] = useState<Array<{ name: string }>>([]);
  const [logo, setLogo] = useState<LogoState | null>(null);
  const [phase, setPhase] = useState<Phase>(0);
  const [replacing, setReplacing] = useState(false);
  const [entities, setEntities] = useState<ExtractedEntity[]>([]);
  const [goLiveResult, setGoLiveResult] = useState<GoLiveResult | null>(null);
  const [mobileTab, setMobileTab] = useState<'schedule' | 'chat'>('chat');
  const [dragOver, setDragOver] = useState(false);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addLog = (entry: string) => {
    setVerboseLogs((prev) => [...prev, entry]);
  };

  const addMessage = (msg: Omit<Message, 'id'>) => {
    setMessages((prev) => [...prev, { ...msg, id: uid() }]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  // ── Init session ──────────────────────────────────────────────
  useEffect(() => {
    const magicToken = searchParams.get('magic_token');

    if (magicToken) {
      // Resume from magic link
      fetch(API(`/onboarding/resume/${magicToken}`))
        .then((r) => r.json())
        .then((data) => {
          if (data.error) {
            addMessage({
              role: 'vera',
              content: "That link has expired or already been used. Let's start fresh — it takes about 90 seconds.",
            });
            createNewSession();
          } else {
            setSession(data as SessionState);
            setPhase(data.phase as Phase);
            setPracticeName(data.practice_name);
            const s = data.state_json || {};
            if (Array.isArray(s.providers)) setProviders(s.providers);
            if (Array.isArray(s.rooms)) setRooms(s.rooms);
            addLog(data.verbose_log?.[0] || 'VERA (Onboarding): Session resumed');

            const summary = data.state_summary || `Practice: ${data.practice_name || 'in progress'}`;
            addMessage({
              role: 'vera',
              content: `Welcome back. ${summary}. Ready to keep going?`,
            });
            setInputDisabled(false);
          }
        })
        .catch(() => createNewSession());
      return;
    }

    // Normal start
    const existingId = sessionStorage.getItem('onboarding_session_id');
    const existingToken = sessionStorage.getItem('onboarding_session_token');

    if (existingId && existingToken) {
      // Check if session has practice_name already
      fetch(API(`/onboarding/session/${existingToken}`))
        .then((r) => r.json())
        .then((data) => {
          if (data.session_id) {
            setSession(data as SessionState);
            setPhase(data.phase as Phase);
            setPracticeName(data.practice_name);
            runPhaseIntro(data.phase as Phase, data);
          } else {
            createNewSession();
          }
        })
        .catch(() => createNewSession());
    } else {
      createNewSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createNewSession = async () => {
    try {
      const res = await fetch(API('/onboarding/session/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.session_id) {
        sessionStorage.setItem('onboarding_session_id', data.session_id);
        sessionStorage.setItem('onboarding_session_token', data.session_token);
        setSession(data as SessionState);
        addLog(data.verbose_log?.[0] || 'VERA (Onboarding): New session started');
        runPhaseIntro(0, data);
      }
    } catch {
      addMessage({ role: 'vera', content: "Couldn't reach the server. Please refresh and try again." });
    }
  };

  const runPhaseIntro = (p: Phase, sessionData?: Partial<SessionState>) => {
    setPhase(p);
    switch (p) {
      case 0:
        // Phase 0: WELCOME — Q1
        setTimeout(() => {
          addMessage({
            role: 'vera',
            content: "What's your practice called?",
          });
          setInputDisabled(false);
        }, 600);
        break;

      case 2:
        // Phase 2: PIVOT — role select
        addMessage({
          role: 'vera',
          content: "Got it. What's your role at the practice?",
          element: (
            <RoleSelector
              onSelect={(role) => handleRoleSelect(role, sessionData?.session_id)}
            />
          ),
        });
        break;

      case 3:
        // Phase 3: OPEN_PROMPT — Q2
        addMessage({
          role: 'vera',
          content:
            "Tell me about the practice — your team, rooms, hours, what you see. Or paste your website URL and I'll read it.",
        });
        setInputDisabled(false);
        break;

      case 4:
        // Phase 4: DOCUMENT — drop files
        addMessage({
          role: 'vera',
          content:
            "Drop your existing files if you have them — staff roster, schedule, anything. I'll read them and surface what I find.",
          element: (
            <label className="file-upload-btn" style={{ cursor: 'pointer' }}>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp,.gif,.heic"
                onChange={(e) => handleFileUpload(e.target.files?.[0])}
              />
              <div className="file-upload-btn-label">📎 Drop or click to upload</div>
              <div className="file-upload-btn-hint">CSV, Excel, PDF, or image · max 25MB</div>
            </label>
          ),
        });
        setInputDisabled(false);
        break;

      default:
        break;
    }
  };

  // ── Handle user message send ──────────────────────────────────
  const handleSend = async () => {
    const text = inputVal.trim();
    if (!text || !session) return;

    addMessage({ role: 'user', content: text });
    setInputVal('');
    setInputDisabled(true);

    if (phase === 0) {
      // Q1: practice name
      try {
        const res = await fetch(API(`/onboarding/session/${session.session_id}`), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ practice_name: text }),
        });
        const data = await res.json();
        setPracticeName(data.practice_name || text);
        for (const l of data.verbose_log || []) addLog(l);

        // Magic link prompt
        setPhase(2);
        addMessage({
          role: 'vera',
          content: "Before we go further — want a link so you can finish from another device? Totally optional.",
          element: (
            <MagicLinkPrompt
              sessionId={session.session_id}
              onSent={(email) => addLog(`VERA (Onboarding): Magic link issued to ${email}`)}
              onSkip={() => {
                addLog('VERA (Onboarding): Magic link skipped');
                runPhaseIntro(2);
              }}
            />
          ),
        });
      } catch {
        setPracticeName(text);
        addMessage({ role: 'vera', content: "Got it. What's your role at the practice?" });
        setInputDisabled(false);
      }
      return;
    }

    if (phase === 3) {
      // Q2: open prompt
      try {
        const res = await fetch(API('/onboarding/open-prompt'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: session.session_id, text }),
        });
        const data = await res.json();
        for (const l of data.verbose_log || []) addLog(l);

        const extracted = data.extracted_fields || {};
        if (extracted.providers?.length) {
          setProviders(extracted.providers);
        }
        if (extracted.rooms?.length) {
          setRooms(extracted.rooms);
        }

        // Trigger logo scrape if URL detected
        const urlMatch = text.match(/https?:\/\/\S+/);
        if (urlMatch && practiceName) {
          addMessage({
            role: 'vera',
            content: "Found your website — grabbing a logo. One moment.",
          });
          handleLogoScrape(urlMatch[0]);
        }

        addMessage({
          role: 'vera',
          content: "That helps. Want to drop any files you already have? Staff roster, schedule, anything. Or I can work with what you've told me.",
        });
        setPhase(4);
        runPhaseIntro(4);
      } catch {
        addMessage({ role: 'vera', content: "I've noted that. Anything else to add, or ready to proceed?" });
        setInputDisabled(false);
      }
      return;
    }

    if (phase === 4) {
      // During doc phase: treat text as additional context
      addMessage({ role: 'vera', content: "Got it — I'll keep that in mind. Ready to review what I've found?" });
      handleReadyToReview();
      return;
    }

    if (phase === 5) {
      // Replace phase — Go Live confirmation
      if (/\b(yes|go|let.s|start|confirm|do it)\b/i.test(text)) {
        handleGoLive();
      } else {
        addMessage({ role: 'vera', content: "No problem — just say 'Go Live' when ready. Anything else you want me to check first?" });
        setInputDisabled(false);
      }
      return;
    }

    // Phase 6: operational
    addMessage({
      role: 'vera',
      content: "I'm on it. (Operational commands coming in the next build — for now, use the schedule panel on the left.)",
    });
    setInputDisabled(false);
  };

  // ── Role selection ────────────────────────────────────────────
  const handleRoleSelect = async (role: string, sessionId?: string) => {
    const sid = sessionId || session?.session_id;
    if (!sid) return;

    addMessage({ role: 'user', content: role.charAt(0).toUpperCase() + role.slice(1) });

    try {
      const res = await fetch(API(`/onboarding/session/${sid}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona_role: role }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);
    } catch {
      // non-fatal
    }

    runPhaseIntro(3);
  };

  // ── Logo scrape ───────────────────────────────────────────────
  const handleLogoScrape = async (url: string) => {
    if (!session) return;
    try {
      const res = await fetch(API('/onboarding/scrape-logo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id, url }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);
      if (data.logo_asset_id) {
        const logoState: LogoState = {
          logo_asset_id: data.logo_asset_id,
          source_type: data.source_type,
          image_url: data.image_url,
          fallback_type: data.fallback_type,
          initials: data.initials,
        };
        setLogo(logoState);
        addMessage({
          role: 'vera',
          content: data.source_type === 'monogram'
            ? `No image found — I generated initials from your practice name. This it?`
            : `Found a logo from your site. Want to use it?`,
          element: (
            <LogoConfirmCard
              logo={logoState}
              onConfirm={() => handleLogoConfirm(data.logo_asset_id, 'confirm')}
              onTryNext={() => handleLogoConfirm(data.logo_asset_id, 'try_next')}
              onUpload={() => handleLogoConfirm(data.logo_asset_id, 'upload')}
            />
          ),
        });
      }
    } catch {
      // non-fatal
    }
  };

  const handleLogoConfirm = async (assetId: string, action: string) => {
    try {
      const res = await fetch(API(`/onboarding/confirm-logo/${assetId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);

      if (action === 'confirm') {
        addMessage({ role: 'vera', content: 'Logo confirmed — placed in your practice header.' });
        setLogo((prev) => prev ? { ...prev, ...data } : prev);
      } else if (action === 'try_next' && data.logo_asset_id) {
        setLogo(data);
      } else if (action === 'upload') {
        fileInputRef.current?.click();
      }
    } catch {
      // non-fatal
    }
  };

  // ── File upload ───────────────────────────────────────────────
  const handleFileUpload = async (file?: File) => {
    if (!file || !session) return;

    addMessage({ role: 'user', content: `📎 ${file.name}` });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(API(`/onboarding/upload?session_id=${session.session_id}`), {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) {
        addMessage({ role: 'vera', content: data.detail || 'Upload error — please try again.' });
        setInputDisabled(false);
        return;
      }

      for (const l of data.verbose_log || []) addLog(l);
      setDocumentId(data.document_id);

      addMessage({
        role: 'vera',
        content: `Got it — ${data.classified_type?.replace('_', ' ') || 'file'} received. Reading it now...`,
      });

      // Start SSE extraction stream
      startExtractionStream(data.document_id);
    } catch {
      addMessage({ role: 'vera', content: 'Upload failed — please try again.' });
      setInputDisabled(false);
    }
  };

  const startExtractionStream = (docId: string) => {
    const source = new EventSource(API(`/onboarding/extract-stream/${docId}`));

    let newEntities: ExtractedEntity[] = [];

    source.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data);

        if (evt.type === 'start') {
          addLog(`VERA (Onboarding): ${evt.message}`);
        } else if (evt.type === 'tab_found') {
          addLog(`VERA (Onboarding): ${evt.message}`);
        } else if (evt.type === 'entity') {
          const entity: ExtractedEntity = {
            entity_id: evt.entity_id,
            entity_type: evt.entity_type,
            display: evt.display,
            confidence: evt.confidence,
            confidence_label: evt.confidence_label,
            source_text: evt.source_text,
            extracted_fields: evt.extracted_fields || {},
            confirmed: false,
          };
          newEntities = [...newEntities, entity];
          setEntities([...newEntities]);
        } else if (evt.type === 'timeout') {
          addLog(`VERA (Onboarding): ${evt.message}`);
          addMessage({ role: 'vera', content: evt.message });
        } else if (evt.type === 'error') {
          addLog(`VERA (Onboarding): Error — ${evt.message}`);
        } else if (evt.type === 'done') {
          addLog(`VERA (Onboarding): Extraction complete — ${evt.entity_count} entities found`);
          source.close();

          // Update providers/rooms from entities
          const newProviders = newEntities
            .filter((e) => e.entity_type === 'provider')
            .map((e) => ({ name: e.display, role: e.extracted_fields.role }));
          const newRooms = newEntities
            .filter((e) => e.entity_type === 'room')
            .map((e) => ({ name: e.display }));

          if (newProviders.length) setProviders(newProviders);
          if (newRooms.length) setRooms(newRooms);

          addMessage({
            role: 'vera',
            content: `Found ${newEntities.length} item${newEntities.length !== 1 ? 's' : ''}. Review them below — mark anything that's off.`,
          });
          setInputDisabled(false);
        }
      } catch {
        // parse error — ignore
      }
    };

    source.onerror = () => {
      source.close();
      setInputDisabled(false);
    };
  };

  const handleReadyToReview = () => {
    if (entities.length === 0) {
      addMessage({
        role: 'vera',
        content: "No files — no problem. Ready to go live with what you've told me?",
      });
    } else {
      addMessage({
        role: 'vera',
        content: "Here's what I found. Confirm the ones that are right, fix any that aren't.",
      });
    }
    setPhase(5);
    setInputDisabled(false);
  };

  // ── Entity confirmation ───────────────────────────────────────
  const handleConfirmEntity = async (entityId: string) => {
    setEntities((prev) =>
      prev.map((e) => (e.entity_id === entityId ? { ...e, confirmed: true } : e))
    );
    try {
      const res = await fetch(API(`/onboarding/confirm-entity/${entityId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);
    } catch {
      // non-fatal
    }
  };

  const handleCorrectEntity = async (entityId: string, field: string, value: string) => {
    setEntities((prev) =>
      prev.map((e) =>
        e.entity_id === entityId
          ? { ...e, display: value, extracted_fields: { ...e.extracted_fields, [field]: value }, confirmed: true }
          : e
      )
    );
    try {
      const res = await fetch(API(`/onboarding/confirm-entity/${entityId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmed: true,
          correction: { field_name: field, correct_value: value },
        }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);
    } catch {
      // non-fatal
    }
  };

  // ── Go Live ───────────────────────────────────────────────────
  const handleGoLive = async () => {
    if (!session) return;
    setReplacing(true);
    addMessage({ role: 'vera', content: "Replacing Harmony. Building your practice now..." });

    try {
      const res = await fetch(API('/onboarding/go-live'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id }),
      });
      const data = await res.json();
      for (const l of data.verbose_log || []) addLog(l);

      setGoLiveResult(data as GoLiveResult);
      setPhase(6);

      setTimeout(() => {
        setReplacing(false);
        addMessage({
          role: 'vera',
          content: data.boundary_statement,
        });
        addMessage({
          role: 'vera',
          content: "Here's where I'd start:",
          element: <FirstActionsCard targets={data.first_action_targets || []} />,
        });
        setInputDisabled(false);
      }, 3200);
    } catch {
      setReplacing(false);
      addMessage({ role: 'vera', content: "Something went wrong. Please try again in a moment." });
      setInputDisabled(false);
    }
  };

  // ── Drag and drop ─────────────────────────────────────────────
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileUpload(file);
  };

  // ── Render ────────────────────────────────────────────────────
  const sessionReady = phase >= 3 && !!practiceName;

  return (
    <div
      className="onboarding-shell onboarding-body"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Mobile tab bar */}
      <div className="tab-bar" style={{ display: 'flex', order: -1 }}>
        <button
          className={`tab-btn ${mobileTab === 'schedule' ? 'active' : ''}`}
          onClick={() => setMobileTab('schedule')}
        >
          Schedule
        </button>
        <button
          className={`tab-btn ${mobileTab === 'chat' ? 'active' : ''}`}
          onClick={() => setMobileTab('chat')}
        >
          Setup
        </button>
      </div>

      {/* Drop overlay */}
      {dragOver && (
        <div className="drop-overlay active">
          <div className="drop-overlay-inner">
            <div className="drop-overlay-icon">📎</div>
            <div className="drop-overlay-label">Drop file to upload</div>
          </div>
        </div>
      )}

      {/* Live Panel */}
      <LivePanel
        practiceName={practiceName}
        logo={logo}
        providers={providers}
        rooms={rooms}
        replacing={replacing}
        onGoLive={handleGoLive}
        sessionReady={sessionReady}
      />

      {/* Chat Panel */}
      <div className="chat-panel">
        <div className="chat-header">
          <div className="vera-avatar-sm" aria-hidden="true">V</div>
          <span className="vera-label">Vera</span>
          <span className="vera-role-label">Chief of Staff</span>
          <span className="phase-badge" style={{ marginLeft: '0.5rem' }}>
            Phase {phase}
          </span>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="vera-thinking">
              <span /><span /><span />
            </div>
          )}

          {messages.map((msg) =>
            msg.role === 'vera' ? (
              <VeraMessage
                key={msg.id}
                content={msg.content}
                element={msg.element}
              />
            ) : (
              <UserMessage key={msg.id} content={msg.content} />
            )
          )}

          {/* Entity stream display */}
          {entities.length > 0 && phase >= 4 && (
            <div className="extraction-stream">
              {entities.map((entity) => (
                <EntityRow
                  key={entity.entity_id}
                  entity={entity}
                  onConfirm={handleConfirmEntity}
                  onCorrect={handleCorrectEntity}
                />
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Review/GoLive helper button */}
        {phase === 4 && entities.length > 0 && (
          <div style={{ padding: '0.5rem 1rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <button
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleReadyToReview}
            >
              Looks good — continue →
            </button>
          </div>
        )}

        {phase === 5 && !goLiveResult && (
          <div style={{ padding: '0.5rem 1rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <button
              className="btn-go-live"
              style={{ width: '100%' }}
              onClick={handleGoLive}
            >
              Go Live — Replace Harmony →
            </button>
          </div>
        )}

        {/* Input bar */}
        {phase !== 6 && (
          <div className="chat-input-bar">
            <textarea
              className="chat-input"
              placeholder={
                phase === 0 ? "Your practice name..." :
                phase === 3 ? "Describe your practice, or paste a URL..." :
                phase === 4 ? "Or type a description / skip with 'continue'..." :
                "Ask Vera anything..."
              }
              value={inputVal}
              disabled={inputDisabled}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              rows={1}
              aria-label="Message to Vera"
            />
            <button
              className="chat-send-btn"
              onClick={handleSend}
              disabled={inputDisabled || !inputVal.trim()}
              aria-label="Send message"
            >
              →
            </button>
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp,.gif,.heic"
          onChange={(e) => handleFileUpload(e.target.files?.[0])}
        />
      </div>

      {/* Verbose Log Panel */}
      <VerboseLogPanel logs={verboseLogs} />
    </div>
  );
}
