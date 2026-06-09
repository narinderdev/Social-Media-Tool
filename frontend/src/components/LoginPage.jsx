import { useState } from "react";
import { AlertCircle, Eye, EyeOff, LayoutDashboard, Loader2 } from "lucide-react";

import { APP_NAME } from "../constants";

function LoginPage({ onLogin, onToast }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submitLogin = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await onLogin({ email, password });
    } catch (loginError) {
      setError(loginError.message);
      onToast?.(loginError.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submitLogin}>
        <div>
          <img className="brand-logo large" src="/logo.png" alt="" />
          <p className="eyebrow">{APP_NAME}</p>
          <h1>Admin Login</h1>
        </div>

        {error && (
          <section className="alert compact-alert">
            <AlertCircle size={18} />
            <p>{error}</p>
          </section>
        )}

        <label className="field-label" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          className="text-input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Enter admin email"
          autoComplete="username"
          required
        />

        <label className="field-label" htmlFor="password">
          Password
        </label>
        <div className="password-field">
          <input
            id="password"
            className="text-input"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <button className="submit-button" type="submit" disabled={submitting}>
          {submitting ? <Loader2 className="spin" size={18} /> : <LayoutDashboard size={18} />}
          Login
        </button>
      </form>
    </main>
  );
}

export default LoginPage;
