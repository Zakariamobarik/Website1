from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date as date_type
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



# ============================================================
# PLANNING JOURNALIER OPÉRATEUR
# ============================================================

@login_required(login_url='home')
def mon_dashboard_operateur(request):
    """
    Redirige l'utilisateur connecté vers son propre dashboard opérateur.
    Si l'utilisateur n'est pas lié à un opérateur → tableau de bord superviseur.
    """
    try:
        operateur = request.user.operateur_profil
        return redirect('dashboard_operateur', operateur_id=operateur.id)
    except (Operateur.DoesNotExist, AttributeError):
        return redirect('superviseur_dashboard')


@login_required(login_url='home')
def dashboard_operateur(request, operateur_id):
    """Dashboard timeline pour un opérateur donné (aujourd'hui)."""
    operateur   = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()

    # Récupère ou génère le planning du jour
    planning = PlanningJournalier.objects.filter(operateur=operateur, date=aujourd_hui).first()

    # Si l'opérateur n'a pas de gammes assignées, on le signale
    has_gammes = GammeOperation.objects.filter(operateur=operateur).exists()

    timeline_data = build_timeline_data(planning) if planning else None

    context = {
        'operateur'    : operateur,
        'planning'     : planning,
        'timeline_data': timeline_data,
        'aujourd_hui'  : aujourd_hui,
        'has_gammes'   : has_gammes,
    }
    return render(request, 'planning/dashboard_operateur.html', context)


@login_required(login_url='home')
def generer_planning_view(request, operateur_id):
    """Génère (ou régénère) le planning du jour pour un opérateur."""
    operateur   = get_object_or_404(Operateur, id=operateur_id)
    aujourd_hui = timezone.localdate()

    if not GammeOperation.objects.filter(operateur=operateur).exists():
        messages.error(request, f"❌ Aucune gamme assignée à {operateur} — planning impossible.")
        return redirect('dashboard_operateur', operateur_id=operateur_id)

    generer_planning_journalier(operateur, aujourd_hui)
    messages.success(request, f"✅ Planning du {aujourd_hui} généré pour {operateur}.")
    return redirect('dashboard_operateur', operateur_id=operateur_id)


@login_required(login_url='home')
def demarrer_tache(request, tache_id):
    """Marque le démarrage réel d'une tâche."""
    tache = get_object_or_404(TachePlanifiee, id=tache_id)

    if tache.heure_debut_reelle:
        messages.warning(request, "Cette tâche a déjà été démarrée.")
    else:
        tache.heure_debut_reelle = timezone.now()
        tache.save(update_fields=['heure_debut_reelle'])
        messages.success(request, f"▶️ Tâche démarrée : {tache.nom_affichage}")

    return redirect('dashboard_operateur', operateur_id=tache.planning.operateur_id)


@login_required(login_url='home')
def terminer_tache(request, tache_id):
    """Marque la fin réelle d'une tâche."""
    tache = get_object_or_404(TachePlanifiee, id=tache_id)

    if not tache.heure_debut_reelle:
        messages.error(request, "Vous devez d'abord démarrer cette tâche.")
    elif tache.heure_fin_reelle:
        messages.warning(request, "Cette tâche est déjà terminée.")
    else:
        tache.heure_fin_reelle = timezone.now()
        tache.save(update_fields=['heure_fin_reelle'])
        ecart = tache.ecart_fin_minutes
        if ecart and ecart > 0:
            messages.warning(request, f"✅ Tâche terminée avec {ecart} min de retard.")
        elif ecart and ecart < 0:
            messages.success(request, f"✅ Tâche terminée avec {abs(ecart)} min d'avance !")
        else:
            messages.success(request, f"✅ Tâche terminée dans les temps.")

    return redirect('dashboard_operateur', operateur_id=tache.planning.operateur_id)


@login_required(login_url='home')
def superviseur_dashboard(request):
    """Vue superviseur : état des 3 opérateurs en temps réel."""
    aujourd_hui = timezone.localdate()
    operateurs  = Operateur.objects.all().order_by('nom')

    data = []
    for op in operateurs:
        planning = PlanningJournalier.objects.filter(operateur=op, date=aujourd_hui).first()
        if planning:
            td = build_timeline_data(planning)
        else:
            td = None
        data.append({
            'operateur'     : op,
            'planning'      : planning,
            'timeline_data' : td,
            'has_gammes'    : GammeOperation.objects.filter(operateur=op).exists(),
        })

    context = {
        'aujourd_hui': aujourd_hui,
        'operateurs_data': data,
    }
    return render(request, 'planning/superviseur.html', context)

