import { useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { api } from "../api";
import { setSplunkAuth } from "../utils/splunkAuth";
import { AppLogo } from "./ui/AppLogo";

interface SplunkAuthGateProps {
  inline?: boolean;
  onAuthenticated: () => void;
}

export function SplunkAuthGate({ inline, onAuthenticated }: SplunkAuthGateProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.splunkLogin(username.trim(), password);
      setSplunkAuth(username.trim(), password);
      if (!res.splunk_connected) {
        setError("Signed in, but Splunk API is unreachable.");
      }
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`auth-gate ${inline ? "auth-gate--inline" : ""}`}>
      <div className="auth-gate__card">
        {!inline && (
          <div className="auth-gate__brand">
            <div className="auth-gate__logo">
              <AppLogo size={44} />
            </div>
            <div>
              <h1>SignalSmith</h1>
              <p>Telemetry optimization workspace</p>
            </div>
          </div>
        )}

        <h2>{inline ? "Switch account" : "Sign in"}</h2>

        <form className="auth-gate__form" onSubmit={submit}>
          <div className="auth-field">
            <label htmlFor="splunk-username">Username</label>
            <input
              id="splunk-username"
              type="text"
              name="username"
              autoComplete="username"
              autoFocus={!inline}
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              required
            />
          </div>
          <div className="auth-field">
            <label htmlFor="splunk-password">Password</label>
            <div className="auth-field__password">
              <input
                id="splunk-password"
                type={showPassword ? "text" : "password"}
                name="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
              <button
                type="button"
                className="auth-field__toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
              </button>
            </div>
          </div>
          {error && (
            <p className="auth-gate__error" role="alert">
              {error}
            </p>
          )}
          <button
            type="submit"
            className="btn btn-primary btn-block auth-gate__submit"
            disabled={loading || !username.trim() || !password}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}