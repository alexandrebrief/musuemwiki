#!/usr/bin/env python3
"""
Script d'extraction des œuvres de Grant Wood
Avec élimination automatique des doublons
Récupère 100 œuvres (ou moins si pas assez disponibles)
"""

import time
import json
import hashlib
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON

# ============================================
# CONFIGURATION
# ============================================
USER_AGENT = "MuseumWikiBot/9.0 (https://github.com/alexandrebrief/museumwiki)"
ENDPOINT_URL = "https://query.wikidata.org/sparql"
ARTIST_NAME = "Grant Wood"
ARTIST_QID = "Q217434"
MAX_ARTWORKS = 100
OUTPUT_FILE = "grant_wood_100_oeuvres.json"

# ============================================
# FONCTIONS SPARQL
# ============================================

def get_sparql():
    """Crée une connexion SPARQL"""
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(120)
    sparql.addCustomParameter("User-Agent", USER_AGENT)
    return sparql

def execute_query(query, description=""):
    """Exécute une requête SPARQL avec gestion d'erreur"""
    print(f"🔍 {description}...")
    try:
        sparql = get_sparql()
        sparql.setQuery(query)
        results = sparql.query().convert()
        time.sleep(1)  # Pause de courtoisie pour Wikidata
        return results
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

# ============================================
# REQUÊTES SPARQL
# ============================================

def get_artworks_query(offset=0, limit=50):
    """
    Requête pour récupérer les œuvres de Grant Wood
    Avec DISTINCT pour éviter les doublons
    """
    return f"""
    SELECT DISTINCT ?œuvre ?œuvreLabel 
           ?dateCreation ?image ?hauteur ?largeur ?materiau ?technique 
           ?collection ?collectionLabel ?lieuConservation ?lieuLabel
           ?description_fr ?description_en ?inventaire ?genre ?genreLabel
           ?mouvement ?mouvementLabel
    WHERE {{
      # L'œuvre doit être créée par Grant Wood
      ?œuvre wdt:P170 wd:{ARTIST_QID}.
      
      # C'est une œuvre d'art (peinture, dessin, etc.)
      ?œuvre wdt:P31/wdt:P279* wd:Q3305213.
      
      # Labels en français et anglais
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "fr,en". 
        ?œuvre rdfs:label ?œuvreLabel.
        ?collection rdfs:label ?collectionLabel.
        ?lieu rdfs:label ?lieuLabel.
        ?genre rdfs:label ?genreLabel.
        ?mouvement rdfs:label ?mouvementLabel.
      }}
      
      # Tous les champs optionnels
      OPTIONAL {{ ?œuvre wdt:P571 ?dateCreation. }}
      OPTIONAL {{ ?œuvre wdt:P18 ?image. }}
      OPTIONAL {{ ?œuvre wdt:P2048 ?hauteur. }}
      OPTIONAL {{ ?œuvre wdt:P2049 ?largeur. }}
      OPTIONAL {{ ?œuvre wdt:P186 ?materiau. }}
      OPTIONAL {{ ?œuvre wdt:P2079 ?technique. }}
      OPTIONAL {{ ?œuvre wdt:P195 ?collection. }}
      OPTIONAL {{ ?œuvre wdt:P276 ?lieuConservation. }}
      OPTIONAL {{ ?œuvre wdt:P217 ?inventaire. }}
      OPTIONAL {{ ?œuvre wdt:P136 ?genre. }}
      OPTIONAL {{ ?œuvre wdt:P135 ?mouvement. }}
      
      # Descriptions
      OPTIONAL {{ ?œuvre schema:description ?description_fr. FILTER(LANG(?description_fr) = "fr") }}
      OPTIONAL {{ ?œuvre schema:description ?description_en. FILTER(LANG(?description_en) = "en") }}
    }}
    ORDER BY ?œuvreLabel
    LIMIT {limit}
    OFFSET {offset}
    """

# ============================================
# TRAITEMENT DES RÉSULTATS
# ============================================

def parse_artwork(binding):
    """Convertit un résultat SPARQL en dictionnaire structuré"""
    
    # Extraire l'ID Wikidata de l'URL
    artwork_url = binding.get('œuvre', {}).get('value', '')
    artwork_id = artwork_url.split('/')[-1] if artwork_url else ''
    
    # Créer l'objet œuvre
    artwork = {
        # Identifiants
        'wikidata_id': artwork_id,
        'wikidata_url': artwork_url,
        'titre': binding.get('œuvreLabel', {}).get('value', 'Sans titre'),
        
        # Créateur
        'createur': ARTIST_NAME,
        'createur_qid': ARTIST_QID,
        
        # Date
        'date_creation': binding.get('dateCreation', {}).get('value', ''),
        
        # Image
        'image_url': binding.get('image', {}).get('value', ''),
        
        # Dimensions
        'hauteur': binding.get('hauteur', {}).get('value', ''),
        'largeur': binding.get('largeur', {}).get('value', ''),
        
        # Technique et matériaux
        'materiau': binding.get('materiau', {}).get('value', ''),
        'technique': binding.get('technique', {}).get('value', ''),
        
        # Localisation
        'collection': binding.get('collectionLabel', {}).get('value', ''),
        'collection_id': binding.get('collection', {}).get('value', '').split('/')[-1] if binding.get('collection') else '',
        'lieu_conservation': binding.get('lieuLabel', {}).get('value', ''),
        'lieu_id': binding.get('lieuConservation', {}).get('value', '').split('/')[-1] if binding.get('lieuConservation') else '',
        'inventaire': binding.get('inventaire', {}).get('value', ''),
        
        # Classification
        'genre': binding.get('genreLabel', {}).get('value', ''),
        'genre_id': binding.get('genre', {}).get('value', '').split('/')[-1] if binding.get('genre') else '',
        'mouvement': binding.get('mouvementLabel', {}).get('value', ''),
        'mouvement_id': binding.get('mouvement', {}).get('value', '').split('/')[-1] if binding.get('mouvement') else '',
        
        # Descriptions
        'description_fr': binding.get('description_fr', {}).get('value', ''),
        'description_en': binding.get('description_en', {}).get('value', ''),
        
        # Métadonnées
        'date_extraction': datetime.now().isoformat(),
        'source': 'Wikidata'
    }
    
    return artwork

def remove_duplicates(artworks):
    """
    Supprime les doublons basés sur wikidata_id
    Garde la première occurrence de chaque ID
    """
    vus = set()
    uniques = []
    doublons = 0
    
    for artwork in artworks:
        artwork_id = artwork.get('wikidata_id')
        if artwork_id and artwork_id not in vus:
            vus.add(artwork_id)
            uniques.append(artwork)
        else:
            doublons += 1
            # Optionnel: afficher les doublons pour debug
            # print(f"  Doublon ignoré: {artwork.get('titre')} ({artwork_id})")
    
    print(f"  🧹 Dédoublonnage: {len(artworks)} → {len(uniques)} uniques ({doublons} doublons supprimés)")
    return uniques

def create_fingerprint(artwork):
    """
    Crée une empreinte unique pour détecter les doublons
    même si l'ID Wikidata est différent (cas rares)
    """
    # Combiner les champs principaux pour créer une signature
    fingerprint_data = f"{artwork.get('titre')}_{artwork.get('date_creation')}_{artwork.get('collection')}"
    return hashlib.md5(fingerprint_data.encode('utf-8')).hexdigest()

def remove_similar_duplicates(artworks):
    """
    Supprime les doublons basés sur une combinaison de champs
    (au cas où certaines œuvres auraient des IDs différents)
    """
    vus = set()
    uniques = []
    
    for artwork in artworks:
        fingerprint = create_fingerprint(artwork)
        if fingerprint not in vus:
            vus.add(fingerprint)
            uniques.append(artwork)
    
    if len(uniques) != len(artworks):
        print(f"  🔍 Doublons par similarité: {len(artworks) - len(uniques)} supprimés")
    
    return uniques

# ============================================
# FONCTION PRINCIPALE
# ============================================

def main():
    print("="*80)
    print(f"🖼️  EXTRACTION DES ŒUVRES DE {ARTIST_NAME}")
    print(f"🎯 Objectif: {MAX_ARTWORKS} œuvres")
    print("="*80)
    
    toutes_les_oeuvres = []
    offset = 0
    limit = 50  # Taille des lots
    total_recu = 0
    
    while total_recu < MAX_ARTWORKS:
        print(f"\n📦 Lot {offset//limit + 1} (offset {offset})...")
        
        # Exécuter la requête
        query = get_artworks_query(offset, limit)
        results = execute_query(query, f"Récupération des œuvres (lot {offset//limit + 1})")
        
        if not results or 'results' not in results:
            print("🏁 Plus de résultats disponibles")
            break
        
        bindings = results['results']['bindings']
        if not bindings:
            print("🏁 Aucune œuvre trouvée dans ce lot")
            break
        
        print(f"  📋 {len(bindings)} œuvres brutes reçues")
        
        # Parser les résultats
        for binding in bindings:
            artwork = parse_artwork(binding)
            toutes_les_oeuvres.append(artwork)
        
        total_recu = len(toutes_les_oeuvres)
        print(f"  📊 Total provisoire: {total_recu} œuvres")
        
        offset += limit
        
        # Petite pause entre les lots
        time.sleep(2)
    
    print("\n" + "="*80)
    print("📊 RÉSULTATS BRUTS")
    print("="*80)
    print(f"✅ Œuvres récupérées: {len(toutes_les_oeuvres)}")
    
    # Étape 1: Dédoublonnage par ID
    print("\n🔄 Étape 1: Dédoublonnage par ID Wikidata...")
    oeuvres_sans_doublons_id = remove_duplicates(toutes_les_oeuvres)
    
    # Étape 2: Dédoublonnage par similarité (au cas où)
    print("\n🔄 Étape 2: Vérification des doublons par similarité...")
    oeuvres_finales = remove_similar_duplicates(oeuvres_sans_doublons_id)
    
    # Limiter au nombre demandé
    if len(oeuvres_finales) > MAX_ARTWORKS:
        oeuvres_finales = oeuvres_finales[:MAX_ARTWORKS]
        print(f"\n🎯 Limitation à {MAX_ARTWORKS} œuvres")
    
    print("\n" + "="*80)
    print("📊 RÉSULTATS FINAUX")
    print("="*80)
    print(f"🎨 Artiste: {ARTIST_NAME}")
    print(f"📦 Œuvres uniques finales: {len(oeuvres_finales)}")
    
    # Statistiques sur les données
    avec_images = sum(1 for o in oeuvres_finales if o.get('image_url'))
    avec_dates = sum(1 for o in oeuvres_finales if o.get('date_creation'))
    avec_collections = sum(1 for o in oeuvres_finales if o.get('collection'))
    
    print(f"🖼️  Avec images: {avec_images}/{len(oeuvres_finales)}")
    print(f"📅 Avec dates: {avec_dates}/{len(oeuvres_finales)}")
    print(f"🏛️  Avec collections: {avec_collections}/{len(oeuvres_finales)}")
    
    # Sauvegarde en JSON
    print(f"\n💾 Sauvegarde dans {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(oeuvres_finales, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Fichier sauvegardé avec succès!")
    
    # Afficher quelques exemples
    print("\n🖼️  Exemples d'œuvres:")
    for i, oeuvre in enumerate(oeuvres_finales[:5], 1):
        print(f"\n  {i}. {oeuvre['titre']}")
        if oeuvre['date_creation']:
            print(f"     📅 {oeuvre['date_creation']}")
        if oeuvre['collection']:
            print(f"     🏛️  {oeuvre['collection']}")
        if oeuvre['image_url']:
            print(f"     🖼️  {oeuvre['image_url'][:50]}...")
    
    print("\n" + "="*80)
    print("✅ EXTRACTION TERMINÉE AVEC SUCCÈS!")
    print("="*80)

if __name__ == "__main__":
    main()
