import AgentWorkspace from "@/components/AgentWorkspace/AgentWorkspace";
import Auth from "@/components/Auth/Auth";
import styles from "./page.module.css";

export default async function Home({ params }) {
  const { id } = await params;
  const conversationId = id;

  return (
    <main className={styles.page}>
      <Auth />
      <AgentWorkspace initialConversationId={conversationId} isPublicMode={true} />
    </main>
  );
}
