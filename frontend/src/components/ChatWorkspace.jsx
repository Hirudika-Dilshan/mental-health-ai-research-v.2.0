import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/useAuth";

import "./ChatWorkspace.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const MODE_CONFIG = {
  general: {
    title: "General Chat",
    subtitle: "Open conversation mode",
    tag: "LLM",
    greeting:
      "Hi. I am here to chat. You can talk about your day, stress, goals, or anything on your mind.",
    systemPrompt:
      "You are a helpful and empathetic assistant for general conversation. Be clear, concise, and supportive.",
  },
  anxiety: {
    title: "Anxiety Test Chat",
    subtitle: "Guided protocol placeholder",
    tag: "Protocol",
    greeting:
      "Welcome to the anxiety test chat. This is a guided placeholder flow until the full protocol is implemented.",
    systemPrompt: "",
  },
  depression: {
    title: "Depression Test Chat",
    subtitle: "Guided protocol placeholder",
    tag: "Protocol",
    greeting:
      "Welcome to the depression test chat. This is a guided placeholder flow until the full protocol is implemented.",
    systemPrompt: "",
  },
};

const ANXIETY_QUESTIONS = [
  "Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
  "How often have you been unable to stop or control worrying?",
  "How often have you had trouble relaxing?",
];

const DEPRESSION_QUESTIONS = [
  "Over the last 2 weeks, how often have you had little interest or pleasure in doing things?",
  "How often have you felt down, depressed, or hopeless?",
  "How often have you had trouble sleeping or sleeping too much?",
];

export default function ChatWorkspace({ mode = "general" }) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.general;
  const { user } = useAuth();
  const [messages, setMessages] = useState([{ role: "assistant", content: config.greeting }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const protocolQuestionList = useMemo(() => {
    if (mode === "anxiety") return ANXIETY_QUESTIONS;
    if (mode === "depression") return DEPRESSION_QUESTIONS;
    return [];
  }, [mode]);

  useEffect(() => {
    const loadHistory = async () => {
      if (!user?.user_id) {
        setMessages([{ role: "assistant", content: config.greeting }]);
        setLoadingHistory(false);
        return;
      }

      setLoadingHistory(true);
      try {
        const res = await fetch(
          `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=${mode}`,
        );
        const data = await res.json();
        if (res.ok && Array.isArray(data.messages) && data.messages.length > 0) {
          const formatted = data.messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
          }));
          setMessages(formatted);
        } else {
          setMessages([{ role: "assistant", content: config.greeting }]);
        }
      } catch {
        setMessages([{ role: "assistant", content: config.greeting }]);
      } finally {
        setLoadingHistory(false);
      }
    };

    loadHistory();
  }, [user?.user_id, mode, config.greeting]);

  const persistMessage = async (msg) => {
    if (!user?.user_id) return;
    try {
      await fetch(`${API_URL}/chat/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          mode,
          role: msg.role,
          content: msg.content,
        }),
      });
    } catch {
      // Keep UI responsive even if persistence fails.
    }
  };

  const sendMessage = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    persistMessage(userMsg);

    if (mode === "general") {
      setLoading(true);
      try {
        const history = nextMessages
          .slice(0, -1)
          .slice(-12)
          .map((msg) => ({ role: msg.role, content: msg.content }));

        const res = await fetch(`${API_URL}/chat/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            system_prompt: config.systemPrompt,
            conversation_history: history,
            user_message: trimmed,
          }),
        });

        const data = await res.json();
        const assistantText = res.ok
          ? data.reply
          : data.detail || "Unable to get a response right now. Please try again.";
        const assistantMsg = { role: "assistant", content: assistantText };
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
      } catch {
        const assistantMsg = {
          role: "assistant",
          content: "Network error while contacting the backend. Check API server and VITE_API_URL.",
        };
        setMessages((prev) => [
          ...prev,
          assistantMsg,
        ]);
        persistMessage(assistantMsg);
      } finally {
        setLoading(false);
      }
      return;
    }

    const userTurnCount = nextMessages.filter((msg) => msg.role === "user").length;
    const index = userTurnCount - 1;

    let response = "Thanks. Your answer is noted.";
    if (index < protocolQuestionList.length) {
      response = protocolQuestionList[index];
    } else if (index === protocolQuestionList.length) {
      response =
        "Thanks for your responses. In the next stage, this chat will run full scoring and interpretation.";
    } else {
      response =
        "Protocol placeholder active. You can continue chatting, and we will attach full protocol logic in later stages.";
    }

    const assistantMsg = { role: "assistant", content: response };
    setMessages((prev) => [...prev, assistantMsg]);
    persistMessage(assistantMsg);
  };

  const clearChat = async () => {
    if (user?.user_id) {
      try {
        await fetch(
          `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=${mode}`,
          { method: "DELETE" },
        );
      } catch {
        // Ignore delete failures; reset current UI anyway.
      }
    }
    const reset = [{ role: "assistant", content: config.greeting }];
    setMessages(reset);
  };

  return (
    <div className="chat-page">
      <aside className="chat-side">
        <div className="side-brand">Mind Research</div>
        <Link to="/dashboard" className="side-link">
          Back to Home
        </Link>
        <button type="button" className="side-link side-btn" onClick={clearChat}>
          New Chat
        </button>
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <div>
            <h1>{config.title}</h1>
            <p>{config.subtitle}</p>
          </div>
          <span className="mode-tag">{config.tag}</span>
        </header>

        <div className="chat-messages">
          {loadingHistory && (
            <div className="msg assistant">
              <div className="msg-role">Assistant</div>
              <p>Loading previous chat...</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.role === "user" ? "msg user" : "msg assistant"}>
              <div className="msg-role">{msg.role === "user" ? "You" : "Assistant"}</div>
              <p>{msg.content}</p>
            </div>
          ))}
          {loading && (
            <div className="msg assistant">
              <div className="msg-role">Assistant</div>
              <p>Thinking...</p>
            </div>
          )}
        </div>

        <form className="chat-input-row" onSubmit={sendMessage}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            aria-label="Type message"
          />
          <button type="submit" disabled={loading}>
            Send
          </button>
        </form>
      </section>
    </div>
  );
}
