// Thin fetch client for the Flask backend.
const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5001";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  team: () => get("/api/team"),
  roster: () => get("/api/roster"),
  player: (id) => get(`/api/player/${id}`),
  teamWeaknesses: () => get("/api/team-weaknesses"),
  metrics: () => get("/api/metrics"),
};
