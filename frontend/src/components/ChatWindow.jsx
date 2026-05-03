import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./ChatWindow.module.css";

function SourceBadge({ source }) {
  return (
    <span className={styles.badge} title={`Line ~${source.start_line}`}>
      📄 {source.path} <span className={styles.line}>:{source.start_line}</span>
      <span className={styles.score}>{source.score}</span>
    </span>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`${styles.msgRow} ${isUser ? styles.userRow : styles.botRow}`}>
      <div className={styles.avatar}>{isUser ? "👤" : "🔮"}</div>
      <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.botBubble}`}>
        {isUser ? (
          <p className={styles.userText}>{msg.content}</p>
        ) : (
          <>
            <div className={styles.markdown}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
            {msg.sources?.length > 0 && (
              <div className={styles.sources}>
                <span className={styles.sourcesLabel}>Sources:</span>
                {msg.sources.map((s, i) => <SourceBadge key={i} source={s} />)}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className={`${styles.msgRow} ${styles.botRow}`}>
      <div className={styles.avatar}>🔮</div>
      <div className={`${styles.bubble} ${styles.botBubble} ${styles.typing}`}>
        <span /><span /><span />
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  return (
    <div className={styles.window}>
      {messages.length === 0 && (
        <div className={styles.empty}>
          <p>Ask anything about the repository 👆</p>
          <div className={styles.suggestions}>
            {["Explain this project", "How can I add authentication?", "Where is error handling done?", "How do I add a new API endpoint?", "What is the folder structure?"].map((s) => (
              <span key={s} className={styles.suggestion}>{s}</span>
            ))}
          </div>
        </div>
      )}
      {messages.map((msg, i) => <Message key={i} msg={msg} />)}
      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
