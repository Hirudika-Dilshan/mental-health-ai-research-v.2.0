import { Link } from "react-router-dom";

export default function GeneralChat() {
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div>
            <p style={styles.eyebrow}>Conversation</p>
            <h1 style={styles.title}>General Chat</h1>
          </div>
          <Link to="/dashboard" style={styles.backButton}>
            Back
          </Link>
        </div>

        <div style={styles.chatBody}>
          <Bubble role="assistant">
            Hi. This is your general support chat area. Start with how your day has been.
          </Bubble>
          <Bubble role="user">I want to track my mood patterns this week.</Bubble>
          <Bubble role="assistant">
            Great. We can log daily mood, sleep quality, and stress level.
          </Bubble>
        </div>

        <div style={styles.inputRow}>
          <input
            style={styles.input}
            placeholder="Type a message..."
            disabled
            aria-label="chat input placeholder"
          />
          <button style={styles.sendBtn} disabled>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({ role, children }) {
  return <div style={role === "user" ? styles.userBubble : styles.assistantBubble}>{children}</div>;
}

const styles = {
  page: {
    minHeight: "100dvh",
    display: "grid",
    placeItems: "center",
    padding: 16,
    background: "linear-gradient(160deg, #eef8ff 0%, #effff7 100%)",
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    width: "100%",
    maxWidth: 760,
    borderRadius: 20,
    background: "#ffffff",
    border: "1px solid #d8ece6",
    boxShadow: "0 14px 40px rgba(16, 63, 70, 0.11)",
    padding: 20,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  eyebrow: {
    margin: 0,
    color: "#227077",
    fontSize: 13,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  title: {
    margin: "4px 0 0",
    color: "#12474b",
    fontSize: 30,
  },
  backButton: {
    textDecoration: "none",
    background: "#eaf7f5",
    color: "#1f6a71",
    border: "1px solid #c6e7e2",
    borderRadius: 10,
    padding: "8px 12px",
    fontSize: 14,
    fontWeight: 600,
  },
  chatBody: {
    border: "1px solid #def0eb",
    background: "#f8fffd",
    borderRadius: 14,
    padding: 12,
    minHeight: 280,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  assistantBubble: {
    maxWidth: "80%",
    alignSelf: "flex-start",
    background: "#eaf8f2",
    color: "#1a5e5f",
    border: "1px solid #cdeee3",
    borderRadius: 12,
    padding: "10px 12px",
    fontSize: 14,
  },
  userBubble: {
    maxWidth: "80%",
    alignSelf: "flex-end",
    background: "#dff0ff",
    color: "#245179",
    border: "1px solid #c9e3fa",
    borderRadius: 12,
    padding: "10px 12px",
    fontSize: 14,
  },
  inputRow: {
    marginTop: 12,
    display: "flex",
    gap: 10,
  },
  input: {
    flex: 1,
    borderRadius: 10,
    border: "1px solid #d5e8e3",
    background: "#f7fcfb",
    padding: "10px 12px",
  },
  sendBtn: {
    borderRadius: 10,
    border: "none",
    background: "#1c8d95",
    color: "#ffffff",
    fontWeight: 600,
    padding: "10px 14px",
  },
};
