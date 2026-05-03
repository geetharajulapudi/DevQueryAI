import { useState } from "react";
import styles from "./ChatInput.module.css";

export default function ChatInput({ onSend, loading }) {
  const [text, setText] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !loading) { onSend(text.trim()); setText(""); }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
  };

  return (
    <div className={styles.wrapper}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <textarea className={styles.textarea} placeholder="Ask about the codebase... (Enter to send, Shift+Enter for newline)" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={handleKeyDown} disabled={loading} rows={1} />
        <button className={styles.btn} type="submit" disabled={loading || !text.trim()}>
          {loading ? <span className={styles.spinner} /> : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </form>
      <p className={styles.hint}>Powered by Groq · llama-3.3-70b-versatile · FAISS semantic search</p>
    </div>
  );
}
