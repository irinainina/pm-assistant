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
  const [conversations, setConversations] = useState([]);

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

  const loadConversations = async () => {
    if (!session?.user?.id) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
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
          conversations={conversations}
          onSelectConversation={handleSelectConversation}
          currentConversationId={currentConversationId}
          isOpen={isSidebarOpen}
          onClose={toggleSidebar}
          onConversationsUpdate={loadConversations}
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
          onNewConversation={loadConversations}
        />
      </div>
    </div>
  );
}

// "use client";

// import { useState, useEffect } from "react";
// import { useSession } from "next-auth/react";
// import Sidebar from "@/components/Sidebar/Sidebar";
// import AgentSection from "@/components/AgentSection/AgentSection";
// import styles from "./AgentWorkspace.module.css";

// export default function AgentWorkspace({ initialConversationId, isPublicMode = false }) {
//   const { data: session } = useSession();
//   const [currentConversationId, setCurrentConversationId] = useState(initialConversationId || null);
//   const [isSidebarOpen, setIsSidebarOpen] = useState(true);

//   useEffect(() => {
//     if (initialConversationId) {
//       setCurrentConversationId(initialConversationId);
//     }
//   }, [initialConversationId]);

//   useEffect(() => {
//     const savedSidebarState = localStorage.getItem("sidebarOpen");
//     if (savedSidebarState !== null) {
//       setIsSidebarOpen(JSON.parse(savedSidebarState));
//     }
//   }, []);

//   useEffect(() => {
//     localStorage.setItem("sidebarOpen", JSON.stringify(isSidebarOpen));
//   }, [isSidebarOpen]);

//   const handleSelectConversation = (conversationId) => {
//     setCurrentConversationId(conversationId);
//   };

//   const toggleSidebar = () => {
//     setIsSidebarOpen(!isSidebarOpen);
//   };

//   return (
//     <div className={styles.container}>
//       {session && (
//         <Sidebar
//           onSelectConversation={handleSelectConversation}
//           currentConversationId={currentConversationId}
//           isOpen={isSidebarOpen}
//           onClose={toggleSidebar}
//         />
//       )}

//       <div className={`${isSidebarOpen && session ? styles.chatContainer : styles.chatContainerOpen}`}>
//         {!isSidebarOpen && (
//           <button className={styles.openButton} onClick={toggleSidebar} aria-label="Open sidebar">
//             ☰
//           </button>
//         )}
//         <AgentSection
//           currentConversationId={currentConversationId}
//           onConversationChange={handleSelectConversation}
//           isPublicMode={isPublicMode}
//         />
//       </div>
//     </div>
//   );
// }
