from django.test import TestCase
from django.contrib.auth.models import Group

# Create your tests here.

for group in Group.objects.all():
    print(f"Groupe: {group.name}")
