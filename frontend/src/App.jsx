import { useState } from "react";
import Header from "./components/Header";
import RepoInput from "./components/RepoInput";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import { ingestRepo, queryRepo, resetSession } from "./api";
import styles from "./App.module.css";

export default function App() {
  const [repoUrl, setRepoUrl] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleIngest = async (url) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await ingestRepo(url);
      setRepoUrl(data.repo_url || url);
      setMessages([{
        role: "assistant",
        content: `✅ Repository **${url}** has been indexed successfully!\n\nI've analyzed the codebase and I'm ready to answer your questions. Ask me anything — how features work, where things are implemented, or how to add new functionality.`,
      }]);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to ingest repository. Check the URL and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async (query) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);
    setError(null);
    try {
      const { data } = await queryRepo(query);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      }]);
    } catch (e) {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: "⚠️ " + (e.response?.data?.detail || "Something went wrong. Please try again."),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    await resetSession().catch(() => {});
    setRepoUrl(null);
    setMessages([]);
    setError(null);
  };

  return (
    <div className={styles.app}>
      <Header repoUrl={repoUrl} onReset={handleReset} />

      {!repoUrl ? (
        <>
          <RepoInput onIngest={handleIngest} loading={loading} />
          {error && <div className={styles.error}>{error}</div>}
        </>
      ) : (
        <div className={styles.chat}>
          <ChatWindow messages={messages} loading={loading} />
          <ChatInput onSend={handleQuery} loading={loading} />
        </div>
      )}
    </div>
  );
}
