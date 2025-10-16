"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import styles from "./Auth.module.css";

export default function Auth() {
  const { data: session } = useSession();

  return (
    <div className={styles.container}>
      {!session ? (
        <>
          <p className={styles.text}>Вы не вошли</p>
          <button className={styles.button} onClick={() => signIn("google")}>
            Sign in with Google
          </button>
        </>
      ) : (
        <>
          <p className={styles.text}>Hello, {session.user?.name}</p>
          <button className={styles.button} onClick={() => signOut()}>
            Sign out
          </button>
        </>
      )}
    </div>
  );
}
