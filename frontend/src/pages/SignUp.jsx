import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function extractErrorMessage(data, status) {
  const duplicateEmailMessage = "This email is already registered. Try logging in instead.";

  const isDuplicateEmailText = (text) => {
    if (!text) return false;
    const value = String(text).toLowerCase();
    return (
      value.includes("email_exists") ||
      (value.includes("already") && value.includes("registered")) ||
      (value.includes("already") && value.includes("exist")) ||
      (value.includes("already") && value.includes("use")) ||
      value.includes("duplicate key value")
    );
  };

  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
    if (field === "email") return "Please enter a valid email address.";
    if (field === "password") return "Password must be at least 6 characters.";
    return first?.msg || "Please check your input and try again.";
  }

  if (typeof data?.detail === "string" && data.detail.trim()) {
    if (isDuplicateEmailText(data.detail)) return duplicateEmailMessage;
    return data.detail;
  }

  const rawMessage = [
    data?.msg,
    data?.message,
    data?.error_description,
    data?.error?.message,
    data?.error,
  ]
    .filter(Boolean)
    .join(" ");
  if (isDuplicateEmailText(rawMessage)) return duplicateEmailMessage;

  if (status === 409) return duplicateEmailMessage;
  if (status === 422) return "Invalid email or password format.";
  if (status === 400) return "Please check your details and try again.";
  if (status === 401) return "You are not authorized to perform this action.";
  if (status === 403) return "Access denied. Please try again later.";
  if (status === 404) return "Service not found. Check backend API URL.";
  if (status === 408) return "Request timed out. Please try again.";
  if (status === 429) return "Too many attempts. Please wait and try again.";
  if (status >= 500) return "Server error while creating account. Please try again.";

  return "Registration failed. Please try again.";
}

export default function SignUp() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [error, setError] = useState(null);
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
    if (form.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          name: form.name || null,
        }),
      });

      let data = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }

      if (!res.ok) {
        setError(extractErrorMessage(data, res.status));
        return;
      }

      navigate("/login", { replace: true });
    } catch {
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create Account</h1>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Name <span style={{ color: "#94a3b8", fontSize: 13 }}>(optional)</span>
          </label>
          <input
            style={styles.input}
            type="text"
            name="name"
            placeholder="Jane Doe"
            value={form.name}
            onChange={handleChange}
            autoComplete="name"
          />

          <label style={styles.label}>Email *</label>
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

          <label style={styles.label}>Password *</label>
          <input
            style={styles.input}
            type="password"
            name="password"
            placeholder="Min. 6 characters"
            value={form.password}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />

          {error && <p style={styles.error}>{error}</p>}

          <button
            type="submit"
            style={{
              ...styles.button,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
            disabled={loading}
          >
            {loading ? "Creating account..." : "Sign Up"}
          </button>
        </form>

        <p style={styles.footer}>
          Already have an account? <a href="/login" style={styles.link}>Log in</a>
        </p>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100dvh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f1f5f9",
    fontFamily: "system-ui, sans-serif",
    padding: "16px",
  },
  card: {
    background: "#ffffff",
    borderRadius: 16,
    padding: "40px 36px",
    width: "100%",
    maxWidth: 420,
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    boxSizing: "border-box",
  },
  title: {
    margin: "0 0 28px",
    fontSize: 24,
    fontWeight: 700,
    color: "#0f172a",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  label: {
    fontSize: 14,
    fontWeight: 600,
    color: "#334155",
    marginTop: 12,
    marginBottom: 4,
  },
  input: {
    padding: "10px 14px",
    borderRadius: 8,
    border: "1.5px solid #e2e8f0",
    fontSize: 15,
    outline: "none",
    transition: "border-color 0.2s",
    color: "#0f172a",
  },
  button: {
    marginTop: 20,
    padding: "12px",
    borderRadius: 8,
    border: "none",
    background: "#6366f1",
    color: "#fff",
    fontSize: 16,
    fontWeight: 600,
    transition: "opacity 0.2s",
  },
  error: {
    marginTop: 8,
    padding: "10px 14px",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    color: "#dc2626",
    fontSize: 14,
  },
  footer: {
    marginTop: 20,
    textAlign: "center",
    fontSize: 14,
    color: "#64748b",
  },
  link: {
    color: "#6366f1",
    textDecoration: "none",
    fontWeight: 600,
  },
};
