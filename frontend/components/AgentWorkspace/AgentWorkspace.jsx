"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/Sidebar/Sidebar";
import AgentSection from "@/components/AgentSection/AgentSection";
import styles from "./AgentWorkspace.module.css";

export default function AgentWorkspace() {
  const { data: session } = useSession();
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleSelectConversation = (conversationId) => {
    setCurrentConversationId(conversationId);
  };

  return (
    <div className={styles.container}>
      {session && (
        <Sidebar
          onSelectConversation={handleSelectConversation}
          currentConversationId={currentConversationId}
          isOpen={isSidebarOpen}
        />
      )}

      <div className={styles.chatContainer}>
        <AgentSection currentConversationId={currentConversationId} onConversationChange={handleSelectConversation} />
      </div>
    </div>
  );
}
