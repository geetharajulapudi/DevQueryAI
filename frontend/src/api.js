import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });

export const getStatus = () => api.get("/status");
export const ingestRepo = (repo_url) => api.post("/ingest", { repo_url });
export const queryRepo = (query) => api.post("/query", { query });
export const resetSession = () => api.post("/reset");
