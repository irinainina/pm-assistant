"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/Sidebar/Sidebar";
import AgentSection from "@/components/AgentSection/AgentSection";
import styles from "./AgentWorkspace.module.css";

export default function AgentWorkspace() {
  const { data: session } = useSession();
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

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

  return (
    <div className={styles.container}>
      {session && (
        <Sidebar
          onSelectConversation={handleSelectConversation}
          currentConversationId={currentConversationId}
          isOpen={isSidebarOpen}
          onClose={toggleSidebar}
        />
      )}

      <div className={`${isSidebarOpen ? styles.chatContainer : styles.chatContainerOpen}`}>
        {!isSidebarOpen && (
          <button className={styles.openButton} onClick={toggleSidebar} aria-label="Open sidebar">
            ☰
          </button>
        )}
        <AgentSection currentConversationId={currentConversationId} onConversationChange={handleSelectConversation} />
      </div>
    </div>
  );
}
