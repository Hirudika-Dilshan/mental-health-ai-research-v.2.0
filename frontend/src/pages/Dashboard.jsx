import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import "./Dashboard.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
  const [results, setResults] = useState([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState("");
  const [profileView, setProfileView] = useState("profile");

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

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!user?.user_id) return;
      setResultsLoading(true);
      setResultsError("");
      try {
        const res = await fetch(
          `${API_URL}/dashboard/results?user_id=${encodeURIComponent(user.user_id)}`,
        );
        const data = await res.json();
        if (cancelled) return;
        if (res.ok && Array.isArray(data.results)) {
          setResults(data.results);
        } else {
          setResults([]);
          setResultsError(data?.detail || "Could not load result timeline.");
        }
      } catch {
        if (cancelled) return;
        setResults([]);
        setResultsError("Network error while loading result timeline.");
      } finally {
        if (!cancelled) setResultsLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [user?.user_id]);

  const latestAnxiety = useMemo(
    () => results.find((r) => r.test_type === "anxiety" && r.status === "completed") || null,
    [results],
  );
  const latestDepression = useMemo(
    () => results.find((r) => r.test_type === "depression" && r.status === "completed") || null,
    [results],
  );
  const metrics = useMemo(() => {
    const total = results.length;
    const completedItems = results.filter((item) => item.status === "completed");
    const completed = completedItems.length;
    const crisisTerminated = results.filter((item) => item.status === "crisis_terminated").length;
    const last30DaysCutoff = Date.now() - (30 * 24 * 60 * 60 * 1000);
    const last30Days = results.filter((item) => toTimestamp(item.assessed_at) >= last30DaysCutoff).length;
    const anxietyScores = completedItems.filter((item) => item.test_type === "anxiety");
    const depressionScores = completedItems.filter((item) => item.test_type === "depression");

    return {
      total,
      completionRate: total > 0 ? Math.round((completed / total) * 100) : null,
      crisisTerminated,
      last30Days,
      avgAnxiety: computeAverageScore(anxietyScores),
      avgDepression: computeAverageScore(depressionScores),
    };
  }, [results]);

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

          <aside className="side-stack">
            <article className="howto-panel" aria-label="How to use">
              <h2>How To Use</h2>
              <ol>
                <li>Start with General Chat if you are unsure where to begin.</li>
                <li>Use Anxiety or Depression tests for structured screening.</li>
                <li>Answer each question honestly for better trend tracking.</li>
                <li>Use New Chat to begin a fresh session at any time.</li>
              </ol>
              <p className="howto-note">
                This system is a screening support tool and not a diagnosis.
              </p>
            </article>

            <article className="profile-panel profile-clickable" aria-label="Profile and results">
              <div className="profile-top">
                <h2>{profileView === "profile" ? "Profile" : "Results Over Time"}</h2>
                <div className="profile-tabs">
                  <button
                    type="button"
                    className={profileView === "profile" ? "tab active" : "tab"}
                    onClick={() => setProfileView("profile")}
                  >
                    Profile
                  </button>
                  <button
                    type="button"
                    className={profileView === "results" ? "tab active" : "tab"}
                    onClick={() => setProfileView("results")}
                  >
                    Results
                  </button>
                </div>
              </div>

              {profileView === "profile" ? (
                <>
                  <div className="avatar">{initials}</div>
                  <InfoRow label="Name" value={user?.name || "Not set"} />
                  <InfoRow label="Email" value={user?.email || "-"} />
                  <InfoRow label="User ID" value={user?.user_id || "-"} mono />
                </>
              ) : (
                <div className="profile-results">
                  <div className="timeline-header">
                    <span>{results.length} records</span>
                  </div>
                  <div className="result-glance">
                    <ResultChip label="Latest Anxiety" item={latestAnxiety} />
                    <ResultChip label="Latest Depression" item={latestDepression} />
                  </div>
                  <div className="research-metrics" aria-label="Research snapshot">
                    <MetricCard
                      label="Total Sessions"
                      value={metrics.total}
                      hint="All recorded outcomes"
                    />
                    <MetricCard
                      label="Completion Rate"
                      value={metrics.completionRate === null ? "-" : `${metrics.completionRate}%`}
                      hint="Completed / all outcomes"
                    />
                    <MetricCard
                      label="Crisis Terminations"
                      value={metrics.crisisTerminated}
                      hint="Sessions ended for safety"
                    />
                    <MetricCard
                      label="Last 30 Days"
                      value={metrics.last30Days}
                      hint="Recent recorded outcomes"
                    />
                    <MetricCard
                      label="Avg Anxiety Score"
                      value={metrics.avgAnxiety ?? "-"}
                      hint="Completed anxiety sessions"
                    />
                    <MetricCard
                      label="Avg Depression Score"
                      value={metrics.avgDepression ?? "-"}
                      hint="Completed depression sessions"
                    />
                  </div>

                  {resultsLoading && <p className="timeline-msg">Loading timeline...</p>}
                  {!resultsLoading && resultsError && <p className="timeline-msg error">{resultsError}</p>}
                  {!resultsLoading && !resultsError && results.length === 0 && (
                    <p className="timeline-msg">No completed results yet. Start a test to build your timeline.</p>
                  )}

                  {!resultsLoading && !resultsError && results.length > 0 && (
                    <div className="timeline-list compact">
                      {results.slice(0, 20).map((item, idx) => (
                        <div key={`${item.test_type}-${item.assessed_at}-${idx}`} className="timeline-item">
                          <div className="timeline-item-head">
                            <span className={item.test_type === "anxiety" ? "pill anxiety" : "pill depression"}>
                              {item.test_type === "anxiety" ? "Anxiety" : "Depression"}
                            </span>
                            <span className="timeline-date">{formatDate(item.assessed_at)}</span>
                          </div>
                          <div className="timeline-item-body">
                            <span className={item.status === "completed" ? "status good" : "status warn"}>
                              {item.status === "completed" ? "Completed" : "Crisis Terminated"}
                            </span>
                            <span className="score">
                              {item.total_score === null || item.total_score === undefined
                                ? "No score"
                                : `Score: ${item.total_score}`}
                            </span>
                            <span className="level">{item.level || "-"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </article>
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

function ResultChip({ label, item }) {
  return (
    <div className="result-chip">
      <span>{label}</span>
      <strong>{item ? `${item.total_score ?? "-"} (${item.level || "-"})` : "No data"}</strong>
    </div>
  );
}

function MetricCard({ label, value, hint }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{hint}</p>
    </div>
  );
}

function computeAverageScore(items) {
  const values = items
    .map((item) => item.total_score)
    .filter((score) => Number.isFinite(score));

  if (values.length === 0) return null;
  const avg = values.reduce((sum, score) => sum + score, 0) / values.length;
  return Number(avg.toFixed(1));
}

function toTimestamp(value) {
  const ts = Date.parse(value);
  return Number.isFinite(ts) ? ts : 0;
}

function formatDate(value) {
  try {
    const dt = new Date(value);
    return dt.toLocaleString();
  } catch {
    return value;
  }
}
