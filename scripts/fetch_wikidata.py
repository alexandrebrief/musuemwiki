#!/usr/bin/env python3
"""
Script de récupération des œuvres d'art depuis Wikidata
Pour le projet MuseumWiki
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import json
from datetime import datetime
import os
import sys

# Configuration
ENDPOINT_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "MuseumWikiBot/1.0 (https://github.com/alexandrebrief/musuemwiki)"

# Requête SPARQL pour récupérer les peintures
SPARQL_QUERY = """
SELECT DISTINCT ?œuvre ?œuvreLabel ?créateurLabel ?date ?image ?lieuLabel ?genreLabel ?mouvementLabel
WHERE {
  # L'œuvre doit être une peinture (Q3305213)
  ?œuvre wdt:P31/wdt:P279* wd:Q3305213.
  
  # Récupérer le créateur
  OPTIONAL { ?œuvre wdt:P170 ?créateur. }
  
  # Récupérer la date de création
  OPTIONAL { ?œuvre wdt:P571 ?date. }
  
  # Récupérer une image si disponible
  OPTIONAL { ?œuvre wdt:P18 ?image. }
  
  # Récupérer le lieu de conservation (musée)
  OPTIONAL { ?œuvre wdt:P276 ?lieu. }
  
  # Récupérer le genre (portrait, paysage, etc.)
  OPTIONAL { ?œuvre wdt:P136 ?genre. }
  
  # Récupérer le mouvement artistique
  OPTIONAL { ?œuvre wdt:P135 ?mouvement. }
  
  # Service de labels pour avoir les noms en français
  SERVICE wikibase:label { 
    bd:serviceParam wikibase:language "fr,en". 
  }
}
LIMIT 100
"""

def fetch_wikidata_artworks():
    """Récupère les œuvres d'art depuis Wikidata"""
    
    print(f"🔄 Connexion à Wikidata...")
    
    # Initialiser la connexion
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setQuery(SPARQL_QUERY)
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("User-Agent", USER_AGENT)
    
    try:
        # Exécuter la requête
        print("📥 Téléchargement des données...")
        results = sparql.query().convert()
        
        # Extraire les résultats
        artworks = []
        for result in results["results"]["bindings"]:
            artwork = {
                "id": result.get("œuvre", {}).get("value", "").split("/")[-1],
                "titre": result.get("œuvreLabel", {}).get("value", "Titre inconnu"),
                "createur": result.get("créateurLabel", {}).get("value", "Artiste inconnu"),
                "date": result.get("date", {}).get("value", ""),
                "image_url": result.get("image", {}).get("value", ""),
                "lieu": result.get("lieuLabel", {}).get("value", "Lieu inconnu"),
                "genre": result.get("genreLabel", {}).get("value", ""),
                "mouvement": result.get("mouvementLabel", {}).get("value", ""),
                "wikidata_url": result.get("œuvre", {}).get("value", "")
            }
            artworks.append(artwork)
        
        print(f"✅ {len(artworks)} œuvres récupérées avec succès!")
        return artworks
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération : {e}")
        return []

def save_data(artworks):
    """Sauvegarde les données dans différents formats"""
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs("data", exist_ok=True)
    
    # Timestamp pour la version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sauvegarde en JSON
    json_file = f"data/artworks_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(artworks, f, ensure_ascii=False, indent=2)
    print(f"💾 Données sauvegardées dans {json_file}")
    
    # Sauvegarde en CSV
    if artworks:
        df = pd.DataFrame(artworks)
        csv_file = f"data/artworks_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"💾 Données sauvegardées dans {csv_file}")
        
        # Sauvegarde du dernier jeu de données (pour l'app)
        latest_file = "data/artworks_latest.csv"
        df.to_csv(latest_file, index=False, encoding='utf-8')
        print(f"💾 Mise à jour du fichier latest: {latest_file}")
        
        return json_file, csv_file
    
    return None, None

def main():
    """Fonction principale"""
    print("=" * 50)
    print("🖼️  MuseumWiki - Récupération des données Wikidata")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Récupérer les données
    artworks = fetch_wikidata_artworks()
    
    # Sauvegarder les données
    if artworks:
        json_file, csv_file = save_data(artworks)
        print("\n📊 Statistiques:")
        print(f"   - Total œuvres: {len(artworks)}")
        print(f"   - Avec image: {sum(1 for a in artworks if a['image_url'])}")
        print(f"   - Avec date: {sum(1 for a in artworks if a['date'])}")
        print("\n✨ Données mises à jour avec succès!")
    else:
        print("\n⚠️ Aucune donnée récupérée.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
