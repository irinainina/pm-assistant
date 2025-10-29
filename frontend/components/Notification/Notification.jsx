"use client";

import { useEffect } from "react";
import styles from "./Notification.module.css";

export default function Notification({ message, isVisible, onClose }) {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  return (
    <div className={styles.notification}>
      <span>{message}</span>
    </div>
  );
}
