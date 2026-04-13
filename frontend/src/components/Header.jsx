import styles from "./Header.module.css";

export default function Header({ repoUrl, onReset }) {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <span className={styles.icon}>🔮</span>
        <span className={styles.title}>CodeSage <span className={styles.ai}>AI</span></span>
      </div>
      {repoUrl && (
        <div className={styles.repoInfo}>
          <span className={styles.dot} />
          <span className={styles.repoUrl}>{repoUrl}</span>
          <button className={styles.resetBtn} onClick={onReset}>Change Repo</button>
        </div>
      )}
    </header>
  );
}
