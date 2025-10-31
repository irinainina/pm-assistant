import styles from "./DeleteConfirmationModal.module.css";

export default function DeleteConfirmationModal({ isOpen, onClose, onConfirm, chatTitle }) {
  if (!isOpen) return null;

  return (
    <div className={styles.deleteModalOverlay} onClick={onClose}>
      <div className={styles.deleteModal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.deleteModalContent}>
          <h3 className={styles.deleteModalTitle}>Delete chat?</h3>
          <p className={styles.deleteModalMessage}>Are you sure you want to delete this chat?</p>
          <div className={styles.deleteModalActions}>
            <button className={styles.deleteModalCancel} onClick={onClose}>
              Cancel
            </button>
            <button className={styles.deleteModalConfirm} onClick={onConfirm}>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
