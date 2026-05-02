"""
Utilitaires pour la génération du planning journalier.

Chaque opérateur a son propre shift :
  - matin      : 06h → 14h
  - normal     : 08h → 17h
  - apres_midi : 14h → 22h

Les gammes s'enchaînent sans vide à partir du début du shift.
L'opérateur peut les réordonner (champ 'ordre' de TachePlanifiee).
"""

from datetime import datetime, timedelta
from django.utils import timezone
from .models import GammeOperation, PlanningJournalier, TachePlanifiee


def _make_aware(date, heure, minute):
    """
    Crée un datetime timezone-aware pour une date + heure donnée.
    Exemple : _make_aware(today, 6, 0) → 2026-04-22 06:00:00+01:00
    """
    return timezone.make_aware(datetime(date.year, date.month, date.day, heure, minute))


def generer_planning_journalier(operateur, date_travail):
    """
    Génère (ou régénère) le planning d'un opérateur pour une journée.

    Principe :
      1. Supprime l'ancien planning du jour s'il existe
      2. Récupère les gammes assignées à cet opérateur, triées par 'ordre'
      3. Les enchaîne en respectant leur durée exacte (en minutes)
      4. Démarre à: heure_debut_shift + 30 minutes
      5. Crée une TachePlanifiee pour chaque gamme

    Retourne : l'instance PlanningJournalier créée
    """
    # Supprime l'ancien planning pour éviter les doublons
    PlanningJournalier.objects.filter(operateur=operateur, date=date_travail).delete()

    # Crée le nouveau planning vide
    planning = PlanningJournalier.objects.create(operateur=operateur, date=date_travail)

    # Récupère les gammes assignées à cet opérateur, triées par ordre
    gammes = list(
        GammeOperation.objects.filter(operateurs=operateur).order_by('ordre')
    )

    # ✅ CORRECTION: Récupère l'heure de début du shift de l'opérateur
    h_debut, m_debut = operateur.shift_debut_hm
    
    # ✅ CORRECTION: Démarre à heure_debut_shift + 30 minutes
    heure_courante = _make_aware(date_travail, h_debut, m_debut) + timedelta(minutes=30)

    # On crée les tâches en les enchaînant sans vide
    for index, gamme in enumerate(gammes):
        # ✅ Durée de cette gamme (en heures décimaux → minutes)
        # Exemple: temps_alloue = 1.005 heures = 1 heure + 0.3 minutes = 60.3 minutes
        temps_minutes = float(gamme.temps_alloue) * 60
        duree = timedelta(minutes=temps_minutes)

        # Heure de fin = heure de début + durée (respecte la durée réelle)
        heure_fin = heure_courante + duree

        # Crée la tâche planifiée
        TachePlanifiee.objects.create(
            planning=planning,
            type_tache='operation',
            gamme_operation=gamme,
            ordre=index + 1,             # ordre commence à 1
            heure_debut_prevue=heure_courante,
            heure_fin_prevue=heure_fin,
        )

        # ✅ La prochaine tâche commence où finit celle-ci (pas de vide entre les tâches)
        heure_courante = heure_fin

    return planning


def build_timeline_data(planning):
    """
    Prépare les données de la timeline pour le template.

    La timeline va du DÉBUT au FIN du shift de l'opérateur.
    Chaque tâche est positionnée en % sur cet axe.

    Retourne un dict avec :
      - taches_display  : liste de tâches enrichies (position left%, largeur width%)
      - now_pct         : position actuelle en % sur la timeline
      - shift_start_min : début du shift en minutes depuis minuit
      - shift_duree_min : durée totale du shift en minutes
      - maintenant      : datetime courant
      - tache_attendue  : la tâche qui devrait être en cours maintenant
    """
    operateur      = planning.operateur
    shift_start    = operateur.shift_debut_minutes      # ex: 360 pour 06h
    shift_duree    = operateur.shift_duree_minutes      # ex: 480 pour 8h de shift
    maintenant     = timezone.now()

    def to_pct(dt):
        """Convertit un datetime en pourcentage sur la timeline du shift"""
        # Calcule le nombre de minutes depuis minuit AUJOURD'HUI
        minutes_depuis_minuit = dt.hour * 60 + dt.minute + (dt.second / 60)
        # Calcule le pourcentage: (position - début du shift) / durée du shift * 100
        pct = (minutes_depuis_minuit - shift_start) / shift_duree * 100
        # Retourne le % clamé entre 0 et 100 (ne dépasse pas la timeline)
        return max(0, min(100, round(pct, 2)))

    def duree_pct(debut_dt, fin_dt):
        """Convertit une durée (fin-debut) en pourcentage de la timeline"""
        secondes = (fin_dt - debut_dt).total_seconds()
        pct = (secondes / 60) / shift_duree * 100
        return max(0.5, round(pct, 2))  # minimum 0.5% pour rester visible

    # Position de la ligne "maintenant" sur la timeline
    now_pct = to_pct(maintenant)

    # Construction des données enrichies pour chaque tâche
    taches_display = []
    tache_attendue = None

    for tache in planning.taches.filter(type_tache='operation').order_by('ordre'):
        left_pct  = to_pct(tache.heure_debut_prevue)
        width_pct = duree_pct(tache.heure_debut_prevue, tache.heure_fin_prevue)
        ecart     = tache.ecart_fin_minutes

        taches_display.append({
            'tache'     : tache,
            'nom'       : tache.nom_affichage,
            'statut'    : tache.statut,
            'couleur'   : tache.couleur_statut,
            'left_pct'  : left_pct,
            'width_pct' : width_pct,
            'debut_str' : tache.heure_debut_prevue.strftime('%H:%M'),
            'fin_str'   : tache.heure_fin_prevue.strftime('%H:%M'),
            'ecart'     : ecart,
            'ecart_label': (f'+{ecart} min' if ecart and ecart > 0
                            else f'{ecart} min' if ecart is not None else None),
        })

        # Détecte la tâche en cours (la ligne "maintenant" est dessus)
        if tache.heure_debut_prevue <= maintenant < tache.heure_fin_prevue:
            tache_attendue = {'type': 'operation', 'nom': tache.nom_affichage, 'tache': tache}

    # Axe horaire : marques toutes les heures sur la timeline
    # On génère les heures entre début et fin du shift
    h_debut, m_debut = operateur.shift_debut_hm
    h_fin,   m_fin   = operateur.shift_fin_hm
    timeline_hours = []
    for h in range(h_debut, h_fin + 1):
        pct = ((h * 60 - shift_start) / shift_duree) * 100
        if 0 <= pct <= 100:
            timeline_hours.append({'h': h, 'pct': round(pct, 2)})

    return {
        'taches_display'  : taches_display,
        'now_pct'         : now_pct,
        'maintenant'      : maintenant,
        'tache_attendue'  : tache_attendue,
        'shift_start_min' : shift_start,
        'shift_duree_min' : shift_duree,
        'timeline_hours'  : timeline_hours,
    }
