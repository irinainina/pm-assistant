"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import Notification from "@/components/Notification/Notification";
import styles from "./Sidebar.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Sidebar({ onSelectConversation, currentConversationId, isOpen, onClose }) {
  const { data: session } = useSession();
  const [conversations, setConversations] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [modalPosition, setModalPosition] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editedTitle, setEditedTitle] = useState("");
  const [previousTitle, setPreviousTitle] = useState("");
  const [notification, setNotification] = useState({ isVisible: false, message: "" });
  const [searchTerm, setSearchTerm] = useState("");

  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== "undefined") {
      const savedTab = localStorage.getItem("conversations-active-tab");
      return savedTab && (savedTab === "all" || savedTab === "useful") ? savedTab : "all";
    }
    return "all";
  });

  const editableRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("conversations-active-tab", activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (session?.user?.id) {
      loadConversations();
    }
  }, [session]);

  const loadConversations = async () => {
    if (!session?.user?.id) return;

    try {
      const response = await fetch(`${apiUrl}/api/conversations`, {
        headers: { "User-Id": session.user.id },
      });
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error("Error loading conversations:", error);
    }
  };

  const filteredConversations = conversations.filter((conversation) => {
    const matchesSearch = conversation.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTab = activeTab === "useful" ? conversation.is_useful : true;
    return matchesSearch && matchesTab;
  });

  const clearSearch = () => {
    setSearchTerm("");
  };

  const handleMenuClick = (conversation, event) => {
    event.stopPropagation();
    if (modalOpen && selectedConversation?.id === conversation.id) {
      handleModalClose();
      return;
    }
    setSelectedConversation(conversation);
    const rect = event.currentTarget.getBoundingClientRect();
    setModalPosition({
      top: rect.top - 56,
      left: rect.right - 80,
    });
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setSelectedConversation(null);
  };

  const handleStartEditing = () => {
    if (!selectedConversation) return;
    setEditingId(selectedConversation.id);
    setEditedTitle(selectedConversation.title);
    setPreviousTitle(selectedConversation.title);
    setModalOpen(false);
  };

  const handleFinishEditing = async () => {
    const newTitle = editedTitle.trim();
    if (!editingId) return;

    if (newTitle && newTitle !== previousTitle) {
      try {
        const response = await fetch(`${apiUrl}/api/conversations/${editingId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "User-Id": session.user.id,
          },
          body: JSON.stringify({ title: newTitle }),
        });

        if (response.ok) {
          const updated = await response.json();
          setConversations((prev) =>
            prev.map((conv) => (conv.id === updated.id ? { ...conv, title: updated.title } : conv))
          );
        } else {
          setConversations((prev) =>
            prev.map((conv) => (conv.id === editingId ? { ...conv, title: previousTitle } : conv))
          );
        }
      } catch (error) {
        console.error("Error renaming conversation:", error);
      }
    } else {
      setConversations((prev) =>
        prev.map((conv) => (conv.id === editingId ? { ...conv, title: previousTitle } : conv))
      );
    }

    setEditingId(null);
    setEditedTitle("");
    setPreviousTitle("");
  };

  const handleToggleUseful = async () => {
    if (!selectedConversation) return;

    try {
      const response = await fetch(`${apiUrl}/api/conversations/${selectedConversation.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "User-Id": session.user.id,
        },
        body: JSON.stringify({ is_useful: !selectedConversation.is_useful }),
      });

      if (response.ok) {
        const updated = await response.json();
        setConversations((prev) =>
          prev.map((conv) => (conv.id === updated.id ? { ...conv, is_useful: updated.is_useful } : conv))
        );
        handleModalClose();
      }
    } catch (error) {
      console.error("Error toggling useful:", error);
    }
  };

  const handleDelete = async () => {
    if (!selectedConversation) return;

    if (!confirm("Are you sure you want to delete this conversation?")) return;

    try {
      const response = await fetch(`${apiUrl}/api/conversations/${selectedConversation.id}`, {
        method: "DELETE",
        headers: { "User-Id": session.user.id },
      });

      if (response.ok) {
        setConversations((prev) => prev.filter((c) => c.id !== selectedConversation.id));
        if (currentConversationId === selectedConversation.id) {
          onSelectConversation(null);
        }
        handleModalClose();
      }
    } catch (error) {
      console.error("Error deleting conversation:", error);
    }
  };

  const handleShare = () => {
    if (!selectedConversation) return;
    const shareUrl = `${window.location.origin}/${selectedConversation.id}`;
    navigator.clipboard
      .writeText(shareUrl)
      .then(() => {
        setNotification({ isVisible: true, message: "Conversation link copied to clipboard!" });
      })
      .catch(() => {
        setNotification({ isVisible: true, message: `Share this link: ${shareUrl}` });
      });
    handleModalClose();
  };

  const closeNotification = () => {
    setNotification({ isVisible: false, message: "" });
  };

  const handleModalAction = (action) => {
    switch (action) {
      case "rename":
        handleStartEditing();
        break;
      case "useful":
        handleToggleUseful();
        break;
      case "share":
        handleShare();
        break;
      case "delete":
        handleDelete();
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    if (!modalOpen) return;

    const handleClickOutside = (e) => {
      const modal = document.querySelector(`.${styles.modal}`);
      if (modal && !modal.contains(e.target)) handleModalClose();
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [modalOpen]);

  if (!session) return null;

  useEffect(() => {
    if (editableRef.current && editingId) {
      editableRef.current.focus();
      const range = document.createRange();
      range.selectNodeContents(editableRef.current);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }, [editingId]);

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

        <div className={styles.searchContainer}>
          <div className={styles.searchWrapper}>
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
            />
            {searchTerm && (
              <button className={styles.clearButton} onClick={clearSearch} aria-label="Clear search">
                ×
              </button>
            )}
          </div>
        </div>

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === "all" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("all")}
          >
            All ({conversations.length})
          </button>
          <button
            className={`${styles.tab} ${activeTab === "useful" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("useful")}
          >
            Useful ({conversations.filter((c) => c.is_useful).length})
          </button>
        </div>

        <div className={styles.conversationList}>
          {filteredConversations.length === 0 ? (
            <div className={styles.empty}>
              {searchTerm
                ? "No conversations found"
                : activeTab === "useful"
                ? "No useful conversations yet"
                : "No conversations yet"}
            </div>
          ) : (
            filteredConversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`${styles.conversationItem} 
                ${currentConversationId === conversation.id ? styles.active : ""} 
                ${conversation.is_useful ? styles.useful : ""} 
                ${selectedConversation?.id === conversation.id && modalOpen ? styles.hover : ""}`}
                onClick={() => onSelectConversation(conversation.id)}
              >
                <div className={styles.conversationContent}>
                  {editingId === conversation.id ? (
                    <input
                      ref={editableRef}
                      type="text"
                      className={styles.editableInput}
                      value={editedTitle}
                      autoFocus
                      onBlur={handleFinishEditing}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleFinishEditing();
                        }
                        if (e.key === "Escape") {
                          setEditingId(null);
                          setEditedTitle("");
                          setPreviousTitle("");
                        }
                      }}
                      onMouseDown={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <div className={styles.conversationTitle}>
                      {conversation.is_useful && "⭐ "}
                      {conversation.title}
                    </div>
                  )}
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
        <div
          className={styles.modal}
          style={{
            position: "absolute",
            top: modalPosition?.top ?? 0,
            left: modalPosition?.left ?? 0,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={styles.modalActions}>
            <button className={styles.actionButton} onClick={() => handleModalAction("rename")}>
              Rename
            </button>
            <button className={styles.actionButton} onClick={() => handleModalAction("useful")}>
              {selectedConversation?.is_useful ? "Not useful" : "Useful"}
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
      )}
      <Notification message={notification.message} isVisible={notification.isVisible} onClose={closeNotification} />
    </>
  );
}
