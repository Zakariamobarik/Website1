from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime, time

# ─── Opérateur ───────────────────────────────────────────────
class Operateur(models.Model):
    """
    Représente un opérateur de production.
    Chaque opérateur a un shift qui définit ses heures de travail.
    """

    # ── Les 3 types de shifts disponibles ────────────────────────
    # Format: ('valeur_en_bd', 'texte_affiché_à_lutilisateur')
    SHIFT_CHOICES = [
        ('matin',      'Matin      (06h → 14h)'),
        ('normal',     'Normal     (08h → 17h)'),
        ('apres_midi', 'Après-midi (14h → 22h)'),
    ]

    nom    = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    poste  = models.IntegerField(null=True, blank=True)

    # ── NOUVEAU champ: le shift de l'opérateur ──────────────────
    # blank=False → obligatoire, on doit toujours choisir un shift
    shift  = models.CharField(
        max_length=20,
        choices=SHIFT_CHOICES,
        default='normal',
        verbose_name="Type de shift"
    )

    user   = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operateur_profil',
        verbose_name="Compte utilisateur"
    )
    photo_profil = models.ImageField(
    upload_to='operateurs/photos/',
    null=True,
    blank=True,
    verbose_name="Photo de profil"
)

    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    # ✅ PROPRIÉTÉ 1: Heure et minute de début du shift
    @property
    def shift_debut_hm(self):
        """
        Retourne (heure, minute) de début du shift
        Exemple: shift='matin' → (6, 0) pour 06h00
        """
        # Dictionnaire avec les horaires de chaque shift
        shift_times = {
            'matin':      (6, 0),        # 06h00 le matin
            'normal':     (8, 0),        # 08h00 (shift normal)
            'apres_midi': (14, 0),       # 14h00 (après-midi)
        }
        return shift_times.get(self.shift, (8, 0))
    
    # ✅ PROPRIÉTÉ 2: Heure et minute de fin du shift
    @property
    def shift_fin_hm(self):
        """
        Retourne (heure, minute) de fin du shift
        Exemple: shift='matin' → (14, 0) pour 14h00
        """
        # Dictionnaire avec l'heure de fin de chaque shift
        shift_times = {
            'matin':      (14, 0),       # Finit à 14h00
            'normal':     (17, 0),       # Finit à 17h00
            'apres_midi': (22, 0),       # Finit à 22h00
        }
        return shift_times.get(self.shift, (17, 0))
    
    # ✅ PROPRIÉTÉ 3: Minutes depuis minuit du début du shift
    @property
    def shift_debut_minutes(self):
        """
        Retourne le nombre de minutes depuis minuit pour le début du shift
        Exemple: (6, 0) → 360 minutes (6 heures * 60 minutes)
        """
        h, m = self.shift_debut_hm
        return h * 60 + m
    
    # ✅ PROPRIÉTÉ 4: Durée totale du shift en minutes
    @property
    def shift_duree_minutes(self):
        """
        Retourne la durée totale du shift en minutes
        Exemple: 'matin' (6h à 14h) → 480 minutes (8 heures)
        """
        h_debut, m_debut = self.shift_debut_hm
        h_fin, m_fin = self.shift_fin_hm
        
        # Convertir en minutes depuis minuit
        debut_minutes = h_debut * 60 + m_debut
        fin_minutes = h_fin * 60 + m_fin
        
        # Retourner la différence (durée totale)
        return fin_minutes - debut_minutes

# ─── Gamme opératoire ─────────────────────────────────────────
class GammeOperation(models.Model):
    nom           = models.CharField(max_length=200)
    temps_alloue  = models.DecimalField(max_digits=7, decimal_places=4, help_text="Durée en heures (ex: 1.005)")
    ordre         = models.PositiveSmallIntegerField(help_text="Position dans la gamme")
    
    # Un opérateur peut faire plusieurs gammes
    # Une gamme peut être faite par plusieurs opérateurs
    operateurs    = models.ManyToManyField(
        'Operateur',
        blank=True,
        related_name='gammes',
        verbose_name="Opérateurs assignés"
    )

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f" {self.nom} ({self.temps_alloue} min)"
    


# ─── Planning journalier ──────────────────────────────────────
class PlanningJournalier(models.Model):
    """Planning d'un opérateur pour une journée de travail (shift 06h–14h)"""
    operateur = models.ForeignKey(Operateur, on_delete=models.CASCADE, related_name='plannings')
    date      = models.DateField()
    cree_le   = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('operateur', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"Planning {self.operateur} — {self.date}"

    @property
    def taches_ordonnees(self):
        return self.taches.all().order_by('ordre')

    @property
    def taches_operations(self):
        return self.taches.filter(type_tache='operation').order_by('ordre')

    def get_tache_en_cours_prevue(self, moment=None):
        """Retourne la tâche attendue à un instant donné (en tenant compte des pauses fixes)."""
        if moment is None:
            moment = timezone.now()
        date = self.date
        sqa_start  = timezone.make_aware(datetime.combine(date, time(9, 0)))
        sqa_end    = timezone.make_aware(datetime.combine(date, time(9, 30)))
        dej_start  = timezone.make_aware(datetime.combine(date, time(11, 0)))
        dej_end    = timezone.make_aware(datetime.combine(date, time(11, 30)))
        if sqa_start <= moment < sqa_end:
            return {'type': 'pause_sqa', 'nom': 'Pause SQA', 'tache': None}
        if dej_start <= moment < dej_end:
            return {'type': 'pause_dejeuner', 'nom': 'Pause Déjeuner', 'tache': None}
        for tache in self.taches.filter(type_tache='operation').order_by('ordre'):
            if tache.heure_debut_prevue <= moment < tache.heure_fin_prevue:
                return {'type': 'operation', 'nom': tache.nom_affichage, 'tache': tache}
        return None

    @property
    def avancement(self):
        """Pourcentage de tâches opérations terminées."""
        ops = list(self.taches.filter(type_tache='operation'))
        if not ops:
            return 0
        terminees = sum(1 for t in ops if t.statut == 'termine')
        return round(terminees / len(ops) * 100)

    @property
    def retard_global_minutes(self):
        """Retard global cumulé des tâches terminées (positif = retard)."""
        total = 0
        for tache in self.taches.filter(type_tache='operation'):
            e = tache.ecart_fin_minutes
            if e is not None:
                total += e
        return total


# ─── Tâche planifiée ──────────────────────────────────────────
class TachePlanifiee(models.Model):
    TYPE_TACHE = [
        ('operation',       'Opération de travail'),
        ('pause_sqa',       'Pause SQA'),
        ('pause_dejeuner',  'Pause Déjeuner'),
    ]

    planning           = models.ForeignKey(PlanningJournalier, on_delete=models.CASCADE, related_name='taches')
    type_tache         = models.CharField(max_length=20, choices=TYPE_TACHE)
    gamme_operation    = models.ForeignKey(GammeOperation, null=True, blank=True, on_delete=models.SET_NULL)
    ordre              = models.PositiveSmallIntegerField()
    heure_debut_prevue = models.DateTimeField()
    heure_fin_prevue   = models.DateTimeField()
    heure_fin_reelle   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.nom_affichage} — {self.planning.date}"

    @property
    def nom_affichage(self):
        if self.type_tache == 'pause_sqa':
            return 'Pause SQA'
        if self.type_tache == 'pause_dejeuner':
            return 'Pause Déjeuner'
        return self.gamme_operation.nom if self.gamme_operation else 'Opération'

    @property
    def est_pause(self):
        return self.type_tache in ('pause_sqa', 'pause_dejeuner')

    @property
    def duree_prevue_minutes(self):
        delta = self.heure_fin_prevue - self.heure_debut_prevue
        return round(delta.total_seconds() / 60)

    @property
    def duree_reelle_minutes(self):
        if self.heure_debut_reelle and self.heure_fin_reelle:
            delta = self.heure_fin_reelle - self.heure_debut_reelle
            return round(delta.total_seconds() / 60)
        return None

    @property
    def statut(self):
        if self.est_pause:
            return 'pause'
        if self.heure_fin_reelle:
            return 'termine'
        now = timezone.now()
        if now >= self.heure_debut_prevue:
            return 'en cours'
        return 'en_attente'

    @property
    def ecart_debut_minutes(self):
        """Retard (+) ou avance (-) au démarrage."""
        if not self.heure_debut_reelle:
            return None
        delta = self.heure_debut_reelle - self.heure_debut_prevue
        return round(delta.total_seconds() / 60)

    @property
    def ecart_fin_minutes(self):
        """Retard (+) ou avance (-) à la fin."""
        if not self.heure_fin_reelle:
            return None
        delta = self.heure_fin_reelle - self.heure_fin_prevue
        return round(delta.total_seconds() / 60)

    @property
    def couleur_statut(self):
        s = self.statut
        if s == 'termine':
            return 'success'
        if s == 'en_cours':
            return 'primary'
        if s == 'en_retard_demarrage':
            return 'danger'
        if s == 'pause':
            return 'warning'
        return 'secondary'



# ─── Ordre de Fabrication (SIMPLIFIÉ) ──────────────────────────────
class OrdreFabrication(models.Model):
    """
    SIMPLIFIÉ:
    - Pas de date_lancement (on sait pas quand ça commence)
    - Pas de date_due (on sait pas la date de livraison à l'avance)
    - Pas de statut (calculé automatiquement)
    - Pas de gamme ManyToMany (les OperationOF font le lien)
    """

    numero   = models.CharField(max_length=50, unique=True)
    produit  = models.CharField(max_length=200)
    quantite = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"OF {self.numero} — {self.produit}"

    # ✅ MÉTHODE CORRIGÉE
    @property
    def avancement(self):
        """
        Calcule le % d'avancement en comptant les opérations terminées
        """
        # Récupère toutes les opérations de cet OF
        operations = self.operationof_set.all()
        total = operations.count()
        
        if total == 0:
            return 0
        
        # Compte les opérations terminées (statut='termine')
        terminees = 0
        for op in operations:
            # ✅ On lit la @property statut, on ne la filtre pas
            if op.statut == 'termine':
                terminees += 1
        
        # Retourne le pourcentage
        return round((terminees / total) * 100)

    @property
    def premiere_entree(self):
        """Date d'entrée de la première opération"""
        first = self.operationof_set.order_by('gamme_operation__ordre').first()
        return first.date_entree if first else None

    @property
    def derniere_sortie(self):
        """Date de sortie de la dernière opération"""
        last = self.operationof_set.order_by('gamme_operation__ordre').last()
        return last.date_sortie if last else None

    @property
    def temps_total_reel(self):
        """Calcule le temps TOTAL réel de production"""
        if self.premiere_entree and self.derniere_sortie:
            delta = self.derniere_sortie - self.premiere_entree
            return round(delta.total_seconds() / 60)
        return None

    # ✅ AJOUTER CES 3 PROPRIÉTÉS:
    @property
    def temps_total_theorique(self):
        """
        Temps THÉORIQUE = somme de tous les temps alloués
        C'est le temps idéal sans retards
        """
        operations = self.operationof_set.all()
        
        if not operations.exists():
            return 0
        
        total = 0
        for op in operations:
            total += float(op.gamme_operation.temps_alloue)
        
        return round(total)

    @property
    def heure_fin_prevue(self):
        """
        Heure de fin PRÉVUE = première entrée + temps théorique
        """
        if not self.premiere_entree:
            return None
        
        temps_theo = self.temps_total_theorique
        return self.premiere_entree + timedelta(minutes=temps_theo)

    @property
    def ecart_temps(self):
        """
        ÉCART = temps réel - temps théorique
        Positif = dépassement (en retard)
        Négatif = gain de temps (en avance)
        """
        if not self.temps_total_reel:
            return None
        
        return self.temps_total_reel - self.temps_total_theorique


# ─── -----------------------------Opération d'un OF --------------------------------------------------------------------------
class OperationOF(models.Model):

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours',   'En cours'),
        ('termine',    'Terminé'),
        ('bloque',     'Bloqué'),
    ]

    of              = models.ForeignKey(OrdreFabrication, on_delete=models.CASCADE)
    gamme_operation = models.ForeignKey(GammeOperation, on_delete=models.CASCADE)
    
    date_entree     = models.DateTimeField(null=True, blank=True, help_text="Date/heure d'ENTRÉE (saisie manuelle)")
    operateur       = models.ForeignKey(Operateur, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['gamme_operation__ordre']
        unique_together = ('of', 'gamme_operation')

    def __str__(self):
        return f"{self.of.numero} / {self.gamme_operation.nom}"

    # 🔑 PROPRIÉTÉ 1: Date de sortie (CALCULÉE AUTO)
    @property
    def date_sortie(self):
        """date_sortie = date_entree + temps_alloue"""
        if not self.date_entree:
            return None
        temps_minutes = float(self.gamme_operation.temps_alloue)
        return self.date_entree + timedelta(minutes=temps_minutes)

    # 🔑 PROPRIÉTÉ 2: STATUT AUTOMATIQUE !!!
    @property
    def statut(self):
        """
        🔥 LE STATUT EST CALCULÉ AUTOMATIQUEMENT:
        
        - Si date_entree n'existe pas → 'en_attente'
        - Si l'heure actuelle < date_sortie → 'en_cours'
        - Si l'heure actuelle >= date_sortie → 'termine' ✅
        """
        from django.utils import timezone
        
        # Pas encore commencée
        if not self.date_entree:
            return 'en_attente'
        
        # Déjà commencée, on compare avec maintenant
        maintenant = timezone.now()
        
        # Si on a dépassé la date de sortie → TERMINÉE!
        if self.date_sortie and maintenant >= self.date_sortie:
            return 'termine'
        
        # Sinon, c'est en cours
        return 'en_cours'

    # 🔑 PROPRIÉTÉ 3: Temps réel en minutes
    @property
    def temps_reel_minutes(self):
        """Durée réelle"""
        if self.date_entree and self.date_sortie:
            delta = self.date_sortie - self.date_entree
            return round(delta.total_seconds() / 60)
        return None

    # 🔑 PROPRIÉTÉ 4: Est terminée ?
    @property
    def est_terminee(self):
        """Retourne True si l'opération est terminée"""
        return self.statut == 'termine'
    
    # ✅ AJOUTER: Propriété 5: retard_minutes
    @property
    def retard_minutes(self):
        """Retard = date_entree(n) - date_sortie(n-1)"""
        if not self.date_entree:
            return None
        
        operation_precedente = OperationOF.objects.filter(
            of=self.of,
            gamme_operation__ordre__lt=self.gamme_operation.ordre
        ).order_by('-gamme_operation__ordre').first()
        
        if not operation_precedente:
            return 0
        
        if not operation_precedente.date_sortie:
            return None
        
        delta = self.date_entree - operation_precedente.date_sortie
        return round(delta.total_seconds() / 60)
    
    # ✅ GARDER: Propriété 6: retard_minutes_affichage
    @property
    def retard_minutes_affichage(self):
        """Affiche le retard de l'opération suivante"""
        operation_suivante = OperationOF.objects.filter(
            of=self.of,
            gamme_operation__ordre=self.gamme_operation.ordre + 1
        ).first()
        
        if not operation_suivante:
            return None
        
        return operation_suivante.retard_minutes
    
    # ✅ GARDER: Propriété 7: statut_retard
    @property
    def statut_retard(self):
        """Retourne 'retard', 'avance', ou 'normal'"""
        r = self.retard_minutes
        if r is None:
            return None
        if r > 0:
            return 'retard'
        elif r < 0:
            return 'avance'
        else:
            return 'normal'




# ─── Aléa ─────────────────────────────────────────────────────
# ─── Cause d'un retard (table de référence) ───────────────────
class CauseRetard(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom

# ─── Enregistrement d'un retard sur une tâche ──────────────────
class Retard(models.Model):
    tache       = models.OneToOneField(TachePlanifiee, on_delete=models.CASCADE)
    cause       = models.ForeignKey(CauseRetard, on_delete=models.PROTECT, verbose_name="Cause du retard")
    duree       = models.DurationField(help_text="Durée du retard")
    description = models.TextField(blank=True, null=True, verbose_name="Description (optionnel)")
    cree_le     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Retard pour {self.tache} à cause de {self.cause}"
    
    