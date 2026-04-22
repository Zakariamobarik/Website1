"""
Utilitaires pour la génération et le suivi du planning journalier des opérateurs.

Shift : 06h00 – 14h00
Pauses fixes :
  • SQA       : 09h00 – 09h30  (30 min)
  • Déjeuner  : 11h00 – 11h30  (30 min)

Algorithme de génération :
  - Les opérations sont enchaînées à partir de 06h00.
  - Si une opération recouvre l'heure d'une pause, la durée de la pause
    est ajoutée à l'heure de fin de cette opération (le bloc "opération"
    intègre la coupure ; la pause est visible dans la visualisation).
  - Si une pause survient entre deux opérations, elle est insérée
    en tant que tâche distincte.
"""

from datetime import datetime, timedelta, time as dt_time

from django.utils import timezone

from .models import GammeOperation, PlanningJournalier, TachePlanifiee

# ─── Constantes shift ────────────────────────────────────────────────────────
SHIFT_START   = dt_time(6,  0)
PAUSE_SQA_START  = dt_time(9,  0)
PAUSE_SQA_END    = dt_time(9, 30)
PAUSE_DEJ_START  = dt_time(11, 0)
PAUSE_DEJ_END    = dt_time(11, 30)


def _make_aware(date, h, m, s=0):
    """Crée un datetime timezone-aware pour la date et l'heure données."""
    return timezone.make_aware(datetime(date.year, date.month, date.day, h, m, s))


def generer_planning_journalier(operateur, date_travail):
    """
    Génère (ou régénère) le planning journalier d'un opérateur.

    - Supprime le planning existant pour ce couple (operateur, date).
    - Enchaîne les opérations assignées à l'opérateur (gammes triées par ordre).
    - Insère automatiquement les pauses aux bons endroits.

    Retourne l'instance PlanningJournalier créée.
    """
    sqa_start = _make_aware(date_travail, 9,  0)
    sqa_end   = _make_aware(date_travail, 9, 30)
    dej_start = _make_aware(date_travail, 11, 0)
    dej_end   = _make_aware(date_travail, 11, 30)

    # Supprime l'ancien planning pour cette journée
    PlanningJournalier.objects.filter(operateur=operateur, date=date_travail).delete()

    planning = PlanningJournalier.objects.create(operateur=operateur, date=date_travail)

    gammes = list(GammeOperation.objects.filter(operateur=operateur).order_by('ordre'))

    current  = _make_aware(date_travail, 6, 0)
    sqa_done = False
    dej_done = False
    ordre    = 1
    taches   = []   # liste de dicts à créer en bulk

    def enqueue_break(type_tache, b_start, b_end):
        nonlocal ordre
        taches.append(dict(
            planning=planning,
            type_tache=type_tache,
            gamme_operation=None,
            ordre=ordre,
            heure_debut_prevue=b_start,
            heure_fin_prevue=b_end,
        ))
        ordre += 1

    for gamme in gammes:
        duree    = timedelta(hours=float(gamme.temps_alloue))
        task_end = current + duree

        # ── Pause SQA ──────────────────────────────────────────────────────────
        if not sqa_done:
            if current >= sqa_start:
                # Heure actuelle déjà passée SQA : insérer la pause et décaler
                enqueue_break('pause_sqa', sqa_start, sqa_end)
                sqa_done = True
                if current < sqa_end:
                    current  = sqa_end
                task_end = current + duree

            elif current < sqa_start <= task_end:
                # La tâche chevauche la pause SQA : prolonger l'heure de fin
                task_end += (sqa_end - sqa_start)
                sqa_done = True

        # ── Pause Déjeuner ────────────────────────────────────────────────────
        if not dej_done:
            if current >= dej_start:
                enqueue_break('pause_dejeuner', dej_start, dej_end)
                dej_done = True
                if current < dej_end:
                    current  = dej_end
                task_end = current + duree

            elif current < dej_start <= task_end:
                task_end += (dej_end - dej_start)
                dej_done = True

        # ── Créer la tâche opération ──────────────────────────────────────────
        taches.append(dict(
            planning=planning,
            type_tache='operation',
            gamme_operation=gamme,
            ordre=ordre,
            heure_debut_prevue=current,
            heure_fin_prevue=task_end,
        ))
        ordre   += 1
        current  = task_end

    # Pauses restantes non encore insérées (toutes les opérations terminent avant 09h ou 11h)
    if not sqa_done:
        enqueue_break('pause_sqa', sqa_start, sqa_end)
    if not dej_done:
        enqueue_break('pause_dejeuner', dej_start, dej_end)

    for t in taches:
        TachePlanifiee.objects.create(**t)

    return planning


def get_tache_attendue(planning, moment=None):
    """
    Retourne un dict décrivant la tâche attendue à l'instant `moment`.

    Structure du résultat :
        {
          'type'    : 'operation' | 'pause_sqa' | 'pause_dejeuner' | 'avant_shift' | 'apres_shift',
          'nom'     : str,
          'tache'   : TachePlanifiee | None,
        }
    """
    if moment is None:
        moment = timezone.now()

    date      = planning.date
    sqa_start = _make_aware(date, 9,  0)
    sqa_end   = _make_aware(date, 9, 30)
    dej_start = _make_aware(date, 11, 0)
    dej_end   = _make_aware(date, 11, 30)
    shift_start = _make_aware(date, 6,  0)
    shift_end   = _make_aware(date, 14, 0)

    if moment < shift_start:
        return {'type': 'avant_shift', 'nom': 'Avant le shift', 'tache': None}

    if sqa_start <= moment < sqa_end:
        return {'type': 'pause_sqa', 'nom': 'Pause SQA', 'tache': None}

    if dej_start <= moment < dej_end:
        return {'type': 'pause_dejeuner', 'nom': 'Pause Déjeuner', 'tache': None}

    for tache in planning.taches.filter(type_tache='operation').order_by('ordre'):
        if tache.heure_debut_prevue <= moment < tache.heure_fin_prevue:
            return {'type': 'operation', 'nom': tache.nom_affichage, 'tache': tache}

    if moment >= shift_end:
        return {'type': 'apres_shift', 'nom': 'Fin de shift', 'tache': None}

    return {'type': 'inconnu', 'nom': '—', 'tache': None}


def build_timeline_data(planning):
    """
    Prépare les données de la timeline pour le template.

    Retourne un dict avec :
    - taches_display : liste de dicts enrichis (position/largeur en %)
    - pauses_display : liste des 2 pauses fixes (idem)
    - now_pct        : position de l'instant présent en %
    - shift_start_min, shift_end_min : bornes absolues en minutes depuis minuit
    - maintenant     : datetime courant
    - tache_attendue : résultat de get_tache_attendue()
    """
    SHIFT_START_MIN = 6  * 60   # 360 min depuis minuit
    SHIFT_END_MIN   = 14 * 60   # 840 min depuis minuit
    SHIFT_TOTAL     = SHIFT_END_MIN - SHIFT_START_MIN  # 480 min

    def to_pct(dt):
        minutes = dt.hour * 60 + dt.minute + dt.second / 60
        return max(0, min(100, (minutes - SHIFT_START_MIN) / SHIFT_TOTAL * 100))

    def duration_pct(start_dt, end_dt):
        seconds = (end_dt - start_dt).total_seconds()
        return max(0.5, seconds / 60 / SHIFT_TOTAL * 100)

    maintenant  = timezone.now()
    now_pct     = to_pct(maintenant)
    date        = planning.date

    pauses_display = [
        {
            'type'      : 'pause_sqa',
            'nom'       : 'Pause SQA',
            'heure'     : '09:00–09:30',
            'left_pct'  : to_pct(_make_aware(date, 9,  0)),
            'width_pct' : 30 / SHIFT_TOTAL * 100,
        },
        {
            'type'      : 'pause_dejeuner',
            'nom'       : 'Pause Déjeuner',
            'heure'     : '11:00–11:30',
            'left_pct'  : to_pct(_make_aware(date, 11, 0)),
            'width_pct' : 30 / SHIFT_TOTAL * 100,
        },
    ]

    taches_display = []
    for tache in planning.taches.filter(type_tache='operation').order_by('ordre'):
        left_pct  = to_pct(tache.heure_debut_prevue)
        width_pct = duration_pct(tache.heure_debut_prevue, tache.heure_fin_prevue)
        ecart     = tache.ecart_fin_minutes
        taches_display.append({
            'tache'           : tache,
            'nom'             : tache.nom_affichage,
            'statut'          : tache.statut,
            'couleur'         : tache.couleur_statut,
            'left_pct'        : round(left_pct, 2),
            'width_pct'       : round(width_pct, 2),
            'debut_prevu_str' : tache.heure_debut_prevue.strftime('%H:%M'),
            'fin_prevue_str'  : tache.heure_fin_prevue.strftime('%H:%M'),
            'ecart_minutes'   : ecart,
            'ecart_label'     : (f'+{ecart} min' if ecart and ecart > 0
                                 else f'{ecart} min' if ecart is not None
                                 else None),
        })

    tache_attendue = get_tache_attendue(planning, maintenant)

    # Axe horaire (6h à 14h, soit 9 marques)
    timeline_hours = [
        {'h': h, 'pct': round((h * 60 - SHIFT_START_MIN) / SHIFT_TOTAL * 100, 2)}
        for h in range(6, 15)
    ]

    return {
        'taches_display'   : taches_display,
        'pauses_display'   : pauses_display,
        'now_pct'          : round(now_pct, 2),
        'maintenant'       : maintenant,
        'tache_attendue'   : tache_attendue,
        'shift_start_min'  : SHIFT_START_MIN,
        'shift_end_min'    : SHIFT_END_MIN,
        'timeline_hours'   : timeline_hours,
    }
