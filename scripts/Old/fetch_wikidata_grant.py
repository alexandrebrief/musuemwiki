#!/usr/bin/env python3
"""
Script d'extraction des œuvres de Grant Wood
Récupère TOUS les champs disponibles pour chaque œuvre
"""

import time
import json
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON

# Configuration
USER_AGENT = "MuseumWikiBot/7.0 (https://github.com/alexandrebrief/museumwiki)"
ENDPOINT_URL = "https://query.wikidata.org/sparql"
ARTIST_NAME = "Grant Wood"
ARTIST_QID = "Q217434"  # QID de Grant Wood sur Wikidata

def get_sparql():
    """Crée une connexion SPARQL"""
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(120)
    sparql.addCustomParameter("User-Agent", USER_AGENT)
    return sparql

def execute_query(query, description=""):
    """Exécute une requête SPARQL"""
    print(f"🔍 Exécution: {description}")
    try:
        sparql = get_sparql()
        sparql.setQuery(query)
        results = sparql.query().convert()
        time.sleep(1)  # Pause de courtoisie
        return results
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def get_grant_wood_artworks():
    """
    Récupère TOUTES les œuvres de Grant Wood avec tous les champs disponibles
    """
    query = f"""
    SELECT DISTINCT ?œuvre ?œuvreLabel 
           ?dateCreation ?image ?hauteur ?largeur ?materiau ?technique 
           ?collection ?collectionLabel ?lieuConservation ?lieuLabel
           ?description ?description_fr ?description_en
           ?inventaire ?dateDebut ?dateFin ?siecle ?genre ?genreLabel
           ?mouvement ?mouvementLabel ?influencePar ?influenceParLabel
           ?exposition ?expositionLabel ?proprietaire ?proprietaireLabel
    WHERE {{
      # L'œuvre doit être créée par Grant Wood (Q217434)
      ?œuvre wdt:P170 wd:{ARTIST_QID}.
      
      # C'est une œuvre d'art (peinture, dessin, etc.)
      ?œuvre wdt:P31/wdt:P279* wd:Q3305213.  # Peinture
      
      # Récupérer les labels en français et anglais
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "fr,en". 
        ?œuvre rdfs:label ?œuvreLabel.
        ?collection rdfs:label ?collectionLabel.
        ?lieu rdfs:label ?lieuLabel.
        ?genre rdfs:label ?genreLabel.
        ?mouvement rdfs:label ?mouvementLabel.
        ?influencePar rdfs:label ?influenceParLabel.
        ?exposition rdfs:label ?expositionLabel.
        ?proprietaire rdfs:label ?proprietaireLabel.
      }}
      
      # Tous les champs optionnels
      OPTIONAL {{ ?œuvre wdt:P571 ?dateCreation. }}
      OPTIONAL {{ ?œuvre wdt:P18 ?image. }}
      OPTIONAL {{ ?œuvre wdt:P2048 ?hauteur. }}  # Hauteur
      OPTIONAL {{ ?œuvre wdt:P2049 ?largeur. }}  # Largeur
      OPTIONAL {{ ?œuvre wdt:P186 ?materiau. }}  # Matériau
      OPTIONAL {{ ?œuvre wdt:P2079 ?technique. }}  # Technique de fabrication
      OPTIONAL {{ ?œuvre wdt:P195 ?collection. }}  # Collection
      OPTIONAL {{ ?œuvre wdt:P276 ?lieuConservation. }}  # Lieu de conservation
      BIND(?lieuConservation AS ?lieu)
      OPTIONAL {{ ?œuvre wdt:P217 ?inventaire. }}  # Numéro d'inventaire
      OPTIONAL {{ ?œuvre wdt:P571 ?dateDebut. }}  # Date de début
      OPTIONAL {{ ?œuvre wdt:P576 ?dateFin. }}  # Date de fin
      OPTIONAL {{ ?œuvre wdt:P2348 ?siecle. }}  # Siècle
      OPTIONAL {{ ?œuvre wdt:P136 ?genre. }}  # Genre (portrait, paysage...)
      OPTIONAL {{ ?œuvre wdt:P135 ?mouvement. }}  # Mouvement artistique
      OPTIONAL {{ ?œuvre wdt:P737 ?influencePar. }}  # Influencé par
      OPTIONAL {{ ?œuvre wdt:P608 ?exposition. }}  # Expositions
      OPTIONAL {{ ?œuvre wdt:P127 ?proprietaire. }}  # Propriétaire
      
      # Descriptions
      OPTIONAL {{ ?œuvre schema:description ?description_fr. FILTER(LANG(?description_fr) = "fr") }}
      OPTIONAL {{ ?œuvre schema:description ?description_en. FILTER(LANG(?description_en) = "en") }}
    }}
    ORDER BY ?œuvreLabel
    """
    
    return execute_query(query, f"Œuvres de {ARTIST_NAME}")

def format_results(results):
    """Formate les résultats en JSON lisible"""
    if not results or 'results' not in results:
        return []
    
    artworks = []
    bindings = results['results']['bindings']
    
    for binding in bindings:
        artwork = {
            # Identifiants
            'wikidata_id': binding.get('œuvre', {}).get('value', '').split('/')[-1],
            'wikidata_url': binding.get('œuvre', {}).get('value', ''),
            'titre': binding.get('œuvreLabel', {}).get('value', 'Sans titre'),
            
            # Métadonnées de base
            'createur': ARTIST_NAME,
            'createur_qid': ARTIST_QID,
            
            # Dates
            'date_creation': binding.get('dateCreation', {}).get('value', ''),
            'date_debut': binding.get('dateDebut', {}).get('value', ''),
            'date_fin': binding.get('dateFin', {}).get('value', ''),
            'siecle': binding.get('siecle', {}).get('value', ''),
            
            # Dimensions
            'hauteur': binding.get('hauteur', {}).get('value', ''),
            'largeur': binding.get('largeur', {}).get('value', ''),
            
            # Technique et matériaux
            'materiau': binding.get('materiau', {}).get('value', ''),
            'technique': binding.get('technique', {}).get('value', ''),
            
            # Localisation
            'collection': binding.get('collectionLabel', {}).get('value', ''),
            'collection_qid': binding.get('collection', {}).get('value', '').split('/')[-1] if binding.get('collection') else '',
            'lieu_conservation': binding.get('lieuLabel', {}).get('value', ''),
            'lieu_qid': binding.get('lieuConservation', {}).get('value', '').split('/')[-1] if binding.get('lieuConservation') else '',
            'inventaire': binding.get('inventaire', {}).get('value', ''),
            
            # Images
            'image_url': binding.get('image', {}).get('value', ''),
            
            # Classification
            'genre': binding.get('genreLabel', {}).get('value', ''),
            'genre_qid': binding.get('genre', {}).get('value', '').split('/')[-1] if binding.get('genre') else '',
            'mouvement': binding.get('mouvementLabel', {}).get('value', ''),
            'mouvement_qid': binding.get('mouvement', {}).get('value', '').split('/')[-1] if binding.get('mouvement') else '',
            
            # Influences
            'influence_par': binding.get('influenceParLabel', {}).get('value', ''),
            'influence_par_qid': binding.get('influencePar', {}).get('value', '').split('/')[-1] if binding.get('influencePar') else '',
            
            # Descriptions
            'description_fr': binding.get('description_fr', {}).get('value', ''),
            'description_en': binding.get('description_en', {}).get('value', ''),
            
            # Autres
            'expositions': binding.get('expositionLabel', {}).get('value', ''),
            'proprietaire': binding.get('proprietaireLabel', {}).get('value', ''),
            
            # Métadonnées du script
            'date_extraction': datetime.now().isoformat(),
            'source': 'Wikidata'
        }
        artworks.append(artwork)
    
    return artworks

def save_to_json(artworks, filename="grant_wood_artworks.json"):
    """Sauvegarde les résultats en JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(artworks, f, indent=2, ensure_ascii=False)
    print(f"💾 Données sauvegardées dans {filename}")

def display_summary(artworks):
    """Affiche un résumé des œuvres trouvées"""
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ DES ŒUVRES DE GRANT WOOD")
    print("="*80)
    print(f"🎨 Nombre d'œuvres trouvées : {len(artworks)}")
    
    if artworks:
        print("\n🖼️  Liste des œuvres :")
        for i, artwork in enumerate(artworks, 1):
            print(f"\n  {i}. {artwork['titre']}")
            
            if artwork['date_creation']:
                print(f"     📅 Date: {artwork['date_creation']}")
            if artwork['image_url']:
                print(f"     🖼️  Image: {artwork['image_url']}")
            if artwork['collection']:
                print(f"     🏛️  Collection: {artwork['collection']}")
            if artwork['lieu_conservation']:
                print(f"     📍 Lieu: {artwork['lieu_conservation']}")
            if artwork['technique']:
                print(f"     🎨 Technique: {artwork['technique']}")
            if artwork['genre']:
                print(f"     🏷️  Genre: {artwork['genre']}")
            if artwork['mouvement']:
                print(f"     🌊 Mouvement: {artwork['mouvement']}")
            if artwork['description_fr']:
                print(f"     📝 Description: {artwork['description_fr'][:100]}...")

def main():
    """Fonction principale"""
    print("="*80)
    print(f"🖼️  EXTRACTION DES ŒUVRES DE {ARTIST_NAME}")
    print("="*80)
    
    # Récupérer les œuvres
    results = get_grant_wood_artworks()
    
    if results:
        # Formater les résultats
        artworks = format_results(results)
        
        # Afficher le résumé
        display_summary(artworks)
        
        # Sauvegarder en JSON
        save_to_json(artworks)
        
        # Sauvegarder aussi en JSON lisible pour l'inspection
        with open("grant_wood_details.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("\n💾 Données brutes sauvegardées dans grant_wood_details.json")
        
        print(f"\n✅ Extraction terminée avec succès!")
        print(f"📊 Total: {len(artworks)} œuvres trouvées")
    else:
        print("❌ Aucune œuvre trouvée ou erreur lors de la requête")

if __name__ == "__main__":
    main()
