// frontend/src/pages/Dashboard.jsx
// Protected page — only accessible when logged in

import { useAuth } from "../context/useAuth";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <h1 style={styles.title}>
              👋 Hello, {user?.name || user?.email}!
            </h1>
            <p style={styles.subtitle}>You're successfully logged in.</p>
          </div>
          <button onClick={handleLogout} style={styles.logoutBtn}>
            Log out
          </button>
        </div>

        {/* User info */}
        <div style={styles.infoBox}>
          <InfoRow label="Email"   value={user?.email} />
          <InfoRow label="Name"    value={user?.name || "—"} />
          <InfoRow label="User ID" value={user?.user_id} mono />
        </div>

        <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 20 }}>
          Your access token is stored in sessionStorage and will be cleared when you close the tab.
        </p>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }) {
  return (
    <div style={styles.infoRow}>
      <span style={styles.infoLabel}>{label}</span>
      <span style={{ ...styles.infoValue, fontFamily: mono ? "monospace" : "inherit", fontSize: mono ? 12 : 14 }}>
        {value}
      </span>
    </div>
  );
}

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
    maxWidth:     520,
    boxShadow:    "0 4px 24px rgba(0,0,0,0.08)",
  },
  header: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "flex-start",
    marginBottom:   28,
  },
  title: {
    margin:     0,
    fontSize:   22,
    fontWeight: 700,
    color:      "#0f172a",
  },
  subtitle: {
    margin:   "4px 0 0",
    fontSize: 14,
    color:    "#64748b",
  },
  logoutBtn: {
    padding:      "8px 16px",
    borderRadius: 8,
    border:       "1.5px solid #e2e8f0",
    background:   "#fff",
    color:        "#64748b",
    fontSize:     14,
    fontWeight:   600,
    cursor:       "pointer",
  },
  infoBox: {
    background:   "#f8fafc",
    borderRadius: 12,
    padding:      "16px 20px",
    display:      "flex",
    flexDirection: "column",
    gap:          12,
  },
  infoRow: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
  },
  infoLabel: {
    fontSize:   13,
    fontWeight: 600,
    color:      "#64748b",
    minWidth:   70,
  },
  infoValue: {
    color:     "#0f172a",
    wordBreak: "break-all",
    textAlign: "right",
  },
};
