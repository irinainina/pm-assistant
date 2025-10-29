"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { useSession } from "next-auth/react";
import QuickQuestions from "@/components/QuickQuestions/QuickQuestions";
import styles from "./AgentSection.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

export default function AgentSection({ currentConversationId, onConversationChange, isPublicMode = false }) {
  const { data: session } = useSession();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDbActual, setIsDbActual] = useState(true);
  const [showQuickQuestions, setShowQuickQuestions] = useState(false);

  const handleSelectQuestion = (question) => {
    setInput(question);
    setShowQuickQuestions(false);
  };

  const chatRef = useRef(null);
  const storageKey = "agent_history";

  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    } else {
      const savedHistory = localStorage.getItem(storageKey);
      if (savedHistory) setMessages(JSON.parse(savedHistory));
    }
  }, [currentConversationId]);

  const loadConversation = async (conversationId) => {
    if (!conversationId) return;

    try {
      let url;
      let options = {};

      if (isPublicMode) {
        url = `${apiUrl}/api/public/conversations/${conversationId}/messages`;
      } else {
        if (!session?.user?.id) return;
        url = `${apiUrl}/api/conversations/${conversationId}/messages`;
        options.headers = {
          "User-Id": session.user.id,
        };
      }

      const response = await fetch(url, options);

      if (response.ok) {
        const data = await response.json();

        const formattedMessages = data.messages.map((msg) => {
          if (msg.role === "user") {
            return {
              role: "user",
              content: msg.content,
              text: msg.content,
            };
          } else {
            return {
              role: "agent",
              content: msg.content,
              text: msg.content,
              sources: msg.sources || [],
            };
          }
        });

        setMessages(formattedMessages);
      }
    } catch (error) {
      console.error("Error loading conversation:", error);
    }
  };

  const showInput = !isPublicMode || (isPublicMode && session);

  const saveHistory = (newMessages) => {
    setMessages(newMessages);
    if (!currentConversationId) {
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
    }
  };

  const checkDbStatus = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/notion/status`);
      const data = await res.json();

      if (res.ok) {
        setIsDbActual(data.is_actual);
      }
    } catch (err) {
      console.error("Failed to check DB status:", err);
    }
  };

  const updateDatabase = async () => {
    setIsUpdating(true);

    try {
      const res = await fetch(`${apiUrl}/api/notion/update_vector_db`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      const data = await res.json();

      if (res.ok) {
        await checkDbStatus();
      } else {
        console.error("Update error:", data.error || "Unknown error");
      }
    } catch (err) {
      console.error("Update failed:", err);
    } finally {
      setIsUpdating(false);
    }
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setInput("");

    const userMessage = { role: "user", content: trimmed, text: trimmed };
    const updatedMessages = [...messages, userMessage];
    saveHistory(updatedMessages);

    try {
      const conversationHistory = updatedMessages
        .filter((msg) => msg.role === "user" || msg.role === "agent")
        .map((msg) => ({
          role: msg.role === "user" ? "user" : "assistant",
          content: msg.content || msg.text,
        }));

      const res = await fetch(`${apiUrl}/api/ask-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Id": session?.user?.id || "",
        },
        body: JSON.stringify({
          query: trimmed,
          history: conversationHistory,
          conversation_id: currentConversationId,
        }),
      });

      if (!res.ok) {
        throw new Error("Request failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedAnswer = "";

      const tempMessage = {
        role: "agent",
        content: "",
        text: "",
        sources: [],
        isStreaming: true,
      };

      const streamingMessages = [...updatedMessages, tempMessage];
      saveHistory(streamingMessages);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.error) {
                throw new Error(data.error);
              }

              if (data.chunk) {
                accumulatedAnswer += data.chunk;

                const updatedStreamingMessages = [
                  ...updatedMessages,
                  {
                    role: "agent",
                    content: accumulatedAnswer,
                    text: accumulatedAnswer,
                    sources: [],
                    isStreaming: true,
                  },
                ];
                saveHistory(updatedStreamingMessages);
              }

              if (data.done) {
                const finalMessage = {
                  role: "agent",
                  content: accumulatedAnswer,
                  text: accumulatedAnswer,
                  sources: data.sources || [],
                  isStreaming: false,
                };

                saveHistory([...updatedMessages, finalMessage]);
                setIsLoading(false);
                return;
              }
            } catch (e) {
              console.error("Error parsing stream data:", e);
            }
          }
        }
      }
    } catch (err) {
      const errorMessage = {
        role: "error",
        content: "Error: " + err.message,
        text: "Error: " + err.message,
      };
      saveHistory([...updatedMessages, errorMessage]);
      setIsLoading(false);
      setInput(trimmed);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    onConversationChange(null);
    localStorage.removeItem(storageKey);
    setInput("");
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    checkDbStatus();
  }, []);

  return (
    <section className={styles.section}>
      <div className={styles.imageWrapper}>
        <button
          className={`${styles.button} ${styles.quickQuestionsButton}`}
          onClick={() => {
            handleNewChat();
            setShowQuickQuestions(true);
          }}
        >
          Quick Questions
        </button>
        <button
          onClick={updateDatabase}
          className={`${styles.button} ${styles.updateButton} ${
            isUpdating ? styles.loading : !isDbActual ? styles.outdated : ""
          }`}
          disabled={isUpdating}
        >
          {isUpdating ? "Updating" : "Update DB"}
          {isUpdating && (
            <span className={styles.dots}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
            </span>
          )}
        </button>
        <Image src="/agent.jpg" className={styles.image} width={1900} height={700} alt="agent" priority />
      </div>

      <div className={styles.titleWrapper}>
        <h2 className={styles.title}>PM Assistant</h2>
        <button
          onClick={handleNewChat}
          className={`${styles.button} ${messages.length > 0 ? styles.active : styles.inactive}`}
          disabled={messages.length === 0}
        >
          New Chat
        </button>
      </div>
      <p className={styles.description}>Ask any project management question and get answers with sources.</p>

      <div className={styles.chatWrapper}>
        <div ref={chatRef} className={messages.length > 0 ? styles.chat : ""}>
          {messages.map((msg, idx) => (
            <div key={idx} className={styles[msg.role]}>
              <strong>{msg.role === "user" ? "You: " : msg.role === "agent" ? "AI: " : "Error: "}</strong>
              {msg.role === "user" || msg.role === "error" ? (
                msg.text
              ) : (
                <>
                  <div className={styles.agentContent} dangerouslySetInnerHTML={{ __html: msg.text }} />
                  {msg.sources && msg.sources.length > 0 && (
                    <>
                      <h3 className={styles.sourcesTitle}>Sources:</h3>
                      <ul className={styles.sources}>
                        {msg.sources.map((src, i) => (
                          <li
                            key={i}
                            className={
                              src.score >= 0.75
                                ? styles.highScore
                                : src.score >= 0.45
                                ? styles.mediumScore
                                : styles.lowScore
                            }
                          >
                            <a href={src.url} target="_blank" rel="noopener noreferrer">
                              {src.title}
                            </a>{" "}
                            - {src.score}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {showInput && (
        <div className={styles.inputArea}>
          <input
            type="text"
            value={input}
            placeholder="Type your question..."
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className={styles.input}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            className={`${styles.button} ${isLoading ? styles.loading : ""}`}
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? "Sending" : "Send"}
            {isLoading && (
              <span className={styles.dots}>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
              </span>
            )}
          </button>
        </div>
      )}
      <QuickQuestions
        onSelectQuestion={handleSelectQuestion}
        isOpen={showQuickQuestions}
        onClose={() => setShowQuickQuestions(false)}
      />
    </section>
  );
}
