import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import "./Dashboard.css";

const actions = [
  {
    title: "Self Anxiety Test",
    description: "A short anxiety check-in to understand your current stress level.",
    to: "/anxiety-test",
    duration: "2-4 min",
    cta: "Start Anxiety Test",
  },
  {
    title: "Depression Test",
    description: "A guided mood screening based on common research assessment items.",
    to: "/depression-test",
    duration: "3-5 min",
    cta: "Start Depression Test",
  },
  {
    title: "General Chat",
    description: "Talk freely about your day, feelings, or concerns in a supportive space.",
    to: "/general-chat",
    duration: "Always available",
    cta: "Open Chat",
  },
];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initials = useMemo(() => {
    const name = user?.name?.trim();
    if (name) {
      return name
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("");
    }
    return user?.email?.slice(0, 2).toUpperCase() || "U";
  }, [user?.name, user?.email]);

  const firstName = useMemo(() => {
    const name = user?.name?.trim();
    return name ? name.split(" ")[0] : "there";
  }, [user?.name]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <h1>Hello, {firstName}</h1>
            <p>What would you like to do right now?</p>
          </div>
          <button onClick={handleLogout} className="logout-btn">
            Log out
          </button>
        </header>

        <p className="dashboard-tip">
          Recommended first step: If you are unsure, start with <strong>General Chat</strong>.
        </p>

        <div className="dashboard-layout">
          <section className="actions-panel" aria-label="Primary actions">
            {actions.map((item) => (
              <Link key={item.to} to={item.to} className="action-card">
                <p className="action-time">{item.duration}</p>
                <h2>{item.title}</h2>
                <p className="action-desc">{item.description}</p>
                <span className="action-btn">{item.cta}</span>
              </Link>
            ))}
          </section>

          <aside className="profile-panel" aria-label="Profile">
            <h2>Profile</h2>
            <div className="avatar">{initials}</div>
            <InfoRow label="Name" value={user?.name || "Not set"} />
            <InfoRow label="Email" value={user?.email || "-"} />
            <InfoRow label="User ID" value={user?.user_id || "-"} mono />
          </aside>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }) {
  return (
    <div className="info-row">
      <span className="info-label">{label}</span>
      <span className={mono ? "info-value mono" : "info-value"}>{value}</span>
    </div>
  );
}
