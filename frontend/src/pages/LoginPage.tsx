import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, login } from "../api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? err.message
          : "Nepodařilo se přihlásit. Zkontrolujte e-mail a heslo (ADMIN_EMAIL / ADMIN_PASSWORD v .env).",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <h1>JobRadar AI</h1>
        <p className="muted">Přihlášení do vaší instance</p>
        <label>
          E-mail
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="username" required />
        </label>
        <label>
          Heslo
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" type="submit" disabled={busy}>{busy ? "Přihlašuji…" : "Přihlásit se"}</button>
      </form>
    </div>
  );
}
