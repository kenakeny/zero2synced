import { useState } from "react";
import { fivetran } from "../api.js";

export default function ConnectFivetran({ onConnected, onLogout, userEmail }) {
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e?.preventDefault();
    if (busy) return;
    setError(null);
    if (!apiKey.trim() || !apiSecret.trim()) {
      setError("Enter both your API key and secret.");
      return;
    }
    setBusy(true);
    try {
      await fivetran.connect(apiKey.trim(), apiSecret.trim());
      onConnected();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth-card connect-card">
        <div className="auth-brand">
          <div className="brand-mark" />
          <div className="brand-name">
            Zero-to-Synced
            <small>pipeline agent</small>
          </div>
        </div>

        <h1 className="auth-title">Connect your Fivetran account</h1>
        <p className="auth-sub">
          The agent uses your Fivetran keys to discover connectors and set up
          syncs on your behalf. They're encrypted and never shared.
        </p>

        <form onSubmit={submit} className="auth-form">
          <label className="field">
            <span>Fivetran API key</span>
            <input
              type="text"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="e.g. d9X2k7..."
            />
          </label>

          <label className="field">
            <span>Fivetran API secret</span>
            <input
              type="password"
              autoComplete="off"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder="Your API secret"
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={busy}>
            {busy ? "Verifying with Fivetran…" : "Connect Fivetran"}
          </button>
        </form>

        <p className="connect-help">
          Find these under{" "}
          <a
            href="https://fivetran.com/docs/rest-api/getting-started"
            target="_blank"
            rel="noreferrer"
          >
            Fivetran → API key
          </a>
          . We verify them before saving.
        </p>

        <div className="auth-switch">
          Signed in as {userEmail} ·{" "}
          <button type="button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
