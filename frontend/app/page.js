import AgentSection from "@/components/AgentSection/AgentSection";
import Auth from "@/components/Auth/Auth";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.page}>
      <Auth />
      <AgentSection />
    </main>
  );
}
