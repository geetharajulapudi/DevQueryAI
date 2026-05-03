import { useState, useRef } from "react";
import Header from "./components/Header";
import RepoInput from "./components/RepoInput";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import { ingestRepo, queryRepo, resetSession, getStatus } from "./api";
import styles from "./App.module.css";

export default function App() {
  const [repoUrl, setRepoUrl] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ingestStatus, setIngestStatus] = useState("");
  const pollRef = useRef(null);

  const pollUntilReady = () => {
    return new Promise((resolve, reject) => {
      pollRef.current = setInterval(async () => {
        try {
          const { data } = await getStatus();
          if (data.status === "ready") {
            clearInterval(pollRef.current);
            resolve(data);
          } else if (data.status === "error") {
            clearInterval(pollRef.current);
            reject(new Error(data.error || "Ingestion failed"));
          } else {
            setIngestStatus("⏳ Cloning and indexing repository, please wait...");
          }
        } catch (e) {
          clearInterval(pollRef.current);
          reject(e);
        }
      }, 3000);
    });
  };

  const handleIngest = async (url) => {
    setLoading(true);
    setError(null);
    setIngestStatus("⏳ Starting ingestion...");
    try {
      await ingestRepo(url);
      await pollUntilReady();
      setRepoUrl(url);
      setMessages([{
        role: "assistant",
        content: `✅ Repository **${url}** has been indexed successfully!\n\nI've analyzed the codebase and I'm ready to answer your questions. Ask me anything — how features work, where things are implemented, or how to add new functionality.`,
      }]);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Failed to ingest repository.");
    } finally {
      setLoading(false);
      setIngestStatus("");
    }
  };

  const handleQuery = async (query) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);
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
        content: "⚠️ " + (e.response?.data?.detail || "Something went wrong."),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    clearInterval(pollRef.current);
    await resetSession().catch(() => {});
    setRepoUrl(null);
    setMessages([]);
    setError(null);
    setIngestStatus("");
  };

  return (
    <div className={styles.app}>
      <Header repoUrl={repoUrl} onReset={handleReset} />
      {!repoUrl ? (
        <>
          <RepoInput onIngest={handleIngest} loading={loading} ingestStatus={ingestStatus} />
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
