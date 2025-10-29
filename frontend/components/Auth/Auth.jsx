"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import Image from "next/image";
import styles from "./Auth.module.css";

export default function Auth() {
  const { data: session } = useSession();

  return (
    <div className={styles.container}>
      {!session ? (
        <>
          <div className={styles.user}></div>
          <button className={styles.button} onClick={() => signIn("google")}>
            Sign in
          </button>
        </>
      ) : (
        <>
          <div className={styles.user}>
            {session.user?.image && (
              <Image src={session.user.image} alt="User avatar" width={40} height={40} className={styles.avatar} />
            )}
            <p className={styles.text}>Hello, {session.user?.name}</p>
          </div>
          <button className={styles.button} onClick={() => signOut()}>
            Sign out
          </button>
        </>
      )}
    </div>
  );
}
