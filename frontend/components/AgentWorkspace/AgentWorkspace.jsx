"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/Sidebar/Sidebar";
import AgentSection from "@/components/AgentSection/AgentSection";
import styles from "./AgentWorkspace.module.css";

export default function AgentWorkspace({ initialConversationId, isPublicMode = false }) {
  const { data: session } = useSession();
  const [currentConversationId, setCurrentConversationId] = useState(initialConversationId || null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [newConversationFlag, setNewConversationFlag] = useState(false);

  useEffect(() => {
    if (initialConversationId) {
      setCurrentConversationId(initialConversationId);
    }
  }, [initialConversationId]);

  useEffect(() => {
    const savedSidebarState = localStorage.getItem("sidebarOpen");
    if (savedSidebarState !== null) {
      setIsSidebarOpen(JSON.parse(savedSidebarState));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("sidebarOpen", JSON.stringify(isSidebarOpen));
  }, [isSidebarOpen]);

  const handleSelectConversation = (conversationId) => {
    setCurrentConversationId(conversationId);
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const handleNewConversation = () => {
    setNewConversationFlag((prev) => !prev);
  };

  return (
    <div className={styles.container}>
      {session && (
        <Sidebar
          onSelectConversation={handleSelectConversation}
          currentConversationId={currentConversationId}
          isOpen={isSidebarOpen}
          onClose={toggleSidebar}
          onNewConversation={newConversationFlag}
        />
      )}

      <div className={`${isSidebarOpen && session ? styles.chatContainer : styles.chatContainerOpen}`}>
        {!isSidebarOpen && (
          <button className={styles.openButton} onClick={toggleSidebar} aria-label="Open sidebar">
            ☰
          </button>
        )}
        <AgentSection
          currentConversationId={currentConversationId}
          onConversationChange={handleSelectConversation}
          isPublicMode={isPublicMode}
          onNewConversation={handleNewConversation}
        />
      </div>
    </div>
  );
}
