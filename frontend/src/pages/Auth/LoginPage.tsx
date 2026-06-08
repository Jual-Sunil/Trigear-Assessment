import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LoginButton } from "../../components/auth/LoginButton";
import { useAuthStore } from "../../store/authStore";
import { useLogin } from "../../hooks/useAuth";
import heroImage from "../../assets/hero.png";

/**
 * Full-page login screen.
 * Redirects already-authenticated users to the dashboard.
 * Renders the Google OAuth sign-in button for unauthenticated users.
 */
export function Component() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate = useNavigate();
  const { error } = useLogin();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return (
    <>
      <style>{CSS}</style>
      <div className="auth-root">
        {/* ── Background effects ── */}
        <div className="auth-bg" aria-hidden="true">
          <div className="auth-bg-orb auth-bg-orb-1" />
          <div className="auth-bg-orb auth-bg-orb-2" />
          <div className="auth-bg-grid" />
        </div>

        {/* ── Left panel – hero + value prop ── */}
        <div className="auth-left">
          <div className="auth-left-inner">
            {/* Wordmark */}
            <div className="auth-wordmark">
              <span className="auth-wordmark-icon" aria-hidden="true">
                <MailIcon />
              </span>
              <span className="auth-wordmark-text">Mail Intel</span>
            </div>

            {/* Headline */}
            <div className="auth-headline">
              <h1 className="auth-h1">
                Your inbox,<br />
                <span className="auth-h1-accent">intelligently decoded.</span>
              </h1>
              <p className="auth-subhead">
                AI reads your Gmail so you don't have to. Extract tasks,
                surface job leads, and track interviews — automatically.
              </p>
            </div>

            {/* Feature pills */}
            <ul className="auth-features" aria-label="Key features">
              {FEATURES.map((f) => (
                <li key={f.label} className="auth-feature">
                  <span className="auth-feature-dot" aria-hidden="true" />
                  {f.label}
                </li>
              ))}
            </ul>

            {/* Hero illustration */}
            <div className="auth-hero-wrap" aria-hidden="true">
              <img
                src={heroImage}
                alt=""
                className="auth-hero-img"
                draggable={false}
              />
              <div className="auth-hero-glow" />
            </div>
          </div>
        </div>

        {/* ── Right panel – auth card ── */}
        <div className="auth-right">
          <div className="auth-card" role="main" aria-label="Sign in">
            <div className="auth-card-inner">
              {/* Mobile-only wordmark */}
              <div className="auth-card-brand">
                <span className="auth-wordmark-icon auth-wordmark-icon-sm" aria-hidden="true">
                  <MailIcon />
                </span>
                <span className="auth-wordmark-text auth-wordmark-text-sm">Mail Intel</span>
              </div>

              <div className="auth-card-copy">
                <h2 className="auth-card-title">Sign in to continue</h2>
                <p className="auth-card-desc">
                  Connect your Google account to get started. We only request
                  read-only Gmail access.
                </p>
              </div>

              {/* Error state */}
              {error && (
                <div className="auth-error" role="alert">
                  <span className="auth-error-icon" aria-hidden="true">
                    <ErrorIcon />
                  </span>
                  <span className="auth-error-msg">{error}</span>
                </div>
              )}

              <LoginButton />

              <div className="auth-divider" aria-hidden="true">
                <span className="auth-divider-line" />
                <span className="auth-divider-text">secure OAuth 2.0</span>
                <span className="auth-divider-line" />
              </div>

              <ul className="auth-trust-list" aria-label="Security guarantees">
                {TRUST.map((t) => (
                  <li key={t} className="auth-trust-item">
                    <span className="auth-trust-check" aria-hidden="true">
                      <CheckIcon />
                    </span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className="auth-legal">
            By signing in, you agree to our{" "}
            <a href="#" className="auth-legal-link">Terms of Service</a>{" "}
            and{" "}
            <a href="#" className="auth-legal-link">Privacy Policy</a>.
          </p>
        </div>
      </div>
    </>
  );
}

/* ── Icons ──────────────────────────────────── */
function MailIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-10 7L2 7" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

/* ── Data ───────────────────────────────────── */
const FEATURES = [
  { label: "Auto-extract tasks from every email" },
  { label: "Detect job leads & opportunities" },
  { label: "Track interview scheduling" },
  { label: "Unified search across your inbox" },
];

const TRUST = [
  "Read-only Gmail access",
  "No emails stored or modified",
  "Revoke access anytime from Google",
];

/* ── Styles ─────────────────────────────────── */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

.auth-root {
  min-height: 100dvh;
  display: flex;
  background: #080810;
  position: relative;
  overflow: hidden;
  font-family: 'DM Sans', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ── Background ── */
.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.auth-bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.18;
}

.auth-bg-orb-1 {
  width: 560px;
  height: 560px;
  background: radial-gradient(circle, #7c3aed 0%, transparent 70%);
  top: -120px;
  left: 10%;
  animation: auth-orb-drift 14s ease-in-out infinite alternate;
}

.auth-bg-orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
  bottom: -80px;
  left: 30%;
  animation: auth-orb-drift 18s ease-in-out infinite alternate-reverse;
}

@keyframes auth-orb-drift {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(40px, 30px) scale(1.08); }
}

.auth-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(139, 92, 246, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139, 92, 246, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 80% 80% at 30% 40%, black 20%, transparent 100%);
}

/* ── Left Panel ── */
.auth-left {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 64px 56px 64px 72px;
  position: relative;
  z-index: 1;
}

.auth-left-inner {
  max-width: 520px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  animation: auth-fade-up 0.6s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes auth-fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Wordmark ── */
.auth-wordmark {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auth-wordmark-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 0 0 1px rgba(139,92,246,0.4), 0 4px 12px rgba(124,58,237,0.3);
  flex-shrink: 0;
}

.auth-wordmark-icon-sm {
  width: 26px;
  height: 26px;
  border-radius: 7px;
}

.auth-wordmark-text {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #f0eeff;
}

.auth-wordmark-text-sm {
  font-size: 15px;
}

/* ── Headline ── */
.auth-headline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-h1 {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: clamp(36px, 4.5vw, 54px);
  font-weight: 400;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: #ede9fe;
  margin: 0;
}

.auth-h1-accent {
  font-style: italic;
  background: linear-gradient(135deg, #a78bfa 0%, #818cf8 50%, #c4b5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.auth-subhead {
  font-size: 15px;
  font-weight: 400;
  line-height: 1.65;
  color: #8b82a8;
  max-width: 400px;
  margin: 0;
}

/* ── Features ── */
.auth-features {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0;
  margin: 0;
}

.auth-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 400;
  color: #a09cc0;
  letter-spacing: -0.01em;
}

.auth-feature-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #7c3aed;
  box-shadow: 0 0 6px rgba(124,58,237,0.8);
  flex-shrink: 0;
}

/* ── Hero image ── */
.auth-hero-wrap {
  position: relative;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.auth-hero-img {
  width: 260px;
  height: auto;
  object-fit: contain;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 32px rgba(124,58,237,0.25));
  animation: auth-hero-float 6s ease-in-out infinite;
}

@keyframes auth-hero-float {
  0%, 100% { transform: translateY(0px); }
  50%       { transform: translateY(-10px); }
}

.auth-hero-glow {
  position: absolute;
  bottom: -20px;
  left: 40px;
  width: 180px;
  height: 40px;
  background: radial-gradient(ellipse, rgba(124,58,237,0.35) 0%, transparent 70%);
  filter: blur(12px);
  z-index: 0;
  animation: auth-hero-float 6s ease-in-out infinite;
}

/* ── Right Panel ── */
.auth-right {
  width: 440px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  position: relative;
  z-index: 1;
}

/* Vertical separator */
.auth-right::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10%;
  bottom: 10%;
  width: 1px;
  background: linear-gradient(
    to bottom,
    transparent,
    rgba(139,92,246,0.15) 30%,
    rgba(139,92,246,0.15) 70%,
    transparent
  );
}

/* ── Auth Card ── */
.auth-card {
  width: 100%;
  border-radius: 20px;
  background: rgba(15, 12, 28, 0.7);
  border: 1px solid rgba(139,92,246,0.18);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.04) inset,
    0 32px 64px rgba(0,0,0,0.5),
    0 0 48px rgba(124,58,237,0.06);
  animation: auth-fade-up 0.7s 0.1s cubic-bezier(0.16,1,0.3,1) both;
  position: relative;
  overflow: hidden;
}

/* Top shimmer edge */
.auth-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(167,139,250,0.4), transparent);
}

.auth-card-inner {
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Mobile-only brand */
.auth-card-brand {
  display: none;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.auth-card-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-card-title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #ede9fe;
  margin: 0;
  line-height: 1.2;
}

.auth-card-desc {
  font-size: 14px;
  line-height: 1.6;
  color: #7a738f;
  margin: 0;
}

/* ── Error state ── */
.auth-error {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(244,63,94,0.08);
  border: 1px solid rgba(244,63,94,0.22);
}

.auth-error-icon {
  color: #f43f5e;
  flex-shrink: 0;
  margin-top: 1px;
}

.auth-error-msg {
  font-size: 13px;
  font-weight: 400;
  color: #fda4af;
  line-height: 1.5;
}

/* ── Login Button (injected via LoginButton.tsx) ── */
.login-btn {
  position: relative;
  width: 100%;
  height: 46px;
  border-radius: 11px;
  border: 1px solid rgba(139,92,246,0.3);
  background: rgba(99,102,241,0.1);
  cursor: pointer;
  overflow: hidden;
  transition:
    background 0.18s cubic-bezier(0.16,1,0.3,1),
    border-color 0.18s cubic-bezier(0.16,1,0.3,1),
    transform 0.14s cubic-bezier(0.16,1,0.3,1),
    box-shadow 0.18s cubic-bezier(0.16,1,0.3,1);
  font-family: 'DM Sans', system-ui, sans-serif;
}

.login-btn:hover:not(:disabled) {
  background: rgba(99,102,241,0.18);
  border-color: rgba(139,92,246,0.5);
  box-shadow: 0 0 24px rgba(124,58,237,0.18), 0 4px 12px rgba(0,0,0,0.3);
  transform: translateY(-1px);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: none;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-btn:focus-visible {
  outline: 2px solid rgba(139,92,246,0.7);
  outline-offset: 2px;
}

.login-btn-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.login-btn-text {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: #e9e4ff;
}

.login-btn-glow {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0;
  background: radial-gradient(circle at 50% 50%, rgba(139,92,246,0.15), transparent 70%);
  transition: opacity 0.3s;
}

.login-btn:hover .login-btn-glow { opacity: 1; }

/* Spinner */
.login-btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(139,92,246,0.25);
  border-top-color: #a78bfa;
  border-radius: 50%;
  animation: auth-spin 0.65s linear infinite;
  flex-shrink: 0;
}

@keyframes auth-spin {
  to { transform: rotate(360deg); }
}

/* ── Divider ── */
.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auth-divider-line {
  flex: 1;
  height: 1px;
  background: rgba(139,92,246,0.12);
}

.auth-divider-text {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #4d4668;
  white-space: nowrap;
}

/* ── Trust list ── */
.auth-trust-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-trust-item {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  color: #5c5578;
  letter-spacing: -0.005em;
}

.auth-trust-check {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(124,58,237,0.15);
  border: 1px solid rgba(124,58,237,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7c3aed;
  flex-shrink: 0;
}

/* ── Legal ── */
.auth-legal {
  margin-top: 20px;
  font-size: 11.5px;
  color: #3d3655;
  text-align: center;
  line-height: 1.6;
}

.auth-legal-link {
  color: #6d5eac;
  text-decoration: none;
  border-bottom: 1px solid rgba(109,94,172,0.3);
  transition: color 0.15s, border-color 0.15s;
}

.auth-legal-link:hover {
  color: #a78bfa;
  border-color: rgba(167,139,250,0.5);
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .auth-root {
    flex-direction: column;
    align-items: stretch;
  }

  .auth-left {
    padding: 56px 32px 32px;
    flex: none;
  }

  .auth-left-inner {
    max-width: 100%;
    gap: 28px;
    align-items: flex-start;
  }

  .auth-hero-wrap {
    display: none;
  }

  .auth-h1 { font-size: clamp(30px, 7vw, 42px); }

  .auth-right {
    width: 100%;
    padding: 24px 24px 56px;
  }

  .auth-right::before { display: none; }
}

@media (max-width: 600px) {
  .auth-left { padding: 40px 20px 24px; }

  .auth-right { padding: 16px 16px 48px; }

  .auth-card-inner { padding: 28px 24px; }

  .auth-card-brand { display: flex; }
}

@media (max-width: 900px) {
  .auth-features {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .auth-features {
    grid-template-columns: 1fr;
  }
}
`;

export default Component;
