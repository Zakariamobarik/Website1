from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date as date_type, timedelta, time
from .forms import *
from .models import *
from .planning_utils import generer_planning_journalier, build_timeline_data

# ============================================
# AUTHENTIFICATION
# ============================================

def home(request):
    """Page d'accueil - Login"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Bienvenue {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, "Identifiants invalides!")
            return redirect('home')
    else:
        return render(request, 'home.html')

def logout_user(request):
    """Déconnexion"""
    logout(request)
    messages.success(request, "Vous avez été déconnecté!")
    return redirect('home')

def register_user(request):
    """Inscription"""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "Inscription réussie! Bienvenue!")
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

# ============================================
# DASHBOARD ET PRODUCTION
# ============================================



#----------------------------Gamme opératoire--------------------------------------------------

@login_required(login_url='home')
def gammes_list(request):
    """
    Affiche la liste de toutes les gammes opératoires
    """
    gammes = GammeOperation.objects.all().order_by('ordre')
    context = {
        'gammes': gammes,
    }
    return render(request, 'gamme/gammes_list.html', context)


# Remplacer les 3 fonctions gammes par ces 2 seules fonctions

@login_required(login_url='home')
def gamme_form(request, id=None):
    """
    Ajoute ou modifie une gamme opératoire
    - Si id est None → Ajouter
    - Si id existe → Modifier
    """
    gamme = get_object_or_404(GammeOperation, id=id) if id else None
    titre = "Modifier la Gamme" if gamme else "Ajouter une Gamme"
    
    if request.method == 'POST':
        form = GammeOperationForm(request.POST, instance=gamme)
        if form.is_valid():
            form.save()
            msg = "modifiée" if gamme else "ajoutée"
            messages.success(request, f"✅ Gamme {msg} avec succès!")
            return redirect('gammes_list')
    else:
        form = GammeOperationForm(instance=gamme)
    
    return render(request, 'gamme/gamme_form.html', {'form': form, 'titre': titre, 'gamme': gamme})


@login_required(login_url='home')
def supprimer_gamme(request, id):
    """Supprime une gamme opératoire"""
    gamme = get_object_or_404(GammeOperation, id=id)
    
    if request.method == 'POST':
        gamme.delete()
        messages.success(request, "✅ Gamme supprimée!")
        return redirect('gammes_list')
    
    return render(request, 'gamme/gamme_confirm_delete.html', {'gamme': gamme})







#-----------------------------Opérateur--------------------------------------------------

@login_required(login_url='home')
def operateurs_list(request):
    """
    Affiche la liste de tous les opérateurs
    """
    operateurs = Operateur.objects.all().order_by('nom')
    
    context = {
        'operateurs': operateurs,
    }
    return render(request, 'operateur/operateur_list.html', context)


# Ajouter à la fin de views.py

@login_required(login_url='home')
def operateur_form(request, id=None):
    """
    Ajoute ou modifie un opérateur
    - Si id est None → Ajouter
    - Si id existe → Modifier
    """
    operateur = get_object_or_404(Operateur, id=id) if id else None
    titre = "Modifier l'Opérateur" if operateur else "Ajouter un Opérateur"
    
    if request.method == 'POST':
        form = OperateurForm(request.POST, instance=operateur)
        if form.is_valid():
            form.save()
            msg = "modifié" if operateur else "ajouté"
            messages.success(request, f"✅ Opérateur {msg} avec succès!")
            return redirect('operateur_list')
    else:
        form = OperateurForm(instance=operateur)
    
    return render(request, 'operateur/operateur_form.html', {'form': form, 'titre': titre, 'operateur': operateur})


@login_required(login_url='home')
def supprimer_operateur(request, id):
    """Supprime un opérateur"""
    operateur = get_object_or_404(Operateur, id=id)
    
    if request.method == 'POST':
        operateur.delete()
        messages.success(request, "✅ Opérateur supprimé!")
        return redirect('operateur/operateur_list')
    
    return render(request, 'operateur/operateur_delete.html', {'operateur': operateur})

#--------------------Ordre de fabrication ----------------------------------------------------------------------------

@login_required(login_url='home')
def of_list(request):
    """Affiche la liste de tous les OF"""
    ofs = OrdreFabrication.objects.all()
    context = {'ofs': ofs}
    return render(request, 'of/of_list.html', context)


@login_required(login_url='home')
def of_form(request, id=None):
    """Ajoute ou modifie un OF"""
    of = get_object_or_404(OrdreFabrication, id=id) if id else None
    titre = "Modifier l'OF" if of else "Ajouter un OF"
    
    if request.method == 'POST':
        form = OrdreFabricationForm(request.POST, instance=of)
        if form.is_valid():
            of = form.save()
            
            # 🔥 SI NOUVEL OF: créer automatiquement les 6 OperationOF
            if not id:  # C'est un nouvel OF
                # Récupérer toutes les opérations (gammes)
                gammes = GammeOperation.objects.all().order_by('ordre')
                for gamme in gammes:
                    # ✅ PLUS BESOIN d'assigner statut !
                    # statut est CALCULÉ AUTOMATIQUEMENT via @property
                    OperationOF.objects.create(
                        of=of,
                        gamme_operation=gamme
                        # ❌ SUPPRIMER: statut='en_attente'
                    )
                messages.success(request, f"✅ OF {of.numero} créé avec {gammes.count()} opérations!")
            else:
                messages.success(request, f"✅ OF {of.numero} modifié!")
            
            return redirect('of_list')
    else:
        form = OrdreFabricationForm(instance=of)
    
    return render(request, 'of/of_form.html', {'form': form, 'titre': titre, 'of': of})


@login_required(login_url='home')
def supprimer_of(request, id):
    """Supprime un OF"""
    of = get_object_or_404(OrdreFabrication, id=id)
    
    if request.method == 'POST':
        numero = of.numero
        of.delete()
        messages.success(request, f"✅ OF {numero} supprimé!")
        return redirect('of_list')
    
    return render(request, 'of/of_confirm_delete.html', {'of': of})


@login_required(login_url='home')
def of_detail(request, id):
    """Affiche le détail d'un OF avec sa timeline"""
    of = get_object_or_404(OrdreFabrication, id=id)
    operations = of.operationof_set.all().order_by('gamme_operation__ordre')
    
    context = {
        'of': of,
        'operations': operations,
        'avancement': of.avancement,
    }
    return render(request, 'of/of_detail.html', context)


@login_required(login_url='home')
def saisir_entree_operation(request, operation_id):
    """Saisit la date d'ENTRÉE d'une opération"""
    operation = get_object_or_404(OperationOF, id=operation_id)
    
    # Vérifier que l'opération n'a pas déjà commencé
    if operation.date_entree:
        messages.warning(request, "Cette opération a déjà une date d'entrée!")
        return redirect('of_detail', id=operation.of.id)
    
    if request.method == 'POST':
        form = EntreeOperationForm(request.POST, instance=operation)
        if form.is_valid():
            operation = form.save()  # ← Pas besoin de commit=False
            # ❌ PLUS BESOIN: operation.statut = 'en_cours'
            # ✅ Le statut est AUTOMATIQUEMENT 'en_cours' maintenant!
            
            messages.success(
                request,
                f"✅ {operation.gamme_operation.nom} — "
                f"Entrée: {operation.date_entree.strftime('%H:%M')} | "
                f"Sortie: {operation.date_sortie.strftime('%H:%M')} | "
                f"Statut: {operation.statut}"  # ← Affiche le statut CALCULÉ
            )
            return redirect('of_detail', id=operation.of.id)
    else:
        form = EntreeOperationForm(instance=operation)
    
    return render(request, 'of/saisir_entree.html', {
        'form': form,
        'operation': operation,
        'of': operation.of,
    })


@login_required(login_url='home')
def terminer_operation(request, operation_id):
    """
    Marque une opération comme TERMINÉE
    (OPTIONNEL MAINTENANT - elle se termine toute seule!)
    """
    operation = get_object_or_404(OperationOF, id=operation_id)
    
    if not operation.date_entree:
        messages.error(request, "Cette opération n'a pas de date d'entrée!")
        return redirect('of_detail', id=operation.of.id)
    
    # ❌ PLUS BESOIN: operation.statut = 'termine'
    # ✅ Le statut est AUTOMATIQUEMENT 'termine' si l'heure est atteinte!
    
    # On peut juste afficher un message de confirmation
    if operation.est_terminee:
        messages.success(
            request,
            f"✅ {operation.gamme_operation.nom} est TERMINÉE! "
            f"(Sortie: {operation.date_sortie.strftime('%H:%M')})"
        )
    else:
        remaining = operation.date_sortie - timezone.now()
        remaining_minutes = round(remaining.total_seconds() / 60)
        messages.info(
            request,
            f"⏳ {operation.gamme_operation.nom} — "
            f"Encore {remaining_minutes} minutes avant la fin..."
        )
    
    return redirect('of_detail', id=operation.of.id)



@login_required(login_url='home')
def list_retard(request):
    """
    Tableau simple des retards:
    - Lignes: Les 20 derniers OF
    - Colonnes: Les opérations (gammes)
    - Cellules: Le retard en minutes
    """
    # Les 20 derniers OF
    ofs = OrdreFabrication.objects.all().order_by('-id')[:20]
    
    # Toutes les gammes (opérations) triées par ordre
    gammes = GammeOperation.objects.all().order_by('ordre')
    
    context = {
        'ofs': ofs,
        'gammes': gammes,
    }
    return render(request, 'statistiques_retard/list_retard.html', context)





@login_required(login_url='home')
def dashboard(request):
    """
    Page d'accueil principal après connexion
    Affiche un résumé des OF
    """
    # ✅ SIMPLE - récupère juste tous les OF
    ofs = OrdreFabrication.objects.all()
    
    context = {
        'ofs': ofs,
        'total_of': ofs.count(),
        'today': datetime.now(),
    }
    return render(request, 'dashboard.html', context)







@login_required(login_url='home')
def declarer_alea(request, operation_id):
    """
    Vue pour déclarer un aléa (problème) pendant une opération
    """
    operation = get_object_or_404(OperationOF, id=operation_id)
    
    if request.method == 'POST':
        form = AleaForm(request.POST)
        if form.is_valid():
            alea = form.save(commit=False)
            alea.operation = operation
            alea.save()
            messages.success(request, f"⚠️ Aléa enregistré : {alea.get_type_alea_display()}")
            return redirect('detail_of', numero_of=operation.of.numero)
    else:
        form = AleaForm()
    
    context = {
        'form': form,
        'operation': operation,
    }
    return render(request, 'of/declarer_alea.html', context)




# ===== VUE: ASSIGNER LES GAMMES AVEC DRAG & DROP =====
@login_required(login_url='home')
def assigner_gammes_operateur(request, operateur_id):
    """
    Page Drag & Drop pour assigner les gammes opératoires à un opérateur.
    
    Interface simple:
    - À gauche: toutes les gammes disponibles (on peut les glisser)
    - À droite: zone de dépôt (les gammes assignées à cet opérateur)
    """
    # Récupère l'opérateur
    operateur = get_object_or_404(Operateur, id=operateur_id)
    
    if request.method == 'POST':
        # Traitement du formulaire POST (quand on soumet l'ordre des gammes)
        import json
        
        # Récupère les IDs des gammes dans l'ordre
        gammes_ids = request.POST.get('gammes_ordre', '[]')
        
        try:
            gammes_ids = json.loads(gammes_ids)
        except:
            gammes_ids = []
        
        # Supprime toutes les assignations existantes pour cet opérateur
        operateur.gammes.clear()
        
        # Ajoute les gammes dans le nouvel ordre
        for index, gamme_id in enumerate(gammes_ids):
            try:
                gamme = GammeOperation.objects.get(id=gamme_id)
                gamme.operateurs.add(operateur)
            except:
                pass
        
        messages.success(request, f"✅ Gammes assignées à {operateur}!")
        return redirect('dashboard_operateur', operateur_id=operateur_id)
    
    # GET: Affiche la page Drag & Drop
    # Récupère les gammes assignées à cet opérateur (dans l'ordre)
    gammes_assignees = operateur.gammes.all()
    
    # Récupère toutes les autres gammes (non assignées)
    gammes_disponibles = GammeOperation.objects.exclude(operateurs=operateur).order_by('ordre')
    
    context = {
        'operateur': operateur,
        'gammes_assignees': gammes_assignees,
        'gammes_disponibles': gammes_disponibles,
    }
    return render(request, 'planning/assigner_gammes_dragdrop.html', context)


# ============================================================
# VUE MODIFIER L'HEURE DE DÉBUT DU PLANNING
# ============================================================

@login_required(login_url='home')
def modifier_heure_debut(request, operateur_id):
    """
    Permet de modifier l'heure de début du planning pour un opérateur.
    Cela met à jour toutes les tâches du jour automatiquement.
    """
    operateur = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()
    
    # Récupère le planning du jour
    planning = PlanningJournalier.objects.filter(
        operateur=operateur,
        date=aujourd_hui
    ).first()
    
    if not planning:
        messages.error(request, "❌ Aucun planning pour aujourd'hui")
        return redirect('dashboard_operateur', operateur_id=operateur_id)
    
    if request.method == 'POST':
        # Récupère la nouvelle heure depuis le formulaire
        try:
            heure_str = request.POST.get('heure_debut', '')
            heure, minute = map(int, heure_str.split(':'))
            
            # Crée la nouvelle heure de début
            nouvelle_heure_debut = timezone.make_aware(
                datetime(aujourd_hui.year, aujourd_hui.month, aujourd_hui.day, heure, minute)
            )
            
            # Récupère toutes les tâches ordonnées
            taches = planning.taches.filter(type_tache='operation').order_by('ordre')
            
            # Recalcule les heures pour chaque tâche
            heure_courante = nouvelle_heure_debut
            
            for tache in taches:
                # Récupère la durée de la gamme
                duree = timedelta(hours=float(tache.gamme_operation.temps_alloue))
                
                # Met à jour les horaires
                tache.heure_debut_prevue = heure_courante
                tache.heure_fin_prevue = heure_courante + duree
                tache.save()
                
                # La prochaine tâche commence où finit celle-ci
                heure_courante = tache.heure_fin_prevue
            
            messages.success(request, f"✅ Heure de début modifiée à {heure:02d}:{minute:02d}")
            return redirect('dashboard_operateur', operateur_id=operateur_id)
        
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")
            return redirect('dashboard_operateur', operateur_id=operateur_id)
    
    # Affiche le formulaire avec l'heure actuelle
    heure_actuelle = planning.taches.filter(type_tache='operation').order_by('ordre').first()
    if heure_actuelle:
        heure_str = heure_actuelle.heure_debut_prevue.strftime('%H:%M')
    else:
        heure_str = '06:00'
    
    context = {
        'operateur': operateur,
        'planning': planning,
        'heure_str': heure_str,
    }
    return render(request, 'planning/modifier_heure_debut.html', context)


# ============================================================
# VUE SUPERVISEUR — Tous les opérateurs sur une seule page
# ============================================================

@login_required(login_url='home')
def superviseur_dashboard(request):
    """
    Page superviseur : affiche tous les opérateurs avec leur timeline.
    Un opérateur par carte, avec sa timeline du shift.
    Rafraîchissement automatique toutes les 30 secondes (géré en JS).
    """
    aujourd_hui  = timezone.localdate()
    operateurs   = Operateur.objects.all().order_by('shift', 'nom')

    operateurs_data = []
    for operateur in operateurs:
        # Récupère le planning du jour pour cet opérateur (peut être None)
        planning = PlanningJournalier.objects.filter(
            operateur=operateur,
            date=aujourd_hui
        ).first()

        # Construit les données de timeline si le planning existe
        timeline_data = build_timeline_data(planning) if planning else None

        operateurs_data.append({
            'operateur'    : operateur,
            'planning'     : planning,
            'timeline_data': timeline_data,
            'has_gammes'   : GammeOperation.objects.filter(operateurs=operateur).exists(),
        })

    return render(request, 'planning/superviseur.html', {
        'operateurs_data': operateurs_data,
        'aujourd_hui'    : aujourd_hui,
    })


# ============================================================
# VUE DASHBOARD OPERATEUR — Timeline d'un seul opérateur
# ============================================================

@login_required(login_url='home')
def dashboard_operateur(request, operateur_id):
    """
    Page détaillée d'un opérateur avec sa timeline complète.
    Permet aussi de démarrer/terminer des tâches.
    """
    operateur   = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()

    # Planning du jour (peut être None si pas encore généré)
    planning = PlanningJournalier.objects.filter(
        operateur=operateur,
        date=aujourd_hui
    ).first()

    timeline_data = build_timeline_data(planning) if planning else None

    return render(request, 'planning/dashboard_operateur.html', {
        'operateur'    : operateur,
        'planning'     : planning,
        'timeline_data': timeline_data,
        'aujourd_hui'  : aujourd_hui,
        'has_gammes'   : GammeOperation.objects.filter(operateurs=operateur).exists(),
    })


# ============================================================
# VUE GÉNÉRER PLANNING — Génère le planning du jour
# ============================================================

@login_required(login_url='home')
def generer_planning(request, operateur_id):
    """
    Génère (ou régénère) le planning du jour pour un opérateur.
    Redirige vers le dashboard opérateur après génération.
    """
    operateur   = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()

    # Appelle la fonction utilitaire qui crée les TachePlanifiee
    planning = generer_planning_journalier(operateur, aujourd_hui)

    messages.success(request, f"✅ Planning généré pour {operateur} ({planning.taches.count()} tâches)")
    return redirect('dashboard_operateur', operateur_id=operateur_id)


# ============================================================
# VUE DÉMARRER UNE TÂCHE
# ============================================================

@login_required(login_url='home')
def demarrer_tache(request, tache_id):
    """
    Enregistre l'heure de début RÉELLE d'une tâche (quand l'opérateur clique).
    Permet de calculer l'écart réel vs prévu.
    """
    tache = get_object_or_404(TachePlanifiee, id=tache_id)

    if not tache.heure_debut_reelle:  # on ne démarre pas deux fois
        tache.heure_debut_reelle = timezone.now()
        tache.save()
        messages.success(request, f"▶️ {tache.nom_affichage} démarrée à {tache.heure_debut_reelle.strftime('%H:%M')}")

    return redirect('dashboard_operateur', operateur_id=tache.planning.operateur.id)


# ============================================================
# VUE TERMINER UNE TÂCHE
# ============================================================

@login_required(login_url='home')
def terminer_tache(request, tache_id):
    """
    Enregistre l'heure de fin RÉELLE d'une tâche.
    L'écart (retard ou avance) est calculé automatiquement via la @property ecart_fin_minutes.
    """
    tache = get_object_or_404(TachePlanifiee, id=tache_id)

    if not tache.heure_fin_reelle:  # on ne termine pas deux fois
        tache.heure_fin_reelle = timezone.now()
        tache.save()
        ecart = tache.ecart_fin_minutes
        if ecart and ecart > 0:
            messages.warning(request, f"⚠️ {tache.nom_affichage} terminée avec {ecart} min de retard")
        elif ecart and ecart < 0:
            messages.success(request, f"✅ {tache.nom_affichage} terminée avec {abs(ecart)} min d'avance")
        else:
            messages.success(request, f"✅ {tache.nom_affichage} terminée dans les temps")

    return redirect('dashboard_operateur', operateur_id=tache.planning.operateur.id)


# ============================================================
# VUE RAFRÂICHIR OPÉRATEUR (supprimer toutes les opérations)
# ============================================================

@login_required(login_url='home')
def rafraichir_operateur(request, operateur_id):
    """
    Supprime toutes les gammes assignées à l'opérateur et son planning du jour.
    Utile pour recommencer à zéro.
    """
    operateur = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()

    # Récupère toutes les gammes assignées à cet opérateur
    gammes = operateur.gammes.all()
    gammes_supprimees = gammes.count()
    
    # Supprime l'assignation de toutes les gammes pour cet opérateur
    for gamme in gammes:
        gamme.operateurs.remove(operateur)

    # Supprime le planning du jour s'il existe
    planning_supprime = False
    planning = PlanningJournalier.objects.filter(operateur=operateur, date=aujourd_hui).first()
    if planning:
        planning.delete()
        planning_supprime = True

    # Message de confirmation
    message = f"✅ Opérateur rafraîchi : {gammes_supprimees} gammes supprimées"
    if planning_supprime:
        message += " et planning du jour supprimé"
    
    messages.success(request, message)
    return redirect('dashboard_operateur', operateur_id=operateur_id)


# ============================================================
# VUE DÉPLACER UNE TÂCHE (interchangeabilité)
# ============================================================

@login_required(login_url='home')
def deplacer_tache(request, tache_id, direction):
    """
    Permet de réordonner les tâches (monter ou descendre dans la liste).
    
    Direction: 'up' pour monter, 'down' pour descendre
    Cela change l'ordre de la tâche et recalcule les heures automatiquement.
    """
    # Récupère la tâche à déplacer
    tache = get_object_or_404(TachePlanifiee, id=tache_id)
    planning = tache.planning
    operateur = planning.operateur
    
    # Récupère toutes les tâches du planning (ordonnées)
    taches = list(planning.taches.filter(type_tache='operation').order_by('ordre'))
    
    # Trouve la position actuelle de la tâche
    index_actuel = None
    for i, t in enumerate(taches):
        if t.id == tache_id:
            index_actuel = i
            break
    
    if index_actuel is None:
        messages.error(request, "❌ Tâche non trouvée")
        return redirect('dashboard_operateur', operateur_id=operateur.id)
    
    # Échange avec la tâche voisine (up = vers le haut, down = vers le bas)
    if direction == 'up' and index_actuel > 0:
        # Échange avec la tâche précédente
        taches[index_actuel], taches[index_actuel - 1] = taches[index_actuel - 1], taches[index_actuel]
    elif direction == 'down' and index_actuel < len(taches) - 1:
        # Échange avec la tâche suivante
        taches[index_actuel], taches[index_actuel + 1] = taches[index_actuel + 1], taches[index_actuel]
    else:
        # Déjà au début (up) ou à la fin (down)
        messages.info(request, "ℹ️ Impossible de déplacer plus loin")
        return redirect('dashboard_operateur', operateur_id=operateur.id)
    
    # Recalcule les heures pour toutes les tâches
    h_debut, m_debut = operateur.shift_debut_hm
    heure_courante = timezone.make_aware(
        datetime(planning.date.year, planning.date.month, planning.date.day, h_debut, m_debut)
    )
    
    # Réassigne l'ordre et les heures
    for i, t in enumerate(taches):
        t.ordre = i + 1  # L'ordre recommence à 1
        t.heure_debut_prevue = heure_courante
        t.heure_fin_prevue = heure_courante + timedelta(hours=float(t.gamme_operation.temps_alloue))
        t.save()
        
        # La prochaine tâche commence où finit celle-ci
        heure_courante = t.heure_fin_prevue
    
    messages.success(request, f"✅ Tâches réordonnées")
    return redirect('dashboard_operateur', operateur_id=operateur.id)