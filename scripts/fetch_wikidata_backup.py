#!/usr/bin/env python3
"""
Script de récupération des œuvres d'art depuis Wikidata
Version améliorée avec artistes célèbres
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import json
from datetime import datetime
import os
import time

# Configuration
ENDPOINT_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "MuseumWikiBot/1.0 (https://github.com/alexandrebrief/musuemwiki)"

# Liste des artistes célèbres avec leurs IDs Wikidata
ARTISTES_CONNUS = {
    "Claude Monet": "Q296",
    "Pablo Picasso": "Q5593",
    "Vincent van Gogh": "Q5582",
    "Leonard de Vinci": "Q762",
    "Rembrandt": "Q5598",
    "Michel-Ange": "Q5592",
    "Edvard Munch": "Q41406",
    "Salvador Dali": "Q5577",
    "Frida Kahlo": "Q5588",
    "Gustav Klimt": "Q34661",
    "Jackson Pollock": "Q37571",
    "Andy Warhol": "Q5603",
    "Henri Matisse": "Q5589",
    "Paul Cézanne": "Q35548",
    "Pierre-Auguste Renoir": "Q39931",
    "Eugène Delacroix": "Q33477",
    "Jean-Auguste-Dominique Ingres": "Q23380",
    "Francisco de Goya": "Q5432",
    "Diego Velázquez": "Q297",
    "Caravage": "Q42207"
}

def requete_oeuvres_artistes(artiste_id, artiste_nom, limite=200):
    """Récupère les œuvres d'un artiste spécifique"""
    
    requete = f"""
    SELECT DISTINCT ?œuvre ?œuvreLabel ?date ?image ?lieuLabel ?genreLabel ?mouvementLabel
    WHERE {{
      # L'œuvre doit être une peinture (Q3305213)
      ?œuvre wdt:P31/wdt:P279* wd:Q3305213.
      
      # Liée à l'artiste
      ?œuvre wdt:P170 wd:{artiste_id}.
      
      # Récupérer la date de création
      OPTIONAL {{ ?œuvre wdt:P571 ?date. }}
      
      # Récupérer une image
      OPTIONAL {{ ?œuvre wdt:P18 ?image. }}
      
      # Récupérer le lieu de conservation
      OPTIONAL {{ ?œuvre wdt:P276 ?lieu. }}
      
      # Récupérer le genre
      OPTIONAL {{ ?œuvre wdt:P136 ?genre. }}
      
      # Récupérer le mouvement artistique
      OPTIONAL {{ ?œuvre wdt:P135 ?mouvement. }}
      
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "fr,en". 
      }}
    }}
    LIMIT {limite}
    """
    return requete

def fetch_all_artworks():
    """Récupère les œuvres de tous les artistes célèbres"""
    
    print("=" * 60)
    print("🖼️  MuseumWiki - Récupération des œuvres d'artistes célèbres")
    print("=" * 60)
    
    toutes_oeuvres = []
    
    for i, (artiste, artiste_id) in enumerate(ARTISTES_CONNUS.items(), 1):
        print(f"\n📌 [{i}/{len(ARTISTES_CONNUS)}] Récupération des œuvres de {artiste}...")
        
        try:
            # Créer la connexion
            sparql = SPARQLWrapper(ENDPOINT_URL)
            requete = requete_oeuvres_artistes(artiste_id, artiste)
            sparql.setQuery(requete)
            sparql.setReturnFormat(JSON)
            sparql.addCustomParameter("User-Agent", USER_AGENT)
            
            # Exécuter la requête
            results = sparql.query().convert()
            
            # Traiter les résultats
            oeuvres_artiste = []
            for result in results["results"]["bindings"]:
                oeuvre = {
                    "id": result.get("œuvre", {}).get("value", "").split("/")[-1],
                    "titre": result.get("œuvreLabel", {}).get("value", "Titre inconnu"),
                    "createur": artiste,
                    "createur_id": artiste_id,
                    "date": result.get("date", {}).get("value", ""),
                    "image_url": result.get("image", {}).get("value", ""),
                    "lieu": result.get("lieuLabel", {}).get("value", "Lieu inconnu"),
                    "genre": result.get("genreLabel", {}).get("value", ""),
                    "mouvement": result.get("mouvementLabel", {}).get("value", ""),
                    "wikidata_url": result.get("œuvre", {}).get("value", "")
                }
                oeuvres_artiste.append(oeuvre)
            
            print(f"   ✅ {len(oeuvres_artiste)} œuvres trouvées")
            toutes_oeuvres.extend(oeuvres_artiste)
            
            # Pause pour ne pas surcharger Wikidata
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Erreur pour {artiste}: {e}")
    
    return toutes_oeuvres

def save_data(artworks):
    """Sauvegarde les données"""
    
    os.makedirs("data", exist_ok=True)
    os.makedirs("../data", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Statistiques
    print("\n" + "=" * 60)
    print("📊 STATISTIQUES")
    print("=" * 60)
    print(f"Total œuvres: {len(artworks)}")
    
    if artworks:
        df = pd.DataFrame(artworks)
        
        # Stats par artiste
        print("\n📈 Répartition par artiste:")
        for artiste, count in df['createur'].value_counts().head(10).items():
            print(f"   {artiste}: {count} œuvres")
        
        # Stats images
        avec_image = len(df[df['image_url'] != ''])
        print(f"\n🖼️  Avec image: {avec_image}/{len(artworks)} ({avec_image/len(artworks)*100:.1f}%)")
        
        # Sauvegarde JSON
        json_file = f"data/artworks_{timestamp}.json"
        df.to_json(json_file, orient='records', indent=2, force_ascii=False)
        print(f"\n💾 JSON sauvegardé: {json_file}")
        
        # Sauvegarde CSV
        csv_file = f"data/artworks_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"💾 CSV sauvegardé: {csv_file}")
        
        # Copie vers le dossier data principal
        latest_file = "../data/artworks_latest.csv"
        df.to_csv(latest_file, index=False, encoding='utf-8')
        print(f"💾 Fichier principal mis à jour: {latest_file}")
        
        return json_file, csv_file
    
    return None, None

def main():
    """Fonction principale"""
    
    print("=" * 60)
    print("🖼️  MUSEUMWIKI - COLLECTION DES GRANDS MAÎTRES")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎨 {len(ARTISTES_CONNUS)} artistes célèbres sélectionnés")
    print("=" * 60)
    
    # Récupérer les œuvres
    artworks = fetch_all_artworks()
    
    # Sauvegarder
    if artworks:
        save_data(artworks)
        print("\n" + "=" * 60)
        print("✨ MISE À JOUR TERMINÉE AVEC SUCCÈS !")
        print("=" * 60)
    else:
        print("\n❌ Aucune donnée récupérée")

if __name__ == "__main__":
    main()
