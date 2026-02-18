// frontend/src/pages/Login.jsx

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login() {
  const { login }      = useAuth();
  const navigate       = useNavigate();

  const [form, setForm]       = useState({ email: "", password: "" });
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!form.email || !form.password) {
      setError("Email and password are required.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/login`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: form.email, password: form.password }),
      });

      const data = await res.json();

      if (!res.ok) {
        // 401 → wrong credentials, 422 → validation error
        setError(data.detail || "Login failed. Please try again.");
        return;
      }

      // Save user to global context + sessionStorage
      login(data);

      // Redirect to dashboard (or wherever you want)
      navigate("/dashboard");
    } catch {
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Welcome back</h1>

        <form onSubmit={handleSubmit} style={styles.form}>
          {/* Email */}
          <label style={styles.label}>Email</label>
          <input
            style={styles.input}
            type="email"
            name="email"
            placeholder="jane@example.com"
            value={form.email}
            onChange={handleChange}
            autoComplete="email"
            required
          />

          {/* Password */}
          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            name="password"
            placeholder="Your password"
            value={form.password}
            onChange={handleChange}
            autoComplete="current-password"
            required
          />

          {/* Error */}
          {error && <p style={styles.error}>{error}</p>}

          {/* Submit */}
          <button
            type="submit"
            style={{
              ...styles.button,
              opacity: loading ? 0.7 : 1,
              cursor:  loading ? "not-allowed" : "pointer",
            }}
            disabled={loading}
          >
            {loading ? "Signing in…" : "Log In"}
          </button>
        </form>

        <p style={styles.footer}>
          Don't have an account?{" "}
          <a href="/signup" style={styles.link}>Sign up</a>
        </p>
      </div>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────
const styles = {
  wrapper: {
    minHeight:      "100vh",
    display:        "flex",
    alignItems:     "center",
    justifyContent: "center",
    background:     "#f1f5f9",
    fontFamily:     "system-ui, sans-serif",
  },
  card: {
    background:   "#ffffff",
    borderRadius: 16,
    padding:      "40px 36px",
    width:        "100%",
    maxWidth:     420,
    boxShadow:    "0 4px 24px rgba(0,0,0,0.08)",
  },
  title: {
    margin:     "0 0 28px",
    fontSize:   24,
    fontWeight: 700,
    color:      "#0f172a",
  },
  form: {
    display:       "flex",
    flexDirection: "column",
    gap:           6,
  },
  label: {
    fontSize:     14,
    fontWeight:   600,
    color:        "#334155",
    marginTop:    12,
    marginBottom: 4,
  },
  input: {
    padding:      "10px 14px",
    borderRadius: 8,
    border:       "1.5px solid #e2e8f0",
    fontSize:     15,
    outline:      "none",
    color:        "#0f172a",
  },
  button: {
    marginTop:    20,
    padding:      "12px",
    borderRadius: 8,
    border:       "none",
    background:   "#6366f1",
    color:        "#fff",
    fontSize:     16,
    fontWeight:   600,
  },
  error: {
    marginTop:    8,
    padding:      "10px 14px",
    background:   "#fef2f2",
    border:       "1px solid #fecaca",
    borderRadius: 8,
    color:        "#dc2626",
    fontSize:     14,
  },
  footer: {
    marginTop: 20,
    textAlign: "center",
    fontSize:  14,
    color:     "#64748b",
  },
  link: {
    color:          "#6366f1",
    textDecoration: "none",
    fontWeight:     600,
  },
};
