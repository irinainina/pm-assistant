"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import styles from "./AgentSection.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

export default function AgentSection() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDbActual, setIsDbActual] = useState(true);

  const chatRef = useRef(null);
  const storageKey = "agent_history";

  useEffect(() => {
    const savedHistory = localStorage.getItem(storageKey);
    if (savedHistory) setMessages(JSON.parse(savedHistory));
  }, []);

  const saveHistory = (newMessages) => {
    setMessages(newMessages);
    localStorage.setItem(storageKey, JSON.stringify(newMessages));
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
        method: "POST",
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

    const userMessage = { role: "user", text: trimmed };
    saveHistory([...messages, userMessage]);

    try {
      const res = await fetch(`${apiUrl}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, conversation_id: "default" }),
      });

      const data = await res.json();

      const agentMessage = {
        role: "agent",
        text: data.answer || "No answer",
        sources: data.sources || [],
      };

      saveHistory([...messages, userMessage, agentMessage]);
    } catch (err) {
      const errorMessage = { role: "error", text: "Server error" };
      saveHistory([...messages, errorMessage]);
    } finally {
      setIsLoading(false);
      setInput("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleNewChat = () => {
    setMessages([]);
    localStorage.removeItem(storageKey);
  };

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    checkDbStatus();
  }, []);

  return (
    <section className={styles.section}>
      <div className={styles.imageWrapper}>
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
        >
          New Chat
        </button>
      </div>
      <p className={styles.description}>Ask any project management question and get answers with sources.</p>

      <div className={styles.chatWrapper}>
        <div ref={chatRef} className={messages.length > 0 ? styles.chat : ""}>
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.role === "user" ? styles.user : styles.agent}>
              <strong>{msg.role === "user" ? "You: " : "AI:"}</strong>
              {msg.role === "user" ? (
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
                              src.score >= 0.6
                                ? styles.highScore
                                : src.score >= 0.3
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

      <div className={styles.inputArea}>
        <input
          type="text"
          value={input}
          placeholder="Type your question..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className={styles.input}
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
    </section>
  );
}
