import { Link } from "react-router-dom";

export default function AnxietyTest() {
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <p style={styles.eyebrow}>Assessment</p>
        <h1 style={styles.title}>Self Anxiety Test</h1>
        <p style={styles.text}>
          This page is ready for your GAD-7 style conversational flow. Keep this simple for now:
          present one question at a time and compute a score at the end.
        </p>

        <div style={styles.list}>
          <Step text="Question flow container" />
          <Step text="Answer scale (0-3)" />
          <Step text="Final score and severity label" />
        </div>

        <Link to="/dashboard" style={styles.button}>
          Back to Home
        </Link>
      </div>
    </div>
  );
}

function Step({ text }) {
  return <div style={styles.step}>{text}</div>;
}

const styles = {
  page: {
    minHeight: "100dvh",
    display: "grid",
    placeItems: "center",
    padding: 16,
    background: "linear-gradient(160deg, #edf7ff 0%, #f2fcf3 100%)",
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    width: "100%",
    maxWidth: 720,
    background: "#fff",
    border: "1px solid #dce9f8",
    borderRadius: 20,
    padding: 26,
    boxShadow: "0 14px 40px rgba(15, 42, 74, 0.12)",
  },
  eyebrow: {
    margin: 0,
    color: "#2d628d",
    fontSize: 13,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  title: {
    margin: "6px 0 12px",
    color: "#0e2d52",
    fontSize: 32,
  },
  text: {
    margin: 0,
    color: "#496785",
    lineHeight: 1.6,
  },
  list: {
    marginTop: 20,
    display: "grid",
    gap: 10,
  },
  step: {
    border: "1px solid #dde8f8",
    background: "#f8fbff",
    borderRadius: 10,
    padding: "10px 12px",
    color: "#28486e",
    fontSize: 14,
  },
  button: {
    display: "inline-block",
    marginTop: 20,
    padding: "10px 14px",
    borderRadius: 10,
    textDecoration: "none",
    background: "#0d63c9",
    color: "#fff",
    fontWeight: 600,
  },
};
