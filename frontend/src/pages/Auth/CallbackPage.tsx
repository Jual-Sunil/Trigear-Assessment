import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthCallback } from "../../hooks/useAuth";

/**
 * OAuth2 callback landing page.
 *
 * Google redirects here after the user completes the consent screen.
 * The backend has already exchanged the code and set the HttpOnly session
 * cookie by the time this component mounts. This page calls GET /auth/me
 * to hydrate the Zustand store with the authenticated user, then
 * navigates to the dashboard.
 */
export function Component() {
  const navigate = useNavigate();
  const { resolveCallback, isLoading, error } = useAuthCallback();
  const called = useRef(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    // Stagger step progression for UX feedback
    const t1 = setTimeout(() => setStep(1), 400);
    const t2 = setTimeout(() => setStep(2), 1100);

    resolveCallback().then(() => {
      setStep(3);
      navigate("/", { replace: true });
    });

    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <>
      <style>{CSS}</style>
      <div className="cb-root">
        {/* Background */}
        <div className="cb-bg" aria-hidden="true">
          <div className="cb-bg-orb" />
          <div className="cb-bg-grid" />
        </div>

        {/* Loading state */}
        {!error && (
          <div className="cb-card" role="status" aria-live="polite" aria-label="Completing sign-in">
            <div className="cb-card-inner">
              {/* Animated logo */}
              <div className="cb-logo-wrap" aria-hidden="true">
                <div className="cb-logo-ring cb-logo-ring-outer" />
                <div className="cb-logo-ring cb-logo-ring-inner" />
                <div className="cb-logo-core">
                  <MailIcon />
                </div>
              </div>

              <div className="cb-text">
                <h1 className="cb-title">Signing you in</h1>
                <p className="cb-subtitle">Just a moment…</p>
              </div>

              {/* Step progress */}
              <ol className="cb-steps" aria-label="Sign-in progress">
                {STEPS.map((s, i) => {
                  const state =
                    i < step ? "done" :
                    i === step ? "active" : "pending";
                  return (
                    <li key={s} className={`cb-step cb-step-${state}`} aria-current={state === "active" ? "step" : undefined}>
                      <span className="cb-step-indicator" aria-hidden="true">
                        {state === "done" ? <CheckIcon /> :
                         state === "active" ? <span className="cb-step-dot-pulse" /> :
                         <span className="cb-step-dot" />}
                      </span>
                      <span className="cb-step-label">{s}</span>
                    </li>
                  );
                })}
              </ol>

              {/* Progress bar */}
              <div className="cb-progress-track" aria-hidden="true">
                <div
                  className="cb-progress-fill"
                  style={{ width: `${Math.min(100, (step / (STEPS.length - 1)) * 100)}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="cb-card cb-card-error" role="alert" aria-live="assertive">
            <div className="cb-card-inner">
              <div className="cb-error-icon-wrap" aria-hidden="true">
                <div className="cb-error-ring" />
                <span className="cb-error-icon-core">
                  <AlertIcon />
                </span>
              </div>

              <div className="cb-text">
                <h1 className="cb-title cb-title-error">Authentication failed</h1>
                <p className="cb-error-msg">{error}</p>
              </div>

              <button
                className="cb-retry-btn"
                onClick={() => navigate("/login", { replace: true })}
                aria-label="Return to sign-in page"
              >
                <ArrowIcon />
                Try again
              </button>

              <p className="cb-error-hint">
                If this keeps happening, try clearing your browser cookies.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

/* ── Icons ──────────────────────────────────── */
function MailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-10 7L2 7" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

/* ── Data ───────────────────────────────────── */
const STEPS = [
  "Verifying with Google",
  "Loading your profile",
  "Preparing your workspace",
];

/* ── Styles ─────────────────────────────────── */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

.cb-root {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #080810;
  font-family: 'DM Sans', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  position: relative;
  overflow: hidden;
  padding: 24px;
}

/* ── Background ── */
.cb-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.cb-bg-orb {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(124,58,237,0.2) 0%, transparent 65%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  filter: blur(60px);
  animation: cb-orb-pulse 4s ease-in-out infinite;
}

@keyframes cb-orb-pulse {
  0%, 100% { opacity: 0.6; transform: translate(-50%,-50%) scale(1); }
  50%       { opacity: 1;   transform: translate(-50%,-50%) scale(1.12); }
}

.cb-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(139,92,246,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139,92,246,0.04) 1px, transparent 1px);
  background-size: 48px 48px;
}

/* ── Card ── */
.cb-card {
  width: 100%;
  max-width: 380px;
  border-radius: 20px;
  background: rgba(13, 10, 26, 0.75);
  border: 1px solid rgba(139,92,246,0.2);
  backdrop-filter: blur(28px) saturate(1.5);
  -webkit-backdrop-filter: blur(28px) saturate(1.5);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.04) inset,
    0 40px 80px rgba(0,0,0,0.6),
    0 0 60px rgba(124,58,237,0.08);
  position: relative;
  overflow: hidden;
  animation: cb-slide-up 0.5s cubic-bezier(0.16,1,0.3,1) both;
}

/* top edge shimmer */
.cb-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(167,139,250,0.5), transparent);
}

.cb-card-error {
  border-color: rgba(244,63,94,0.22);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.03) inset,
    0 40px 80px rgba(0,0,0,0.6),
    0 0 60px rgba(244,63,94,0.05);
}

.cb-card-error::before {
  background: linear-gradient(90deg, transparent, rgba(244,63,94,0.35), transparent);
}

@keyframes cb-slide-up {
  from { opacity: 0; transform: translateY(20px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0)   scale(1); }
}

.cb-card-inner {
  padding: 44px 36px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
}

/* ── Logo animation ── */
.cb-logo-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cb-logo-ring {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(124,58,237,0.3);
}

.cb-logo-ring-outer {
  inset: 0;
  animation: cb-ring-spin 3s linear infinite;
  border-top-color: rgba(167,139,250,0.7);
}

.cb-logo-ring-inner {
  inset: 10px;
  animation: cb-ring-spin 2s linear infinite reverse;
  border-top-color: rgba(99,102,241,0.6);
}

@keyframes cb-ring-spin {
  to { transform: rotate(360deg); }
}

.cb-logo-core {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 0 0 1px rgba(139,92,246,0.4), 0 4px 16px rgba(124,58,237,0.4);
  z-index: 1;
}

/* ── Text ── */
.cb-text {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cb-title {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #ede9fe;
  margin: 0;
}

.cb-title-error {
  color: #fda4af;
}

.cb-subtitle {
  font-size: 13.5px;
  color: #6b6386;
  margin: 0;
  letter-spacing: -0.01em;
}

/* ── Steps ── */
.cb-steps {
  width: 100%;
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cb-step {
  display: flex;
  align-items: center;
  gap: 10px;
  transition: opacity 0.3s;
}

.cb-step-pending { opacity: 0.3; }
.cb-step-active  { opacity: 1; }
.cb-step-done    { opacity: 0.7; }

.cb-step-indicator {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cb-step-done .cb-step-indicator {
  background: rgba(124,58,237,0.2);
  border: 1px solid rgba(124,58,237,0.4);
  color: #a78bfa;
}

.cb-step-active .cb-step-indicator,
.cb-step-pending .cb-step-indicator {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(139,92,246,0.15);
}

.cb-step-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4d4668;
  display: block;
}

.cb-step-dot-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #7c3aed;
  display: block;
  box-shadow: 0 0 0 0 rgba(124,58,237,0.5);
  animation: cb-pulse 1.4s ease-out infinite;
}

@keyframes cb-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(124,58,237,0.6); }
  70%  { box-shadow: 0 0 0 6px rgba(124,58,237,0); }
  100% { box-shadow: 0 0 0 0 rgba(124,58,237,0); }
}

.cb-step-label {
  font-size: 13.5px;
  font-weight: 400;
  color: #8b82a8;
  letter-spacing: -0.01em;
}

.cb-step-done .cb-step-label {
  color: #6b6386;
  text-decoration: line-through;
  text-decoration-color: rgba(107,99,134,0.4);
}

.cb-step-active .cb-step-label {
  color: #c4b5fd;
  font-weight: 500;
}

/* ── Progress track ── */
.cb-progress-track {
  width: 100%;
  height: 2px;
  border-radius: 2px;
  background: rgba(139,92,246,0.1);
  overflow: hidden;
}

.cb-progress-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #7c3aed, #818cf8);
  transition: width 0.6s cubic-bezier(0.16,1,0.3,1);
  box-shadow: 0 0 8px rgba(124,58,237,0.6);
}

/* ── Error state ── */
.cb-error-icon-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cb-error-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1.5px solid rgba(244,63,94,0.25);
  animation: cb-error-ring-pulse 2s ease-in-out infinite;
}

@keyframes cb-error-ring-pulse {
  0%, 100% { transform: scale(1);    opacity: 0.6; }
  50%       { transform: scale(1.1); opacity: 1; }
}

.cb-error-icon-core {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(244,63,94,0.1);
  border: 1px solid rgba(244,63,94,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f43f5e;
  z-index: 1;
}

.cb-error-msg {
  font-size: 13.5px;
  color: #9f7a84;
  line-height: 1.55;
  text-align: center;
  margin: 0;
  max-width: 280px;
}

.cb-retry-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 40px;
  padding: 0 20px;
  border-radius: 9px;
  background: rgba(244,63,94,0.1);
  border: 1px solid rgba(244,63,94,0.25);
  color: #fda4af;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 13.5px;
  font-weight: 500;
  letter-spacing: -0.01em;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.12s;
}

.cb-retry-btn:hover {
  background: rgba(244,63,94,0.16);
  border-color: rgba(244,63,94,0.4);
  transform: translateY(-1px);
}

.cb-retry-btn:active {
  transform: translateY(0);
}

.cb-retry-btn:focus-visible {
  outline: 2px solid rgba(244,63,94,0.5);
  outline-offset: 2px;
}

.cb-error-hint {
  font-size: 12px;
  color: #3d3655;
  text-align: center;
  margin: 0;
  line-height: 1.5;
}

/* ── Responsive ── */
@media (max-width: 440px) {
  .cb-card-inner { padding: 36px 24px 32px; }
}
`;

export default Component;
