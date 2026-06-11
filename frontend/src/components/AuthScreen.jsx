import { useState } from "react";
import { auth, token } from "../api.js";

export default function AuthScreen({ onAuthed }) {
  const [mode, setMode] = useState("login"); // 'login' | 'signup'
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  async function submit(e) {
    e?.preventDefault();
    if (busy) return;
    setError(null);

    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setBusy(true);
    try {
      const fn = isSignup ? auth.signup : auth.login;
      const { token: jwt, user } = await fn(email.trim(), password);
      token.set(jwt);
      onAuthed(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark" />
          <div className="brand-name">
            Zero-to-Synced
            <small>pipeline agent</small>
          </div>
        </div>

        <h1 className="auth-title">
          {isSignup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="auth-sub">
          {isSignup
            ? "Start turning plain English into live data pipelines."
            : "Sign in to pick up your pipelines where you left off."}
        </p>

        <form onSubmit={submit} className="auth-form">
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete={isSignup ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isSignup ? "At least 8 characters" : "Your password"}
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={busy}>
            {busy ? "One moment…" : isSignup ? "Create account" : "Sign in"}
          </button>
        </form>

        <div className="auth-switch">
          {isSignup ? "Already have an account?" : "New here?"}{" "}
          <button
            type="button"
            onClick={() => {
              setMode(isSignup ? "login" : "signup");
              setError(null);
            }}
          >
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </div>
      </div>
    </div>
  );
}
