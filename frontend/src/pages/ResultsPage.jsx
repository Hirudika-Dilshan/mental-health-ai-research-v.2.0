import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import "./ResultsPage.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const ANXIETY_MAX_SCORE = 21;
const DEPRESSION_MAX_SCORE = 27;

export default function ResultsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      if (!user?.user_id) return;
      setLoading(true);
      setError("");
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
          setError(data?.detail || "Could not load results.");
        }
      } catch {
        if (cancelled) return;
        setResults([]);
        setError("Network error while loading results.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [user?.user_id]);

  const completedResults = useMemo(
    () => results
      .filter((item) => item.status === "completed" && Number.isFinite(item.total_score))
      .slice()
      .sort((a, b) => toTimestamp(a.assessed_at) - toTimestamp(b.assessed_at)),
    [results],
  );

  const anxietyTrend = useMemo(
    () => completedResults.filter((item) => item.test_type === "anxiety"),
    [completedResults],
  );

  const depressionTrend = useMemo(
    () => completedResults.filter((item) => item.test_type === "depression"),
    [completedResults],
  );

  const metrics = useMemo(() => {
    const total = results.length;
    const completed = results.filter((item) => item.status === "completed").length;
    const crisisTerminated = results.filter((item) => item.status === "crisis_terminated").length;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : null;
    return {
      total,
      completed,
      crisisTerminated,
      completionRate,
      anxietyAvg: averageScore(anxietyTrend),
      depressionAvg: averageScore(depressionTrend),
    };
  }, [results, anxietyTrend, depressionTrend]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="results-page">
      <div className="results-shell">
        <header className="results-header">
          <div>
            <p className="results-kicker">Research Analytics</p>
            <h1>Results Over Time</h1>
            <p className="results-subtitle">
              Score trend lines by date. X-axis is assessment time, Y-axis is test score.
            </p>
          </div>
          <div className="results-header-actions">
            <Link to="/dashboard" className="ghost-btn">Back to Dashboard</Link>
            <button type="button" onClick={handleLogout} className="ghost-btn">
              Log out
            </button>
          </div>
        </header>

        <section className="results-metrics" aria-label="Summary metrics">
          <MetricCard label="Total Outcomes" value={metrics.total} />
          <MetricCard label="Completed" value={metrics.completed} />
          <MetricCard
            label="Completion Rate"
            value={metrics.completionRate === null ? "-" : `${metrics.completionRate}%`}
          />
          <MetricCard label="Crisis Terminated" value={metrics.crisisTerminated} />
          <MetricCard label="Avg Anxiety Score" value={metrics.anxietyAvg ?? "-"} />
          <MetricCard label="Avg Depression Score" value={metrics.depressionAvg ?? "-"} />
        </section>

        {loading && <p className="results-message">Loading results...</p>}
        {!loading && error && <p className="results-message error">{error}</p>}
        {!loading && !error && (
          <section className="charts-grid" aria-label="Trend charts">
            <TrendChart
              title="Anxiety Trend (GAD-7)"
              points={anxietyTrend}
              maxScore={ANXIETY_MAX_SCORE}
              color="#0f5bc5"
              emptyMessage="No completed anxiety scores yet."
            />
            <TrendChart
              title="Depression Trend (PHQ-9)"
              points={depressionTrend}
              maxScore={DEPRESSION_MAX_SCORE}
              color="#2a8f7b"
              emptyMessage="No completed depression scores yet."
            />
          </section>
        )}

        {!loading && !error && (
          <section className="timeline-section" aria-label="Result timeline">
            <h2>Detailed Timeline</h2>
            {results.length === 0 ? (
              <p className="results-message">No outcomes recorded yet.</p>
            ) : (
              <div className="timeline-table-wrap">
                <table className="timeline-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Test</th>
                      <th>Status</th>
                      <th>Score</th>
                      <th>Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((item, idx) => (
                      <tr key={`${item.test_type}-${item.assessed_at}-${idx}`}>
                        <td>{formatDate(item.assessed_at)}</td>
                        <td>{item.test_type === "anxiety" ? "Anxiety" : "Depression"}</td>
                        <td>
                          <span className={item.status === "completed" ? "table-badge good" : "table-badge warn"}>
                            {item.status === "completed" ? "Completed" : "Crisis Terminated"}
                          </span>
                        </td>
                        <td>{item.total_score ?? "-"}</td>
                        <td>{item.level || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <article className="metric-tile">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function TrendChart({
  title,
  points,
  maxScore,
  color,
  emptyMessage,
}) {
  const width = 760;
  const height = 260;
  const pad = { top: 20, right: 18, bottom: 40, left: 42 };
  const innerWidth = width - pad.left - pad.right;
  const innerHeight = height - pad.top - pad.bottom;
  const plotted = points.map((item) => ({
    t: toTimestamp(item.assessed_at),
    score: Number(item.total_score),
    dateLabel: formatDate(item.assessed_at),
  }));

  if (plotted.length === 0) {
    return (
      <article className="chart-card">
        <h2>{title}</h2>
        <p className="results-message">{emptyMessage}</p>
      </article>
    );
  }

  const minT = plotted[0].t;
  const maxT = plotted[plotted.length - 1].t;
  const safeMaxT = maxT > minT ? maxT : minT + 1;

  const xAt = (t) => pad.left + ((t - minT) / (safeMaxT - minT)) * innerWidth;
  const yAt = (v) => pad.top + ((maxScore - v) / maxScore) * innerHeight;

  const pathData = plotted
    .map((item, idx) => `${idx === 0 ? "M" : "L"} ${xAt(item.t).toFixed(2)} ${yAt(item.score).toFixed(2)}`)
    .join(" ");

  const yTicks = [0, Math.round(maxScore * 0.25), Math.round(maxScore * 0.5), Math.round(maxScore * 0.75), maxScore];
  const xTicks = [minT, minT + (safeMaxT - minT) / 2, safeMaxT];

  return (
    <article className="chart-card">
      <h2>{title}</h2>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {yTicks.map((tick) => (
          <g key={`y-${tick}`}>
            <line
              x1={pad.left}
              y1={yAt(tick)}
              x2={width - pad.right}
              y2={yAt(tick)}
              className="grid-line"
            />
            <text x={pad.left - 8} y={yAt(tick) + 4} textAnchor="end" className="axis-text">
              {tick}
            </text>
          </g>
        ))}

        <line
          x1={pad.left}
          y1={height - pad.bottom}
          x2={width - pad.right}
          y2={height - pad.bottom}
          className="axis-line"
        />

        <line
          x1={pad.left}
          y1={pad.top}
          x2={pad.left}
          y2={height - pad.bottom}
          className="axis-line"
        />

        {xTicks.map((tick, idx) => (
          <text
            key={`x-${idx}`}
            x={xAt(tick)}
            y={height - 14}
            textAnchor={idx === 0 ? "start" : idx === xTicks.length - 1 ? "end" : "middle"}
            className="axis-text"
          >
            {shortDate(tick)}
          </text>
        ))}

        <path d={pathData} fill="none" stroke={color} strokeWidth="3" />

        {plotted.map((item, idx) => (
          <circle
            key={`${item.t}-${item.score}-${idx}`}
            cx={xAt(item.t)}
            cy={yAt(item.score)}
            r="4.5"
            fill={color}
          >
            <title>{`${item.dateLabel}: ${item.score}`}</title>
          </circle>
        ))}
      </svg>
    </article>
  );
}

function averageScore(items) {
  if (items.length === 0) return null;
  const sum = items.reduce((acc, item) => acc + Number(item.total_score || 0), 0);
  return Number((sum / items.length).toFixed(1));
}

function toTimestamp(value) {
  const ts = Date.parse(value);
  return Number.isFinite(ts) ? ts : 0;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function shortDate(timestamp) {
  try {
    return new Date(timestamp).toLocaleDateString();
  } catch {
    return "";
  }
}
