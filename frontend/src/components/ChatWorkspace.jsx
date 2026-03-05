import { useEffect, useRef, useState } from "react";
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
    subtitle: "GAD-7 guided protocol",
    tag: "Protocol",
    greeting: "Before we begin, are you 18 or older? (Yes/No)",
    systemPrompt: "",
  },
  depression: {
    title: "Depression Test Chat",
    subtitle: "PHQ-9 guided protocol",
    tag: "Protocol",
    greeting: "Before we begin, are you 18 or older? (Yes/No)",
    systemPrompt: "",
  },
};

function createConversationId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `conv-${Date.now()}`;
}

export default function ChatWorkspace({ mode = "general" }) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.general;
  const { user } = useAuth();
  const [messages, setMessages] = useState([{ role: "assistant", content: config.greeting }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [draftConversationIds, setDraftConversationIds] = useState([]);
  const [deletingConversationId, setDeletingConversationId] = useState("");
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [openMenuConversationId, setOpenMenuConversationId] = useState("");
  const [anxietyAwaitingFrequency, setAnxietyAwaitingFrequency] = useState(false);
  const [anxietySessionLocked, setAnxietySessionLocked] = useState(false);
  const [anxietyLockNotice, setAnxietyLockNotice] = useState("");
  const [depressionAwaitingFrequency, setDepressionAwaitingFrequency] = useState(false);
  const [depressionSessionLocked, setDepressionSessionLocked] = useState(false);
  const [depressionLockNotice, setDepressionLockNotice] = useState("");
  const [showAnxietyOnboarding, setShowAnxietyOnboarding] = useState(false);
  const [showDepressionOnboarding, setShowDepressionOnboarding] = useState(false);
  const [anxietyIntake, setAnxietyIntake] = useState({
    age_18_plus: "yes",
    in_crisis: "no",
    consent: "yes",
  });
  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const menuWrapRefs = useRef({});
  const skipNextHistoryReloadRef = useRef("");

  const isGeneralMode = mode === "general";
  const conversationId = isGeneralMode ? activeConversationId : "default";
  const isDraftConversation =
    isGeneralMode && conversationId ? draftConversationIds.includes(conversationId) : false;

  const inferAnxietyLockNotice = (terminalReason, completed) => {
    if (terminalReason === "crisis") {
      return "Session terminated for safety. No score result is shown. Please use the crisis resources above.";
    }
    if (terminalReason === "withdrawn" || terminalReason === "excluded") {
      return "Session ended without a score result. Click New Chat to start a fresh session.";
    }
    if (completed) {
      return "Session completed. Click New Chat to start a fresh session.";
    }
    return "";
  };

  const inferTerminalReasonFromText = (text) => {
    const value = (text || "").toLowerCase();
    if (value.includes("serious distress") || value.includes("not a crisis counselor")) {
      return "crisis";
    }
    if (value.includes("only for adults (18+)")) return "excluded";
    if (value.includes("we can stop here")) return "withdrawn";
    if (value.includes("thank you for completing the gad-7 screening")) return "completed";
    if (value.includes("thank you for completing the phq-9 screening")) return "completed";
    return "";
  };

  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      if (!user?.user_id) {
        if (!cancelled) {
          setMessages([{ role: "assistant", content: config.greeting }]);
          setLoadingHistory(false);
        }
        return;
      }

        if (!isGeneralMode) {
          if (!cancelled) {
            setActiveConversationId("default");
            setAnxietyAwaitingFrequency(false);
            setAnxietySessionLocked(false);
            setAnxietyLockNotice("");
            setDepressionAwaitingFrequency(false);
            setDepressionSessionLocked(false);
            setDepressionLockNotice("");
            if (mode === "anxiety") {
              setShowAnxietyOnboarding(true);
              setShowDepressionOnboarding(false);
            } else if (mode === "depression") {
              setShowDepressionOnboarding(true);
              setShowAnxietyOnboarding(false);
            }
          }
          return;
        }

      const draftId = createConversationId();
      if (!cancelled) {
        setActiveConversationId(draftId);
        setMessages([{ role: "assistant", content: config.greeting }]);
        setConversations([{ conversation_id: draftId, title: "New chat", updated_at: "" }]);
        setDraftConversationIds([draftId]);
        setLoadingHistory(false);
        setHistoryError("");
        setConversationsLoading(true);
      }

      try {
        const res = await fetch(
          `${API_URL}/chat/conversations?user_id=${encodeURIComponent(user.user_id)}&mode=general`,
        );
        const data = await res.json();
        if (cancelled) return;
        if (res.ok && Array.isArray(data.conversations) && data.conversations.length > 0) {
          setConversations((prev) => {
            const existingIds = new Set(prev.map((item) => item.conversation_id));
            const additions = data.conversations.filter(
              (item) => !existingIds.has(item.conversation_id),
            );
            return [...prev, ...additions];
          });
        }
      } catch {
        // Keep draft chat as fallback.
      } finally {
        if (!cancelled) {
          setConversationsLoading(false);
        }
      }
    };

    init();
    return () => {
      cancelled = true;
    };
  }, [user?.user_id, isGeneralMode, config.greeting, mode]);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [messages, loading, loadingHistory]);

  useEffect(() => {
    if (mode === "anxiety" && (anxietyAwaitingFrequency || anxietySessionLocked)) return;
    if (mode === "depression" && (depressionAwaitingFrequency || depressionSessionLocked)) return;
    if (loading || loadingHistory || showAnxietyOnboarding || showDepressionOnboarding) return;
    const id = window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(id);
  }, [
    messages,
    loading,
    loadingHistory,
    anxietyAwaitingFrequency,
    anxietySessionLocked,
    depressionAwaitingFrequency,
    depressionSessionLocked,
    mode,
    showAnxietyOnboarding,
    showDepressionOnboarding,
  ]);

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (!openMenuConversationId) return;
      const activeWrap = menuWrapRefs.current[openMenuConversationId];
      if (activeWrap && !activeWrap.contains(event.target)) {
        setOpenMenuConversationId("");
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [openMenuConversationId]);

  useEffect(() => {
    const controller = new AbortController();
    const loadHistory = async () => {
      if (!user?.user_id || (isGeneralMode && !conversationId)) {
        setMessages([{ role: "assistant", content: config.greeting }]);
        setLoadingHistory(false);
        return;
      }
      if (isGeneralMode && isDraftConversation) {
        setLoadingHistory(false);
        setHistoryError("");
        return;
      }
      if (isGeneralMode && skipNextHistoryReloadRef.current === conversationId) {
        skipNextHistoryReloadRef.current = "";
        setLoadingHistory(false);
        setHistoryError("");
        return;
      }

      setLoadingHistory(true);
      setHistoryError("");
      try {
        const res = await fetch(
          `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=${mode}&conversation_id=${encodeURIComponent(conversationId)}`,
          { signal: controller.signal },
        );
        const data = await res.json();
        if (res.ok && Array.isArray(data.messages) && data.messages.length > 0) {
          const formatted = data.messages.map((msg) => ({ role: msg.role, content: msg.content }));
          setMessages(formatted);
          if (mode === "anxiety" || mode === "depression") {
            const lastAssistant = [...formatted].reverse().find((m) => m.role === "assistant");
            const lower = (lastAssistant?.content || "").toLowerCase();
            const awaiting = Boolean(
              lower.includes("please choose 1, 2, 3, or 4") ||
              lower.includes("please choose 0, 1, 2, or 3"),
            );
            const inferredReason = inferTerminalReasonFromText(lastAssistant?.content || "");
            if (mode === "anxiety") {
              setAnxietyAwaitingFrequency(awaiting);
              if (inferredReason) {
                setAnxietySessionLocked(true);
                setAnxietyLockNotice(inferAnxietyLockNotice(inferredReason, inferredReason === "completed"));
              } else {
                setAnxietySessionLocked(false);
                setAnxietyLockNotice("");
              }
            } else {
              setDepressionAwaitingFrequency(awaiting);
              if (inferredReason) {
                setDepressionSessionLocked(true);
                setDepressionLockNotice(inferAnxietyLockNotice(inferredReason, inferredReason === "completed"));
              } else {
                setDepressionSessionLocked(false);
                setDepressionLockNotice("");
              }
            }
          }
        } else {
          setMessages([{ role: "assistant", content: config.greeting }]);
          if (mode === "anxiety") {
            setAnxietyAwaitingFrequency(false);
            setAnxietySessionLocked(false);
            setAnxietyLockNotice("");
          } else if (mode === "depression") {
            setDepressionAwaitingFrequency(false);
            setDepressionSessionLocked(false);
            setDepressionLockNotice("");
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        setHistoryError("Could not load chat history. Showing a fresh chat view.");
        setMessages([{ role: "assistant", content: config.greeting }]);
        if (mode === "anxiety") {
          setAnxietyAwaitingFrequency(false);
          setAnxietySessionLocked(false);
          setAnxietyLockNotice("");
        } else if (mode === "depression") {
          setDepressionAwaitingFrequency(false);
          setDepressionSessionLocked(false);
          setDepressionLockNotice("");
        }
      } finally {
        setLoadingHistory(false);
      }
    };

    loadHistory();
    return () => controller.abort();
  }, [user?.user_id, mode, conversationId, config.greeting, isGeneralMode, isDraftConversation]);

  const persistMessage = async (msg) => {
    if (!user?.user_id) return;
    try {
      const res = await fetch(`${API_URL}/chat/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          mode,
          conversation_id: conversationId,
          role: msg.role,
          content: msg.content,
        }),
      });
      if (res.ok && isGeneralMode && conversationId) {
        setDraftConversationIds((prev) => prev.filter((id) => id !== conversationId));
        skipNextHistoryReloadRef.current = conversationId;
      }
    } catch {
      // Keep UI responsive even if persistence fails.
    }
  };

  const shorten = (text, maxLen = 60) => {
    const value = (text || "").trim();
    if (value.length <= maxLen) return value;
    return `${value.slice(0, maxLen).trimEnd()}...`;
  };

  const createAndSelectDraftConversation = () => {
    const id = createConversationId();
    setActiveConversationId(id);
    setConversations((prev) => [{ conversation_id: id, title: "New chat", updated_at: "" }, ...prev]);
    setDraftConversationIds((prev) => [id, ...prev]);
    setMessages([{ role: "assistant", content: config.greeting }]);
    setHistoryError("");
    setLoadingHistory(false);
    return id;
  };

  const deleteConversation = async (targetConversationId) => {
    if (!isGeneralMode || !targetConversationId || !user?.user_id) return;

    const confirmed = window.confirm("Delete this chat conversation permanently?");
    if (!confirmed) return;

    setDeletingConversationId(targetConversationId);
    const isDraft = draftConversationIds.includes(targetConversationId);

    if (!isDraft) {
      try {
        await fetch(
          `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=${mode}&conversation_id=${encodeURIComponent(targetConversationId)}`,
          { method: "DELETE" },
        );
      } catch {
        setDeletingConversationId("");
        return;
      }
    }

    const remaining = conversations.filter((item) => item.conversation_id !== targetConversationId);
    setConversations(remaining);
    setDraftConversationIds((prev) => prev.filter((id) => id !== targetConversationId));

    if (conversationId === targetConversationId) {
      if (remaining.length > 0) {
        setActiveConversationId(remaining[0].conversation_id);
      } else {
        createAndSelectDraftConversation();
      }
    }
    setDeletingConversationId("");
    setOpenMenuConversationId("");
  };

  const updateConversationPreview = (latestText, userTurnCount) => {
    if (!isGeneralMode) return;
    const updated = new Date().toISOString();

    let nextTitle = null;
    if (conversationId && userTurnCount === 1) {
      nextTitle = shorten(latestText) || "New chat";
    }

    setConversations((prev) => {
      const others = prev.filter((item) => item.conversation_id !== conversationId);
      const currentItem = prev.find((item) => item.conversation_id === conversationId);
      const current = {
        conversation_id: conversationId,
        title: nextTitle || currentItem?.title || "New chat",
        updated_at: updated,
      };
      return [current, ...others];
    });
  };

  const sendMessage = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading || loadingHistory) return;
    if (mode === "anxiety" && (anxietyAwaitingFrequency || anxietySessionLocked)) return;
    if (mode === "depression" && (depressionAwaitingFrequency || depressionSessionLocked)) return;

    await submitUserText(trimmed);
  };

  const submitUserText = async (trimmed) => {
    if (!trimmed || loading || loadingHistory) return;
    if (mode === "anxiety" && anxietySessionLocked) return;
    if (mode === "depression" && depressionSessionLocked) return;

    const userMsg = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMsg];
    const userTurnCount = nextMessages.filter((msg) => msg.role === "user").length;
    setMessages(nextMessages);
    setInput("");
    updateConversationPreview(trimmed, userTurnCount);

    if (mode === "general") {
      persistMessage(userMsg);
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
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (mode === "anxiety") {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/protocol/gad7/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user?.user_id || "anonymous",
            conversation_id: conversationId || "default",
            user_message: trimmed,
          }),
        });
        const data = await res.json();
        const assistantText = res.ok
          ? data.reply
          : data.detail || "Unable to continue GAD-7 right now. Please try again.";
        const assistantMsg = { role: "assistant", content: assistantText };
        const terminalReason = data?.terminal_reason || data?.state?.terminal_reason || "";
        const completed = Boolean(data?.completed);
        const shouldLock = Boolean(
          completed &&
            (terminalReason === "crisis" ||
              terminalReason === "withdrawn" ||
              terminalReason === "excluded" ||
              terminalReason === "completed"),
        );
        if (data?.delete_partial) {
          setMessages([{ role: "assistant", content: assistantText }]);
          setAnxietyAwaitingFrequency(false);
          setAnxietySessionLocked(true);
          setAnxietyLockNotice(inferAnxietyLockNotice(terminalReason || "withdrawn", completed));
          if (user?.user_id) {
            try {
              await fetch(
                `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=anxiety&conversation_id=${encodeURIComponent(conversationId || "default")}`,
                { method: "DELETE" },
              );
            } catch {
              // Best effort delete; backend also attempts partial-data deletion.
            }
          }
          return;
        }
        setAnxietyAwaitingFrequency(Boolean(data?.state?.awaiting_frequency));
        if (shouldLock) {
          setAnxietySessionLocked(true);
          setAnxietyLockNotice(inferAnxietyLockNotice(terminalReason, completed));
          setAnxietyAwaitingFrequency(false);
        } else {
          setAnxietySessionLocked(false);
          setAnxietyLockNotice("");
        }
        persistMessage(userMsg);
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
      } catch {
        const assistantMsg = {
          role: "assistant",
          content: "Network error while running GAD-7 protocol. Please try again.",
        };
        persistMessage(userMsg);
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
        setAnxietyAwaitingFrequency(false);
        setAnxietySessionLocked(false);
        setAnxietyLockNotice("");
      } finally {
        setLoading(false);
      }
      return;
    }
    if (mode === "depression") {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/protocol/phq9/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user?.user_id || "anonymous",
            conversation_id: conversationId || "default",
            user_message: trimmed,
          }),
        });
        const data = await res.json();
        const assistantText = res.ok
          ? data.reply
          : data.detail || "Unable to continue PHQ-9 right now. Please try again.";
        const assistantMsg = { role: "assistant", content: assistantText };
        const terminalReason = data?.terminal_reason || data?.state?.terminal_reason || "";
        const completed = Boolean(data?.completed);
        const shouldLock = Boolean(
          completed &&
            (terminalReason === "crisis" ||
              terminalReason === "withdrawn" ||
              terminalReason === "excluded" ||
              terminalReason === "completed"),
        );
        if (data?.delete_partial) {
          setMessages([{ role: "assistant", content: assistantText }]);
          setDepressionAwaitingFrequency(false);
          setDepressionSessionLocked(true);
          setDepressionLockNotice(inferAnxietyLockNotice(terminalReason || "withdrawn", completed));
          if (user?.user_id) {
            try {
              await fetch(
                `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=depression&conversation_id=${encodeURIComponent(conversationId || "default")}`,
                { method: "DELETE" },
              );
            } catch {
              // Best effort delete.
            }
          }
          return;
        }
        setDepressionAwaitingFrequency(Boolean(data?.state?.awaiting_frequency));
        if (shouldLock) {
          setDepressionSessionLocked(true);
          setDepressionLockNotice(inferAnxietyLockNotice(terminalReason, completed));
          setDepressionAwaitingFrequency(false);
        } else {
          setDepressionSessionLocked(false);
          setDepressionLockNotice("");
        }
        persistMessage(userMsg);
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
      } catch {
        const assistantMsg = {
          role: "assistant",
          content: "Network error while running PHQ-9 protocol. Please try again.",
        };
        persistMessage(userMsg);
        setMessages((prev) => [...prev, assistantMsg]);
        persistMessage(assistantMsg);
        setDepressionAwaitingFrequency(false);
        setDepressionSessionLocked(false);
        setDepressionLockNotice("");
      } finally {
        setLoading(false);
      }
    }
  };

  const clearChat = async () => {
    if (isGeneralMode) {
      const hasUserMessage = messages.some((msg) => msg.role === "user");
      if (!hasUserMessage) {
        return;
      }
      createAndSelectDraftConversation();
      return;
    }

    if (mode === "anxiety" && user?.user_id) {
      try {
        await fetch(`${API_URL}/protocol/gad7/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user.user_id,
            conversation_id: conversationId || "default",
          }),
        });
      } catch {
        // Best-effort reset; continue with local reset below.
      }
      setAnxietyAwaitingFrequency(false);
      setAnxietySessionLocked(false);
      setAnxietyLockNotice("");
      setShowAnxietyOnboarding(true);
      setShowDepressionOnboarding(false);
    }

    if (mode === "depression" && user?.user_id) {
      try {
        await fetch(`${API_URL}/protocol/phq9/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user.user_id,
            conversation_id: conversationId || "default",
          }),
        });
      } catch {
        // Best-effort reset; continue with local reset below.
      }
      setDepressionAwaitingFrequency(false);
      setDepressionSessionLocked(false);
      setDepressionLockNotice("");
      setShowDepressionOnboarding(true);
      setShowAnxietyOnboarding(false);
    }

    if (user?.user_id) {
      try {
        await fetch(
          `${API_URL}/chat/history?user_id=${encodeURIComponent(user.user_id)}&mode=${mode}&conversation_id=${encodeURIComponent(conversationId)}`,
          { method: "DELETE" },
        );
      } catch {
        // Ignore delete failures; reset current UI anyway.
      }
    }
    setMessages([{ role: "assistant", content: config.greeting }]);
  };

  const handleAnxietyOnboardingSubmit = async () => {
    if (!user?.user_id) return;
    setLoading(true);
    setHistoryError("");
    try {
      const convId = conversationId || "default";
      const isAnxiety = mode === "anxiety";
      const protocolBootstrapUrl = isAnxiety
        ? `${API_URL}/protocol/gad7/bootstrap`
        : `${API_URL}/protocol/phq9/bootstrap`;

      const res = await fetch(protocolBootstrapUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          conversation_id: convId,
          age_18_plus: anxietyIntake.age_18_plus === "yes",
          in_crisis: anxietyIntake.in_crisis === "yes",
          consent: anxietyIntake.consent === "yes",
        }),
      });
      const data = await res.json();
      const latestReply = res.ok ? data.reply : data.detail || "Failed to initialize protocol session.";
      const latestAwaitingFrequency = Boolean(data?.state?.awaiting_frequency);
      const latestCompleted = Boolean(data?.completed);

      setMessages([{ role: "assistant", content: latestReply }]);
      if (isAnxiety) {
        setAnxietyAwaitingFrequency(latestAwaitingFrequency);
      } else {
        setDepressionAwaitingFrequency(latestAwaitingFrequency);
      }
      const inferredReason = inferTerminalReasonFromText(latestReply);
      if (latestCompleted || inferredReason) {
        const finalReason = inferredReason || "completed";
        if (isAnxiety) {
          setAnxietySessionLocked(true);
          setAnxietyLockNotice(inferAnxietyLockNotice(finalReason, true));
          setAnxietyAwaitingFrequency(false);
        } else {
          setDepressionSessionLocked(true);
          setDepressionLockNotice(inferAnxietyLockNotice(finalReason, true));
          setDepressionAwaitingFrequency(false);
        }
      } else {
        if (isAnxiety) {
          setAnxietySessionLocked(false);
          setAnxietyLockNotice("");
        } else {
          setDepressionSessionLocked(false);
          setDepressionLockNotice("");
        }
      }
      setShowAnxietyOnboarding(false);
      setShowDepressionOnboarding(false);
    } catch {
      setHistoryError("Could not initialize protocol session. Please try again.");
    } finally {
      setLoading(false);
    }
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

        {isGeneralMode && (
          <div className="conversation-list">
            <p className="conversation-title">Recent Chats</p>
            {conversationsLoading && (
              <p className="conversation-loading">Loading chats...</p>
            )}
            {conversations.map((item, idx) => (
              <div
                key={item.conversation_id}
                className={
                  item.conversation_id === conversationId
                    ? "conversation-item-row active"
                    : "conversation-item-row"
                }
              >
                <button
                  type="button"
                  className="conversation-item"
                  onClick={() => setActiveConversationId(item.conversation_id)}
                >
                  {item.title || "New chat"}
                </button>
                <div
                  className="conversation-menu-wrap"
                  ref={(el) => {
                    if (el) {
                      menuWrapRefs.current[item.conversation_id] = el;
                    } else {
                      delete menuWrapRefs.current[item.conversation_id];
                    }
                  }}
                >
                  <button
                    type="button"
                    className="conversation-menu-toggle"
                    onClick={() =>
                      setOpenMenuConversationId((prev) =>
                        prev === item.conversation_id ? "" : item.conversation_id,
                      )
                    }
                    aria-label="Open chat options"
                  >
                    ...
                  </button>
                  {openMenuConversationId === item.conversation_id && (
                    <div
                      className={
                        idx >= conversations.length - 2
                          ? "conversation-menu conversation-menu-up"
                          : "conversation-menu"
                      }
                    >
                      <button
                        type="button"
                        className="conversation-menu-delete"
                        onClick={() => deleteConversation(item.conversation_id)}
                        disabled={deletingConversationId === item.conversation_id}
                      >
                        {deletingConversationId === item.conversation_id
                          ? "Deleting..."
                          : "Delete chat"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </aside>

      <section className="chat-main">
        {(mode === "anxiety" && showAnxietyOnboarding) ||
        (mode === "depression" && showDepressionOnboarding) ? (
          <div className="onboard-overlay">
            <div className="onboard-card">
              <h2>{mode === "anxiety" ? "Anxiety Screening Setup" : "Depression Screening Setup"}</h2>
              <p>
                This is a research screening flow ({mode === "anxiety" ? "GAD-7" : "PHQ-9"}), not
                a diagnosis. Please confirm the required items to begin.
              </p>

              <div className="onboard-field">
                <label>Are you 18 or older?</label>
                <div>
                  <button
                    type="button"
                    className={anxietyIntake.age_18_plus === "yes" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, age_18_plus: "yes" }))}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    className={anxietyIntake.age_18_plus === "no" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, age_18_plus: "no" }))}
                  >
                    No
                  </button>
                </div>
              </div>

              <div className="onboard-field">
                <label>Are you currently in a crisis or actively suicidal?</label>
                <div>
                  <button
                    type="button"
                    className={anxietyIntake.in_crisis === "yes" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, in_crisis: "yes" }))}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    className={anxietyIntake.in_crisis === "no" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, in_crisis: "no" }))}
                  >
                    No
                  </button>
                </div>
              </div>

              <div className="onboard-field">
                <label>Do you consent to participate in this research screening?</label>
                <div>
                  <button
                    type="button"
                    className={anxietyIntake.consent === "yes" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, consent: "yes" }))}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    className={anxietyIntake.consent === "no" ? "onboard-opt active" : "onboard-opt"}
                    onClick={() => setAnxietyIntake((s) => ({ ...s, consent: "no" }))}
                  >
                    No
                  </button>
                </div>
              </div>

              <button type="button" className="onboard-start" onClick={handleAnxietyOnboardingSubmit} disabled={loading}>
                {loading ? "Starting..." : "Start Session"}
              </button>
            </div>
          </div>
        ) : null}
        <header className="chat-header">
          <div>
            <h1>{config.title}</h1>
            <p>{config.subtitle}</p>
          </div>
          <span className="mode-tag">{config.tag}</span>
        </header>

        <div className="chat-messages" ref={messagesRef}>
          {historyError && (
            <div className="msg assistant">
              <div className="msg-role">System</div>
              <p>{historyError}</p>
            </div>
          )}
          {loadingHistory && (
            <div className="msg assistant">
              <div className="msg-role">Assistant</div>
              <p>Loading previous chat...</p>
            </div>
          )}
          {!loadingHistory &&
            messages.map((msg, idx) => (
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
          {mode === "anxiety" && anxietyLockNotice && (
            <div className="anxiety-session-notice">{anxietyLockNotice}</div>
          )}
          {mode === "depression" && depressionLockNotice && (
            <div className="anxiety-session-notice">{depressionLockNotice}</div>
          )}
          {mode === "anxiety" && anxietyAwaitingFrequency && !anxietySessionLocked && (
            <div className="anxiety-frequency-bar">
              <button type="button" onClick={() => submitUserText("1")} disabled={loading || loadingHistory || anxietySessionLocked}>
                1. Not at all
              </button>
              <button type="button" onClick={() => submitUserText("2")} disabled={loading || loadingHistory || anxietySessionLocked}>
                2. Several days
              </button>
              <button type="button" onClick={() => submitUserText("3")} disabled={loading || loadingHistory || anxietySessionLocked}>
                3. More than half the days
              </button>
              <button type="button" onClick={() => submitUserText("4")} disabled={loading || loadingHistory || anxietySessionLocked}>
                4. Nearly every day
              </button>
            </div>
          )}
          {mode === "depression" && depressionAwaitingFrequency && !depressionSessionLocked && (
            <div className="anxiety-frequency-bar">
              <button type="button" onClick={() => submitUserText("1")} disabled={loading || loadingHistory || depressionSessionLocked}>
                1. Not at all
              </button>
              <button type="button" onClick={() => submitUserText("2")} disabled={loading || loadingHistory || depressionSessionLocked}>
                2. Several days
              </button>
              <button type="button" onClick={() => submitUserText("3")} disabled={loading || loadingHistory || depressionSessionLocked}>
                3. More than half the days
              </button>
              <button type="button" onClick={() => submitUserText("4")} disabled={loading || loadingHistory || depressionSessionLocked}>
                4. Nearly every day
              </button>
            </div>
          )}
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              mode === "anxiety" && anxietySessionLocked
                ? "Session ended. Click New Chat to start again."
                : mode === "depression" && depressionSessionLocked
                  ? "Session ended. Click New Chat to start again."
                : mode === "anxiety" && anxietyAwaitingFrequency
                  ? "Select one option above"
                  : mode === "depression" && depressionAwaitingFrequency
                    ? "Select one option above"
                  : "Type your message..."
            }
            aria-label="Type message"
            disabled={
              loading ||
              loadingHistory ||
              (mode === "anxiety" && (anxietyAwaitingFrequency || anxietySessionLocked)) ||
              (mode === "depression" && (depressionAwaitingFrequency || depressionSessionLocked))
            }
          />
          <button
            type="submit"
            disabled={
              loading ||
              loadingHistory ||
              (mode === "anxiety" && (anxietyAwaitingFrequency || anxietySessionLocked)) ||
              (mode === "depression" && (depressionAwaitingFrequency || depressionSessionLocked))
            }
          >
            Send
          </button>
        </form>
      </section>
    </div>
  );
}
