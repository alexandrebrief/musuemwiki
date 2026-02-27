#!/usr/bin/env python3
import json
from collections import Counter

with open('grant_wood_artworks.json', 'r', encoding='utf-8') as f:
    artworks = json.load(f)

print("="*60)
print("📊 ANALYSE DU FICHIER JSON")
print("="*60)
print(f"Total d'entrées: {len(artworks)}")

# Compter les IDs uniques
ids = [a.get('wikidata_id') for a in artworks if a.get('wikidata_id')]
ids_uniques = set(ids)
print(f"IDs uniques: {len(ids_uniques)}")
print(f"Doublons potentiels: {len(ids) - len(ids_uniques)}")

# Trouver les IDs en double
id_counts = Counter(ids)
doublons = {id: count for id, count in id_counts.items() if count > 1}
if doublons:
    print("\n🔍 IDs en double:")
    for id, count in list(doublons.items())[:10]:  # 10 premiers
        print(f"  • {id}: {count} fois")

# Vérifier les champs manquants
champs_manquants = {
    'titre': 0,
    'createur': 0,
    'date_creation': 0,
    'image_url': 0,
    'collection': 0
}

for a in artworks:
    for champ in champs_manquants:
        if not a.get(champ):
            champs_manquants[champ] += 1

print("\n📉 Champs manquants:")
for champ, count in champs_manquants.items():
    print(f"  • {champ}: {count}/{len(artworks)}")

# Afficher les premières entrées pour vérifier la structure
print("\n📋 Structure des 3 premières entrées:")
for i, a in enumerate(artworks[:3]):
    print(f"\nEntrée {i+1}:")
    for key, value in list(a.items())[:5]:  # 5 premiers champs
        print(f"  {key}: {value}")
