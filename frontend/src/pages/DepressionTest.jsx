import { Link } from "react-router-dom";

export default function DepressionTest() {
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <p style={styles.eyebrow}>Assessment</p>
        <h1 style={styles.title}>Depression Test</h1>
        <p style={styles.text}>
          This page is ready for your PHQ-9 style flow. You can plug your question set here and
          keep scoring logic in one clean utility file.
        </p>

        <div style={styles.grid}>
          <Box title="Format">9 short prompts</Box>
          <Box title="Scale">Not at all to nearly every day</Box>
          <Box title="Output">Score + severity band</Box>
        </div>

        <Link to="/dashboard" style={styles.button}>
          Back to Home
        </Link>
      </div>
    </div>
  );
}

function Box({ title, children }) {
  return (
    <div style={styles.box}>
      <h3 style={styles.boxTitle}>{title}</h3>
      <p style={styles.boxText}>{children}</p>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100dvh",
    display: "grid",
    placeItems: "center",
    padding: 16,
    background: "linear-gradient(160deg, #f3f8ff 0%, #f4f2ff 100%)",
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    width: "100%",
    maxWidth: 720,
    background: "#fff",
    border: "1px solid #dddff7",
    borderRadius: 20,
    padding: 26,
    boxShadow: "0 14px 40px rgba(34, 28, 75, 0.12)",
  },
  eyebrow: {
    margin: 0,
    color: "#4c4ea7",
    fontSize: 13,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  title: {
    margin: "6px 0 12px",
    color: "#262869",
    fontSize: 32,
  },
  text: {
    margin: 0,
    color: "#4c5088",
    lineHeight: 1.6,
  },
  grid: {
    marginTop: 20,
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 10,
  },
  box: {
    border: "1px solid #e2e4fb",
    borderRadius: 10,
    padding: 12,
    background: "#f9f9ff",
  },
  boxTitle: {
    margin: 0,
    fontSize: 14,
    color: "#2f3377",
  },
  boxText: {
    margin: "4px 0 0",
    fontSize: 13,
    color: "#505593",
  },
  button: {
    display: "inline-block",
    marginTop: 20,
    padding: "10px 14px",
    borderRadius: 10,
    textDecoration: "none",
    background: "#4043a8",
    color: "#fff",
    fontWeight: 600,
  },
};
