import { FormEvent, useState } from "react";

type Props = {
  onSubmit: (email: string, password: string, mode: "signin" | "signup") => Promise<void>;
};

export function AuthView({ onSubmit }: Props) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onSubmit(email.trim(), password, mode);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "We couldn't authenticate you.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">LOCAL WORKSPACE RAG</p>
        <h1>{mode === "signin" ? "Sign in" : "Create an account"}</h1>
        <p className="muted">Your data and conversations stay on this machine.</p>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={1} autoComplete={mode === "signin" ? "current-password" : "new-password"} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={loading}>{loading ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}</button>
        <button type="button" className="text-button" onClick={() => setMode(mode === "signin" ? "signup" : "signin")}>
          {mode === "signin" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </button>
      </form>
    </main>
  );
}
