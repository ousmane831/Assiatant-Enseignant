from collections import defaultdict
from rest_framework import viewsets, routers
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from . import models as m, serializers as s

# Valeurs PROVISOIRES et modifiables par l'enseignant (Paramètres). À valider avec les sources officielles.
DEFAULTS = {
    "matieres": ["Français", "Mathématiques", "Sciences", "Histoire", "Géographie", "Éducation civique"],
    "types": ["Devoir", "Évaluation", "Composition"],
    "periodes": ["1er trimestre", "2e trimestre", "3e trimestre"],
    "canevas": ["Objectifs", "Compétences", "Prérequis", "Matériel", "Situation de départ",
                "Déroulement", "Activités", "Évaluation"],
    "classement": True, "base_moyenne": 20, "note_max_defaut": 20,
    "appreciations": [  # seuils en fraction de la base : à valider
        {"min": 0, "texte": "Besoin d'accompagnement"}, {"min": 0.4, "texte": "Résultats à surveiller"},
        {"min": 0.5, "texte": "Résultats satisfaisants"}, {"min": 0.7, "texte": "Bons résultats"}],
    "modele_bulletin": "À valider : modèle officiel non défini",
}
def cfg(user):
    p, _ = m.Parametres.objects.get_or_create(user=user)
    return {**DEFAULTS, **p.config}

class Owned(viewsets.ModelViewSet):
    owner, filters = "user", []
    def get_queryset(self):
        qs = self.queryset.filter(**{self.owner: self.request.user})
        return qs.filter(**{k: v for k, v in self.request.query_params.items() if k in self.filters and v})
    def perform_create(self, ser):
        if self.owner == "user": return ser.save(user=self.request.user)
        if ser.validated_data[self.owner.split("__")[0]].user != self.request.user: raise PermissionDenied()
        ser.save()

def moy(lst, base):  # lst = [(valeur, max, coef)] ; moyenne pondérée ramenée à la base configurée
    tot = sum(c for _, _, c in lst)
    return round(sum(v / mx * base * c for v, mx, c in lst) / tot, 2) if tot else None

def calc_classe(classe, periode, c):
    data = defaultdict(lambda: defaultdict(list))
    ns = m.Note.objects.filter(evaluation__classe=classe, evaluation__periode=periode).exclude(valeur=None).select_related("evaluation")
    for n in ns: data[n.eleve_id][n.evaluation.matiere].append((float(n.valeur), float(n.evaluation.note_max), float(n.evaluation.coefficient)))
    out = []
    for e in classe.eleves.all():
        mats = {k: moy(v, c["base_moyenne"]) for k, v in data[e.id].items()}
        vals = list(mats.values())
        out.append({"eleve": e.id, "nom": str(e), "matieres": mats, "moyenne": round(sum(vals) / len(vals), 2) if vals else None})
    if c["classement"]:
        for r, row in enumerate(sorted([o for o in out if o["moyenne"] is not None], key=lambda o: -o["moyenne"]), 1): row["rang"] = r
    return out

class ClasseV(Owned):
    queryset, serializer_class = m.Classe.objects.all(), s.ClasseS
    @action(detail=True)
    def resultats(self, req, pk=None):
        return Response(calc_classe(self.get_object(), req.query_params.get("periode", ""), cfg(req.user)))
    @action(detail=True, methods=["get", "put"])
    def appreciations(self, req, pk=None):
        cl, per = self.get_object(), req.query_params.get("periode", "")
        if req.method == "PUT":
            for r in req.data:
                if cl.eleves.filter(id=r["eleve"]).exists():
                    m.Appreciation.objects.update_or_create(eleve_id=r["eleve"], periode=per,
                        defaults={"texte": r.get("texte", ""), "validee": bool(r.get("validee"))})
        return Response({a.eleve_id: {"texte": a.texte, "validee": a.validee} for a in m.Appreciation.objects.filter(eleve__classe=cl, periode=per)})
    @action(detail=True)
    def proposer(self, req, pk=None):  # PROPOSITIONS seulement : validee=False, modifiables
        c = cfg(req.user); out = {}
        for r in calc_classe(self.get_object(), req.query_params.get("periode", ""), c):
            if r["moyenne"] is None: continue
            out[r["eleve"]] = {"texte": [a["texte"] for a in c["appreciations"] if r["moyenne"] / c["base_moyenne"] >= a["min"]][-1], "validee": False}
        return Response(out)
    @action(detail=True)
    def verification(self, req, pk=None):
        cl, per = self.get_object(), req.query_params.get("periode", "")
        evs, n_el = cl.evaluations.filter(periode=per), cl.eleves.count()
        res = calc_classe(cl, per, cfg(req.user))
        apps = m.Appreciation.objects.filter(eleve__classe=cl, periode=per, validee=True).count()
        att = n_el * evs.count()
        saisies = m.Note.objects.filter(evaluation__in=evs).exclude(valeur=None).count()
        pb = []
        if saisies < att: pb.append("Note manquante")
        if any(r["moyenne"] is None for r in res): pb.append("Élève sans résultat")
        if apps < n_el: pb.append("Information incomplète : appréciations à valider")
        vals = [r["moyenne"] for r in res if r["moyenne"] is not None]
        return Response({"eleves": n_el, "notes_saisies": saisies, "notes_attendues": att, "appreciations": apps,
            "moyenne_generale": round(sum(vals) / len(vals), 2) if vals else None, "problemes": pb, "erreurs": 0})

class EleveV(Owned): queryset, serializer_class, owner, filters = m.Eleve.objects.all(), s.EleveS, "classe__user", ["classe"]
class LeconV(Owned): queryset, serializer_class, filters = m.Lecon.objects.all(), s.LeconS, ["niveau", "matiere"]
class ExerciceV(Owned): queryset, serializer_class, owner, filters = m.Exercice.objects.all(), s.ExerciceS, "fiche__user", ["fiche"]

class FicheV(Owned):
    queryset, serializer_class = m.Fiche.objects.all(), s.FicheS
    filters = ["niveau", "matiere", "annee_scolaire", "lecon__icontains"]
    def perform_update(self, ser):
        ser.save(version_precedente=self.get_object().sections)
    @action(detail=True, methods=["post"])
    def restaurer(self, req, pk=None):
        f = self.get_object()
        if f.version_precedente is not None: f.sections, f.version_precedente = f.version_precedente, f.sections; f.save()
        return Response(s.FicheS(f).data)
    @action(detail=True, methods=["post"])
    def dupliquer(self, req, pk=None):
        f = self.get_object(); ex = list(f.exercices.all())
        f.pk, f.version_precedente, f.annee_scolaire = None, None, req.data.get("annee_scolaire", f.annee_scolaire); f.save()
        for e in ex: e.pk, e.fiche = None, f; e.save()
        return Response(s.FicheS(f).data, status=201)

class EvaluationV(Owned):
    queryset, serializer_class, owner, filters = m.Evaluation.objects.all(), s.EvaluationS, "classe__user", ["classe", "periode"]
    @action(detail=True, methods=["get", "put"])
    def notes(self, req, pk=None):
        ev = self.get_object()
        if req.method == "PUT":
            for r in req.data:
                v = r.get("valeur")
                if v not in ("", None):
                    try: v = float(str(v).replace(",", "."))
                    except ValueError: return Response({"detail": "Valeur invalide"}, 400)
                    if not 0 <= v <= float(ev.note_max): return Response({"detail": "La note doit être comprise entre 0 et %s" % ev.note_max}, 400)
                else: v = None
                if ev.classe.eleves.filter(id=r["eleve"]).exists():
                    m.Note.objects.update_or_create(evaluation=ev, eleve_id=r["eleve"], defaults={"valeur": v, "observation": r.get("observation", "")})
        ns = {n.eleve_id: n for n in ev.notes.all()}
        return Response([{"eleve": e.id, "nom": str(e), "valeur": ns[e.id].valeur if e.id in ns else None,
                          "observation": ns[e.id].observation if e.id in ns else ""} for e in ev.classe.eleves.all()])
    @action(detail=True)
    def resultats(self, req, pk=None):
        ev, c = self.get_object(), cfg(req.user)
        rows = [(n.eleve, float(n.valeur)) for n in ev.notes.exclude(valeur=None).select_related("eleve")]
        mx, vals = float(ev.note_max), [v for _, v in rows]
        dist = [0] * 4
        for v in vals: dist[min(int(v / mx * 4), 3)] += 1
        liste = [{"eleve": e.id, "nom": str(e), "note": v, "sur_base": round(v / mx * c["base_moyenne"], 2)} for e, v in rows]
        if c["classement"]:
            liste.sort(key=lambda x: -x["note"])
            for i, x in enumerate(liste, 1): x["rang"] = i
        return Response({"effectif": ev.classe.eleves.count(), "saisies": len(vals), "note_max": mx,
            "moyenne": round(sum(vals) / len(vals), 2) if vals else None, "meilleure": max(vals, default=None),
            "minimale": min(vals, default=None), "distribution": dist, "eleves": liste, "classement": c["classement"]})

router = routers.DefaultRouter()
for p, v in [("classes", ClasseV), ("eleves", EleveV), ("lecons", LeconV), ("fiches", FicheV), ("exercices", ExerciceV), ("evaluations", EvaluationV)]:
    router.register(p, v, basename=p)

@api_view(["GET"])
def me(req): return Response({"nom": req.user.get_full_name() or req.user.username})

@api_view(["GET", "PUT"])
def parametres(req):
    p, _ = m.Parametres.objects.get_or_create(user=req.user)
    if req.method == "PUT": p.config = req.data; p.save()
    return Response(cfg(req.user))
