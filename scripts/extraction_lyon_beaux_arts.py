#!/usr/bin/env python3
"""
Script d'extraction des œuvres du Musée des Beaux-Arts de Lyon
Avec les champs définis par l'utilisateur
"""

import time
import json
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON

# ============================================
# CONFIGURATION
# ============================================
USER_AGENT = "MuseumWikiBot/12.0 (https://github.com/alexandrebrief/museumwiki)"
ENDPOINT_URL = "https://query.wikidata.org/sparql"
MUSEE_ID = "Q511"  # Musée des Beaux-Arts de Lyon
MUSEE_NOM = "Musée des Beaux-Arts de Lyon"
OUTPUT_FILE = "mba_lyon_complet.json"

# Paramètres d'optimisation
BATCH_SIZE = 20  # Taille des lots pour éviter les timeouts
TIMEOUT = 120    # Timeout en secondes
MAX_RETRIES = 3  # Nombre de tentatives en cas d'échec
PAUSE_BETWEEN_LOTS = 2  # Pause entre les lots

# ============================================
# FONCTIONS SPARQL
# ============================================

def get_sparql():
    """Crée une connexion SPARQL avec timeout"""
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(TIMEOUT)
    sparql.addCustomParameter("User-Agent", USER_AGENT)
    return sparql

def execute_query_with_retry(query, description="", max_retries=MAX_RETRIES):
    """Exécute une requête avec plusieurs tentatives"""
    
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"  🔄 Tentative {attempt}/{max_retries}...")
            
            sparql = get_sparql()
            sparql.setQuery(query)
            results = sparql.query().convert()
            
            # Pause de courtoisie pour Wikidata
            time.sleep(1)
            return results
            
        except Exception as e:
            error_str = str(e)
            print(f"  ⚠️ Erreur: {error_str[:100]}")
            
            if attempt < max_retries:
                wait_time = attempt * 10
                print(f"  ⏳ Nouvelle tentative dans {wait_time}s...")
                time.sleep(wait_time)
    
    print(f"  ❌ Échec après {max_retries} tentatives")
    return None

def get_total_count():
    """Récupère le nombre total d'œuvres (collection directe)"""
    query = f"""
    SELECT (COUNT(DISTINCT ?œuvre) AS ?count) WHERE {{
      ?œuvre wdt:P195 wd:{MUSEE_ID}.
    }}
    """
    results = execute_query_with_retry(query, "Comptage des œuvres")
    if results and 'results' in results and results['results']['bindings']:
        return int(results['results']['bindings'][0]['count']['value'])
    return 0

# ============================================
# REQUÊTE PRINCIPALE
# ============================================

def get_artworks_query(offset=0, limit=BATCH_SIZE):
    """
    Requête avec tous les champs demandés
    - id (obligatoire)
    - titre (fallback via SERVICE)
    - titre_fr, titre_en (optionnels)
    - image (optionnel)
    - createur (optionnel)
    - date (optionnel)
    - type (optionnel)
    - partie de P361 (optionnel)
    - collection P195 (obligatoire - condition de base)
    - lieu P276 (optionnel)
    - mouvement (optionnel)
    - technique (optionnel)
    - url_wikidata (optionnel - dérivé de l'ID)
    """
    return f"""
    SELECT DISTINCT 
           ?œuvre
           ?titre_fr ?titre_en
           ?image
           ?createur ?createurLabel
           ?date
           ?type ?typeLabel
           ?partie_de ?partie_deLabel
           ?collection ?collectionLabel
           ?lieu ?lieuLabel
           ?mouvement ?mouvementLabel
           ?technique
    WHERE {{
      # Condition de base : l'œuvre est dans la collection du musée
      ?œuvre wdt:P195 wd:{MUSEE_ID}.
      
      # Récupération des labels via SERVICE (fallback)
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "fr,en". 
        ?œuvre rdfs:label ?titre.
        ?createur rdfs:label ?createurLabel.
        ?type rdfs:label ?typeLabel.
        ?partie_de rdfs:label ?partie_deLabel.
        ?collection rdfs:label ?collectionLabel.
        ?lieu rdfs:label ?lieuLabel.
        ?mouvement rdfs:label ?mouvementLabel.
      }}
      
      # Titres spécifiques (optionnels)
      OPTIONAL {{
        ?œuvre rdfs:label ?titre_fr.
        FILTER(LANG(?titre_fr) = "fr")
      }}
      OPTIONAL {{
        ?œuvre rdfs:label ?titre_en.
        FILTER(LANG(?titre_en) = "en")
      }}
      
      # Image (optionnel)
      OPTIONAL {{ ?œuvre wdt:P18 ?image. }}
      
      # Créateur (optionnel)
      OPTIONAL {{ ?œuvre wdt:P170 ?createur. }}
      
      # Date (optionnel)
      OPTIONAL {{ ?œuvre wdt:P571 ?date. }}
      
      # Type (optionnel)
      OPTIONAL {{ ?œuvre wdt:P31 ?type. }}
      
      # Partie de (optionnel)
      OPTIONAL {{ ?œuvre wdt:P361 ?partie_de. }}
      
      # Collection (optionnel - déjà utilisé comme condition)
      OPTIONAL {{ ?œuvre wdt:P195 ?collection. }}
      
      # Lieu (optionnel)
      OPTIONAL {{ ?œuvre wdt:P276 ?lieu. }}
      
      # Mouvement (optionnel)
      OPTIONAL {{ ?œuvre wdt:P135 ?mouvement. }}
      
      # Technique (optionnel)
      OPTIONAL {{ ?œuvre wdt:P2079 ?technique. }}
    }}
    ORDER BY ?titre
    LIMIT {limit}
    OFFSET {offset}
    """

# ============================================
# TRAITEMENT DES RÉSULTATS
# ============================================

def parse_artwork(binding):
    """Convertit un résultat SPARQL en dictionnaire structuré"""
    
    # ID (obligatoire)
    artwork_url = binding.get('œuvre', {}).get('value', '')
    artwork_id = artwork_url.split('/')[-1] if artwork_url else ''
    
    # URL Wikidata (dérivée)
    wikidata_url = f"https://www.wikidata.org/wiki/{artwork_id}" if artwork_id else ''
    
    # Création du dictionnaire
    artwork = {
        # Essentiels
        'id': artwork_id,
        'titre_fallback': binding.get('titre', {}).get('value', 'Sans titre'),
        
        # Titres spécifiques (optionnels)
        'titre_fr': binding.get('titre_fr', {}).get('value', ''),
        'titre_en': binding.get('titre_en', {}).get('value', ''),
        
        # Image (optionnel)
        'image_url': binding.get('image', {}).get('value', ''),
        
        # Créateur (optionnel)
        'createur_nom': binding.get('createurLabel', {}).get('value', ''),
        'createur_id': binding.get('createur', {}).get('value', '').split('/')[-1] if binding.get('createur') else '',
        
        # Date (optionnel)
        'date_creation': binding.get('date', {}).get('value', ''),
        
        # Type (optionnel)
        'type': binding.get('typeLabel', {}).get('value', ''),
        'type_id': binding.get('type', {}).get('value', '').split('/')[-1] if binding.get('type') else '',
        
        # Partie de (optionnel)
        'partie_de': binding.get('partie_deLabel', {}).get('value', ''),
        'partie_de_id': binding.get('partie_de', {}).get('value', '').split('/')[-1] if binding.get('partie_de') else '',
        
        # Collection (optionnel)
        'collection': binding.get('collectionLabel', {}).get('value', MUSEE_NOM),
        'collection_id': binding.get('collection', {}).get('value', '').split('/')[-1] if binding.get('collection') else MUSEE_ID,
        
        # Lieu (optionnel)
        'lieu': binding.get('lieuLabel', {}).get('value', ''),
        'lieu_id': binding.get('lieu', {}).get('value', '').split('/')[-1] if binding.get('lieu') else '',
        
        # Mouvement (optionnel)
        'mouvement': binding.get('mouvementLabel', {}).get('value', ''),
        'mouvement_id': binding.get('mouvement', {}).get('value', '').split('/')[-1] if binding.get('mouvement') else '',
        
        # Technique (optionnel)
        'technique': binding.get('technique', {}).get('value', ''),
        
        # URL Wikidata
        'wikidata_url': wikidata_url,
        
        # Métadonnées
        'musee': MUSEE_NOM,
        'musee_id': MUSEE_ID,
        'date_extraction': datetime.now().isoformat(),
        'source': 'Wikidata'
    }
    
    return artwork

# ============================================
# FONCTION PRINCIPALE
# ============================================

def main():
    print("="*80)
    print(f"🖼️  EXTRACTION DES ŒUVRES DU {MUSEE_NOM}")
    print("="*80)
    print(f"📊 Champs demandés: 13 (id, titres, image, createur, date, type, partie_de, collection, lieu, mouvement, technique, url)")
    print(f"📦 Lots de {BATCH_SIZE} œuvres")
    print(f"⏱️  Timeout: {TIMEOUT}s")
    print("="*80)
    
    # Récupérer le nombre total
    total_attendu = get_total_count()
    print(f"📊 Nombre total d'œuvres (collection directe): {total_attendu}")
    
    if total_attendu == 0:
        print("❌ Aucune œuvre trouvée. Vérifie l'ID du musée.")
        return
    
    # Récupérer les œuvres par lots
    toutes_les_oeuvres = []
    offset = 0
    lots_reussis = 0
    lots_echoues = 0
    
    print(f"\n📦 Début de la récupération par lots...")
    
    while offset < total_attendu:
        print(f"\n📦 Lot {offset//BATCH_SIZE + 1} (offset {offset}, taille {BATCH_SIZE})...")
        
        query = get_artworks_query(offset, BATCH_SIZE)
        results = execute_query_with_retry(query, f"Récupération du lot {offset//BATCH_SIZE + 1}")
        
        if results and 'results' in results:
            bindings = results['results']['bindings']
            
            if bindings:
                for binding in bindings:
                    oeuvre = parse_artwork(binding)
                    toutes_les_oeuvres.append(oeuvre)
                
                print(f"  ✅ {len(bindings)} œuvres récupérées (total: {len(toutes_les_oeuvres)}/{total_attendu})")
                lots_reussis += 1
                offset += BATCH_SIZE
            else:
                print(f"  ⚠️ Aucune œuvre dans ce lot")
                break
        else:
            print(f"  ❌ Échec de la récupération")
            lots_echoues += 1
            
            if lots_echoues >= 3:
                print("\n⚠️ Trop d'échecs consécutifs. Arrêt du script.")
                break
        
        # Pause entre les lots
        if offset < total_attendu:
            time.sleep(PAUSE_BETWEEN_LOTS)
    
    # Statistiques finales
    print("\n" + "="*80)
    print("📊 RÉSULTATS FINAUX")
    print("="*80)
    print(f"✅ Œuvres récupérées: {len(toutes_les_oeuvres)}")
    print(f"📊 Total attendu: {total_attendu}")
    
    if len(toutes_les_oeuvres) < total_attendu:
        print(f"⚠️ {total_attendu - len(toutes_les_oeuvres)} œuvres manquantes")
    
    if toutes_les_oeuvres:
        # Statistiques de remplissage
        with_images = sum(1 for o in toutes_les_oeuvres if o.get('image_url'))
        with_dates = sum(1 for o in toutes_les_oeuvres if o.get('date_creation'))
        with_createur = sum(1 for o in toutes_les_oeuvres if o.get('createur_nom'))
        with_titre_fr = sum(1 for o in toutes_les_oeuvres if o.get('titre_fr'))
        with_titre_en = sum(1 for o in toutes_les_oeuvres if o.get('titre_en'))
        with_type = sum(1 for o in toutes_les_oeuvres if o.get('type'))
        with_lieu = sum(1 for o in toutes_les_oeuvres if o.get('lieu'))
        with_mouvement = sum(1 for o in toutes_les_oeuvres if o.get('mouvement'))
        with_technique = sum(1 for o in toutes_les_oeuvres if o.get('technique'))
        
        print(f"\n📊 Qualité des données:")
        print(f"  🖼️  Images: {with_images}/{len(toutes_les_oeuvres)} ({with_images/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  📅 Dates: {with_dates}/{len(toutes_les_oeuvres)} ({with_dates/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🎨 Créateurs: {with_createur}/{len(toutes_les_oeuvres)} ({with_createur/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🇫🇷 Titres FR: {with_titre_fr}/{len(toutes_les_oeuvres)} ({with_titre_fr/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🇬🇧 Titres EN: {with_titre_en}/{len(toutes_les_oeuvres)} ({with_titre_en/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🏷️  Types: {with_type}/{len(toutes_les_oeuvres)} ({with_type/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  📍 Lieux: {with_lieu}/{len(toutes_les_oeuvres)} ({with_lieu/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🌊 Mouvements: {with_mouvement}/{len(toutes_les_oeuvres)} ({with_mouvement/len(toutes_les_oeuvres)*100:.1f}%)")
        print(f"  🔧 Techniques: {with_technique}/{len(toutes_les_oeuvres)} ({with_technique/len(toutes_les_oeuvres)*100:.1f}%)")
        
        # Sauvegarde en JSON
        print(f"\n💾 Sauvegarde dans {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(toutes_les_oeuvres, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Fichier sauvegardé avec succès!")
        
        # Afficher quelques exemples
        print("\n🖼️  Exemples d'œuvres (3 premières):")
        for i, oeuvre in enumerate(toutes_les_oeuvres[:3], 1):
            print(f"\n  {i}. {oeuvre['titre_fallback']}")
            if oeuvre['titre_fr']:
                print(f"     🇫🇷 {oeuvre['titre_fr']}")
            if oeuvre['createur_nom']:
                print(f"     🎨 {oeuvre['createur_nom']}")
            if oeuvre['date_creation']:
                print(f"     📅 {oeuvre['date_creation']}")
            if oeuvre['type']:
                print(f"     🏷️  {oeuvre['type']}")
            if oeuvre['image_url']:
                print(f"     🖼️  Image disponible")
    else:
        print("❌ Aucune œuvre récupérée.")
    
    print("\n" + "="*80)
    print(f"✅ EXTRACTION TERMINÉE (lots réussis: {lots_reussis}, échecs: {lots_echoues})")
    print("="*80)

if __name__ == "__main__":
    main()
