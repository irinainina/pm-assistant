import AgentSection from "@/components/AgentSection/AgentSection";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.page}>  
      <AgentSection />
    </main>
  );
}
