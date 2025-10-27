"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import styles from "./Sidebar.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Sidebar({ onSelectConversation, currentConversationId, isOpen }) {
  const { data: session } = useSession();
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    if (session?.user?.id) {
      loadConversations();
    }
  }, [session]);

  const loadConversations = async () => {
    if (!session?.user?.id) return;

    try {
      const response = await fetch(`${apiUrl}/api/conversations`, {
        headers: {
          "User-Id": session.user.id,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error("Error loading conversations:", error);
    }
  };

  if (!session) {
    return null;
  }

  return (
    <div className={`${styles.sidebar} ${isOpen ? styles.open : styles.closed}`}>
      <div className={styles.header}>
        <h3>Chat History</h3>
      </div>

      <div className={styles.conversationList}>
        {conversations.length === 0 ? (
          <div className={styles.empty}>No conversations yet</div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`${styles.conversationItem} ${currentConversationId === conversation.id ? styles.active : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className={styles.conversationTitle}>{conversation.title}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
