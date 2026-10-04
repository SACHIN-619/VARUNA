import React, { useState } from 'react';
import { loginUser, AuthUser } from '../services/auth';

interface LoginPageProps {
  onLogin: (user: AuthUser) => void;
  onBackToLanding?: () => void;
}

const DEMO_CREDENTIALS = [
  { label: 'Forecaster', email: 'forecaster@ncmrwf.gov.in', role: 'FORECASTER', color: '#22c55e' },
  { label: 'Operations', email: 'ops@ncmrwf.gov.in', role: 'OPERATIONS', color: '#3b82f6' },
  { label: 'Model Analyst', email: 'analyst@ncmrwf.gov.in', role: 'ANALYST', color: '#a855f7' },
  { label: 'Administrator', email: 'admin@ncmrwf.gov.in', role: 'ADMIN', color: '#f97316' },
  { label: 'Auditor', email: 'auditor@ncmrwf.gov.in', role: 'AUDITOR', color: '#64748b' },
];

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onBackToLanding }) => {
  const [email, setEmail] = useState('forecaster@ncmrwf.gov.in');
  const [password, setPassword] = useState('varuna2026');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await loginUser(email.trim(), password);
      onLogin(user);
    } catch (err: any) {
      // Wrong credentials must be rejected (the old "guaranteed fallback" logged in any password)
      setError(err?.message || 'Sign-in failed.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('varuna2026');
    setError(null);
    setLoading(true);
    try {
      const user = await loginUser(demoEmail, 'varuna2026');
      onLogin(user);
    } catch (err: any) {
      setError(err?.message || 'Sign-in failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 40%, #0a1628 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Inter', -apple-system, sans-serif",
      padding: '1rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Atmospheric grid background */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.06,
        backgroundImage: 'linear-gradient(rgba(99,179,237,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(99,179,237,0.3) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }} />

      {/* Glow orbs */}
      <div style={{
        position: 'absolute', top: '-10%', left: '-10%', width: '50%', height: '50%',
        background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 60%)',
        borderRadius: '50%',
      }} />
      <div style={{
        position: 'absolute', bottom: '-10%', right: '-10%', width: '60%', height: '60%',
        background: 'radial-gradient(circle, rgba(168,85,247,0.10) 0%, transparent 60%)',
        borderRadius: '50%',
      }} />

      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: '440px' }}>
        {/* Top Back Navigation */}
        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
              background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(99,179,237,0.2)',
              borderRadius: '9999px', padding: '0.4rem 0.9rem', color: '#94a3b8',
              fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', marginBottom: '1.25rem',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = '#38bdf8'; e.currentTarget.style.borderColor = 'rgba(56,189,248,0.4)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(99,179,237,0.2)'; }}
          >
            ← Back to Platform Overview
          </button>
        )}

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.75rem',
            background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.4)',
            borderRadius: '12px', padding: '0.5.rem 1rem', marginBottom: '1.5rem',
          }}>
            <span style={{ fontSize: '0.75rem', color: '#bfdbfe', fontWeight: 700, letterSpacing: '0.1em' }}>
              SIH26081 · MoES / NCMRWF
            </span>
          </div>
          <h1 style={{
            fontSize: '2.8rem', fontWeight: 900, letterSpacing: '-0.04em',
            background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #67e8f9 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            margin: 0, lineHeight: 1,
          }}>VARUNA</h1>
          <p style={{ color: '#e2e8f0', fontSize: '0.9rem', marginTop: '0.6rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            Adaptive Forecast Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(99,179,237,0.3)',
          borderRadius: '20px',
          padding: '2rem',
          boxShadow: '0 32px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1) inset',
        }}>
          <h2 style={{ color: '#ffffff', fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', marginTop: 0 }}>
            Operational Sign-In
          </h2>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                INSTITUTIONAL EMAIL
              </label>
              <input
                id="varuna-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'rgba(30,41,59,0.95)', border: '1px solid rgba(99,179,237,0.4)',
                  borderRadius: '10px', color: '#ffffff', fontSize: '0.95rem', fontWeight: 500,
                  padding: '0.8rem 1rem', outline: 'none', transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(56,189,248,0.8)'}
                onBlur={e => e.target.style.borderColor = 'rgba(99,179,237,0.4)'}
                placeholder="name@ncmrwf.gov.in"
                autoComplete="email"
              />
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                PASSWORD
              </label>
              <input
                id="varuna-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'rgba(30,41,59,0.95)', border: '1px solid rgba(99,179,237,0.4)',
                  borderRadius: '10px', color: '#ffffff', fontSize: '0.95rem', fontWeight: 500,
                  padding: '0.8rem 1rem', outline: 'none', transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(56,189,248,0.8)'}
                onBlur={e => e.target.style.borderColor = 'rgba(99,179,237,0.4)'}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div style={{
                background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)',
                borderRadius: '8px', padding: '0.7rem 0.9rem', marginBottom: '1rem',
                color: '#fecaca', fontSize: '0.85rem', fontWeight: 600,
              }}>
                ⚠ {error}
              </div>
            )}

            <button
              id="varuna-login-btn"
              type="submit"
              disabled={loading}
              style={{
                width: '100%', padding: '0.9rem',
                background: loading
                  ? 'rgba(59,130,246,0.4)'
                  : 'linear-gradient(135deg, #0284c7 0%, #4f46e5 100%)',
                border: 'none', borderRadius: '10px',
                color: '#ffffff', fontSize: '0.95rem', fontWeight: 800, letterSpacing: '0.04em',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s', transform: loading ? 'none' : undefined,
                boxShadow: loading ? 'none' : '0 4px 20px rgba(14,165,233,0.4)',
              }}
              onMouseEnter={e => { if (!loading) (e.target as HTMLButtonElement).style.transform = 'translateY(-1px)'; }}
              onMouseLeave={e => { (e.target as HTMLButtonElement).style.transform = 'none'; }}
            >
              {loading ? '⟳ Authenticating...' : '→ Enter Operations Center'}
            </button>
          </form>

          {/* Demo Credentials */}
          <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(99,179,237,0.2)' }}>
            <p style={{ color: '#cbd5e1', fontSize: '0.78rem', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.75rem', marginTop: 0 }}>
              DEMO ROLES  ·  password: <code style={{ color: '#38bdf8', fontWeight: 700 }}>varuna2026</code>
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
              {DEMO_CREDENTIALS.map(cred => (
                <button
                  key={cred.role}
                  id={`demo-${cred.role.toLowerCase()}`}
                  onClick={() => fillDemo(cred.email)}
                  style={{
                    background: `rgba(${cred.color === '#22c55e' ? '34,197,94' : cred.color === '#3b82f6' ? '59,130,246' : cred.color === '#a855f7' ? '168,85,247' : '249,115,22'},0.15)`,
                    border: `1px solid ${cred.color}50`,
                    borderRadius: '8px', padding: '0.6rem 0.7rem',
                    color: '#ffffff', fontSize: '0.78rem', fontWeight: 700,
                    cursor: 'pointer', transition: 'all 0.15s', textAlign: 'left',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = cred.color; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = cred.color + '50'; }}
                >
                  <div style={{ color: cred.color, marginBottom: '0.15rem', fontWeight: 800 }}>{cred.label}</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.7rem', fontFamily: 'monospace' }}>
                    {cred.email.split('@')[0]}@ncmrwf
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.75rem', marginTop: '1.5rem', fontWeight: 500 }}>
          Prototype · Not for public operational use · SIH 2026
        </p>
      </div>
    </div>
  );
};
