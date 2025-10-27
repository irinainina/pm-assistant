"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import styles from "./Sidebar.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Sidebar({ onSelectConversation, currentConversationId, isOpen, onClose }) {
  const { data: session } = useSession();
  const [conversations, setConversations] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);

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

  const handleMenuClick = (conversation, event) => {
    event.stopPropagation(); // Предотвращаем всплытие события к родительскому div
    setSelectedConversation(conversation);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setSelectedConversation(null);
  };

  const handleModalAction = (action) => {
    console.log(`Action: ${action} for conversation:`, selectedConversation);
    // Здесь будет логика для каждой кнопки
    switch (action) {
      case "rename":
        // Логика переименования
        break;
      case "useful":
        // Логика пометки как полезное
        break;
      case "share":
        // Логика поделиться
        break;
      case "delete":
        // Логика удаления
        break;
      default:
        break;
    }
    handleModalClose();
  };

  if (!session) {
    return null;
  }

  return (
    <>
      <div className={`${styles.sidebar} ${isOpen ? styles.open : styles.closed}`}>
        <div className={styles.header}>
          <h3>Chat History</h3>
          {isOpen && (
            <button className={styles.closeButton} onClick={onClose} aria-label="Close sidebar">
              ×
            </button>
          )}
        </div>

        <div className={styles.conversationList}>
          {conversations.length === 0 ? (
            <div className={styles.empty}>No conversations yet</div>
          ) : (
            conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`${styles.conversationItem} ${
                  currentConversationId === conversation.id ? styles.active : ""
                }`}
                onClick={() => onSelectConversation(conversation.id)}
              >
                <div className={styles.conversationContent}>
                  <div className={styles.conversationTitle}>{conversation.title}</div>
                  <button
                    className={styles.menuButton}
                    onClick={(e) => handleMenuClick(conversation, e)}
                    aria-label="Conversation menu"
                  >
                    ⋮
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {modalOpen && (
        <div className={styles.modalOverlay} onClick={handleModalClose}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <button className={styles.modalClose} onClick={handleModalClose}>
              ×
            </button>
            <div className={styles.modalActions}>
              <button className={styles.actionButton} onClick={() => handleModalAction("rename")}>
                Rename
              </button>
              <button className={styles.actionButton} onClick={() => handleModalAction("useful")}>
                Usefull
              </button>
              <button className={styles.actionButton} onClick={() => handleModalAction("share")}>
                Share
              </button>
              <button
                className={`${styles.actionButton} ${styles.deleteButton}`}
                onClick={() => handleModalAction("delete")}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
