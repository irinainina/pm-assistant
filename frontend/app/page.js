import AgentWorkspace from "@/components/AgentWorkspace/AgentWorkspace";
import Auth from "@/components/Auth/Auth";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.page}>
      <Auth />
      <AgentWorkspace />
    </main>
  );
}
