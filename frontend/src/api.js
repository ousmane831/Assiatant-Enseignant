// Accès API + mode hors connexion : lectures mises en cache, écritures mises en file d'attente puis synchronisées.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8001/api";
export async function call(method, path, body) {
  const t = localStorage.getItem("token");
  const r = await fetch(BASE + path, { method, headers: { "Content-Type": "application/json", ...(t && { Authorization: "Token " + t }) }, body: body && JSON.stringify(body) });
  if (r.status === 401 && t) { localStorage.removeItem("token"); location.reload(); }
  if (!r.ok) throw new Error(r.status);
  return r.status === 204 ? null : r.json();
}
export async function get(path) {
  try { const d = await call("GET", path); localStorage.setItem("c:" + path, JSON.stringify(d)); return d; }
  catch (e) { const c = localStorage.getItem("c:" + path); if (c) return JSON.parse(c); throw e; }
}
export async function send(method, path, body) {
  if (!navigator.onLine) {
    localStorage.setItem("q", JSON.stringify([...JSON.parse(localStorage.getItem("q") || "[]"), { method, path, body }]));
    return { queued: true };
  }
  return call(method, path, body);
}
export async function flush() {
  const q = JSON.parse(localStorage.getItem("q") || "[]"), rest = [];
  for (const j of q) { try { await call(j.method, j.path, j.body); } catch { rest.push(j); } }
  localStorage.setItem("q", JSON.stringify(rest)); return q.length - rest.length;
}
