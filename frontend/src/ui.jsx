import { createContext, useCallback, useEffect, useState } from "react";
import { get } from "./api";
export const Say = createContext(() => {});
export function useGet(path) {
  const [d, setD] = useState(null);
  const load = useCallback(() => { if (path) get(path).then(setD).catch(() => setD(null)); }, [path]);
  useEffect(load, [load]);
  return [d, load];
}
export const Steps = ({ items, current }) => (
  <ol className="steps" aria-label="Étapes">{items.map((s, i) => <li key={s} className={i === current ? "on" : i < current ? "done" : ""}>{s}</li>)}</ol>);
export const Empty = ({ children }) => <div className="empty">{children}</div>;
export const confirmer = (msg = "Voulez-vous vraiment supprimer cet élément ?") => window.confirm(msg);
