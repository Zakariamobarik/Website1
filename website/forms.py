from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import *

# ===== FORMULAIRE D'INSCRIPTION =====
class SignUpForm(UserCreationForm):
    """
    Formulaire personnalisé pour l'inscription des nouveaux utilisateurs.
    Hérite de UserCreationForm de Django qui gère la création d'utilisateurs.
    """
    
    # Champ pour l'email - requis (par défaut c'est facultatif dans User)
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',  # Classe Bootstrap pour le style
            'placeholder': 'exemple@email.com',
            'required': True
        })
    )
    
    # Champ pour le nom d'utilisateur
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom d\'utilisateur',
        })
    )
    
    # Champ pour le mot de passe
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez votre mot de passe',
        })
    )
    
    # Champ pour confirmer le mot de passe
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmez votre mot de passe',
        })
    )

    class Meta:
        # Spécifie quel modèle utiliser (le modèle User de Django)
        model = User
        # Spécifie les champs à afficher dans le formulaire
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        """
        Validation personnalisée pour l'email.
        Vérifie que l'email n'existe pas déjà dans la base de données.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé!")
        return email
    
    def clean_username(self):
        """
        Validation personnalisée pour le nom d'utilisateur.
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur existe déjà!")
        return username


# ===== FORMULAIRE D'opérateur =====

class OperateurForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un Opérateur"""
    class Meta:
        model = Operateur
        fields = ['nom', 'prenom', 'poste', 'user']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Dupont'
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Jean'
            }),
            'poste': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Assemblage (optionnel)',
                'required': False
            }),
            'user': forms.Select(attrs={
                'class': 'form-control',
            }),
        }


# ===== Gammeopératpoire  ==================================================

class GammeOperationForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier une Gamme Opératoire"""
    class Meta:
        model = GammeOperation
        fields = ['nom', 'temps_alloue', 'ordre', 'operateurs']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Assemblage'
            }),
            'temps_alloue': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': 'Heures (ex: 1.005)'
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1, 2, 3...'
            }),
            'operateurs': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

# ===== FORMULAIRE DE POINTAGE =====
# Ajouter à la fin de forms.py


# Ajouter à la fin de forms.py

class OrdreFabricationForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un OF"""
    class Meta:
        model = OrdreFabrication
        fields = ['numero', 'produit', 'quantite']
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: OF-001',
                'help_text': 'Code unique de l\'OF'
            }),
            'produit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Strapontin modèle X'
            }),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 10',
                'min': 1
            }),
        }

# Ajouter à la fin de forms.py

class EntreeOperationForm(forms.ModelForm):
    """Formulaire pour saisir la date/heure d'ENTRÉE"""
    class Meta:
        model = OperationOF
        fields = ['date_entree']
        widgets = {
            'date_entree': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg',
            }),
        }
        labels = {
            'date_entree': '📅 Date et heure d\'entrée'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        if not self.instance.date_entree:
            self.fields['date_entree'].initial = timezone.now()




# ===== FORMULAIRE DE DÉCLARATION D'ALÉA =====
class AleaForm(forms.ModelForm):
    """
    Quand un opérateur rencontre un problème pendant son opération
    """
    class Meta:
        model = Alea
        fields = ['type_alea', 'description', 'duree']
        widgets = {
            'type_alea': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Décrivez le problème...'
            }),
            'duree': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Durée en minutes'
            })
        }


class AssignerGammesForm(forms.Form):
    """
    Formulaire simple pour assigner des gammes opératoires à un opérateur
    Permet de cocher plusieurs gammes à la fois
    """
    # Récupère TOUTES les gammes, ordonnées par ordre
    gammes = forms.ModelMultipleChoiceField(
        queryset=GammeOperation.objects.all().order_by('ordre'),
        widget=forms.CheckboxSelectMultiple,
        label="Sélectionnez les gammes à assigner",
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Affiche le nom et l'ordre pour chaque gamme
        self.fields['gammes'].label_from_instance = lambda obj: f"{obj.ordre}. {obj.nom} ({obj.temps_alloue}h)"

