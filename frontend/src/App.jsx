import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { flush } from "./api";
import { Say } from "./ui";
import * as P from "./pages";

const NAV = [["/", "🏠", "Tableau de bord"], ["/preparation", "📝", "Préparation"], ["/classes", "🏫", "Mes classes"],
  ["/evaluations", "📊", "Évaluations"], ["/fiches", "📚", "Mes fiches"], ["/eleves", "👨🏾‍🎓", "Mes élèves"], ["/parametres", "⚙️", "Paramètres"]];

export default function App() {
  const [auth, setAuth] = useState(!!localStorage.getItem("token"));
  const [online, setOnline] = useState(navigator.onLine), [sync, setSync] = useState(false), [toast, setToast] = useState(null);
  const say = (m) => { setToast(m); setTimeout(() => setToast(null), 3500); };
  useEffect(() => {
    const on = async () => { setOnline(true); setSync(true); const n = await flush(); setSync(false); if (n) say("✅ Enregistrement réussi — données synchronisées"); };
    const off = () => { setOnline(false); say("⚠️ Connexion interrompue"); };
    addEventListener("online", on); addEventListener("offline", off);
    return () => { removeEventListener("online", on); removeEventListener("offline", off); };
  }, []);
  if (!auth) return <P.Login onDone={() => setAuth(true)} />;
  return (
    <Say.Provider value={say}>
      <div className="shell">
        <nav className="side" aria-label="Navigation principale">
          <div className="brand">Assistant Enseignant</div>
          {NAV.map(([to, ic, l]) => <NavLink key={to} to={to} end={to === "/"}><span aria-hidden>{ic}</span> {l}</NavLink>)}
        </nav>
        <main>
          <div className={"conn " + (online ? "ok" : "off")} role="status">
            {sync ? "🔄 Synchronisation en cours" : online ? "🟢 En ligne" : "🟠 Hors connexion — les données seront synchronisées lorsque la connexion reviendra."}
          </div>
          <Routes>
            <Route path="/" element={<P.Dashboard />} />
            <Route path="/preparation" element={<P.Preparation />} />
            <Route path="/fiches" element={<P.Fiches />} />
            <Route path="/fiches/:id" element={<P.Fiche />} />
            <Route path="/classes" element={<P.Classes />} />
            <Route path="/classes/:id" element={<P.Classe />} />
            <Route path="/classes/:id/evaluations/nouvelle" element={<P.NouvelleEval />} />
            <Route path="/classes/:id/appreciations" element={<P.Appreciations />} />
            <Route path="/classes/:id/verification" element={<P.Verification />} />
            <Route path="/classes/:id/bulletin" element={<P.Bulletin />} />
            <Route path="/evaluations" element={<P.Evaluations />} />
            <Route path="/evaluations/:id/notes" element={<P.Notes />} />
            <Route path="/evaluations/:id/resultats" element={<P.Resultats />} />
            <Route path="/eleves" element={<P.Eleves />} />
            <Route path="/eleves/:id" element={<P.Eleve />} />
            <Route path="/parametres" element={<P.Parametres onLogout={() => setAuth(false)} />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
        {toast && <div className="toast" role="alert">{toast}</div>}
      </div>
    </Say.Provider>
  );
}
