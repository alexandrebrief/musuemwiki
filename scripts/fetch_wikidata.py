#!/usr/bin/env python3
"""
Script de récupération massive des œuvres d'art depuis Wikidata
Version "Big Data" - Peut récupérer des dizaines de milliers d'œuvres
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import json
from datetime import datetime
import os
import time
import sys

# Configuration
ENDPOINT_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "MuseumWikiBot/1.0 (https://github.com/alexandrebrief/musuemwiki)"

# ============================================
# LISTE ÉLARGIE DES ARTISTES (plus de 50 artistes majeurs)
# ============================================
ARTISTES_CONNUS = {
    # Impressionnistes et post-impressionnistes
    "Claude Monet": "Q296",
    "Pierre-Auguste Renoir": "Q39931",
    "Edgar Degas": "Q46373",
    "Paul Cézanne": "Q35548",
    "Vincent van Gogh": "Q5582",
    "Paul Gauguin": "Q37693",
    "Camille Pissarro": "Q134741",
    "Alfred Sisley": "Q175130",
    "Berthe Morisot": "Q105320",
    "Mary Cassatt": "Q173223",
    
    # Renaissance et Baroque
    "Leonard de Vinci": "Q762",
    "Michel-Ange": "Q5592",
    "Raphaël": "Q5597",
    "Titien": "Q47551",
    "Caravage": "Q42207",
    "Rembrandt": "Q5598",
    "Vermeer": "Q41264",
    "Rubens": "Q5599",
    "Velázquez": "Q297",
    "Goya": "Q5432",
    
    # Modernes
    "Pablo Picasso": "Q5593",
    "Henri Matisse": "Q5589",
    "Amedeo Modigliani": "Q120993",
    "Gustav Klimt": "Q34661",
    "Egon Schiele": "Q44032",
    "Wassily Kandinsky": "Q61064",
    "Paul Klee": "Q44007",
    "Joan Miró": "Q152384",
    "Salvador Dali": "Q5577",
    "Frida Kahlo": "Q5588",
    
    # Expressionnistes et abstraits
    "Edvard Munch": "Q41406",
    "James Ensor": "Q158840",
    "Emil Nolde": "Q152762",
    "Ernst Ludwig Kirchner": "Q153602",
    "Jackson Pollock": "Q37571",
    "Mark Rothko": "Q160149",
    "Willem de Kooning": "Q132305",
    "Francis Bacon": "Q154340",
    
    # Romantiques et académiques
    "Eugène Delacroix": "Q33477",
    "Théodore Géricault": "Q184212",
    "Jean-Auguste-Dominique Ingres": "Q23380",
    "William Turner": "Q55842",
    "John Constable": "Q159297",
    "Caspar David Friedrich": "Q104884",
    "Gustave Courbet": "Q34618",
    "Jean-François Millet": "Q148458",
    
    # Américains
    "Edward Hopper": "Q203401",
    "Georgia O'Keeffe": "Q46408",
    "Andy Warhol": "Q5603",
    "Roy Lichtenstein": "Q151679",
    "Norman Rockwell": "Q271884",
    "Grant Wood": "Q335363",
    
    # Sculpteurs (qui ont aussi des peintures parfois)
    "Auguste Rodin": "Q30755",
    "Camille Claudel": "Q237768",
    "Henry Moore": "Q151195",
    "Alberto Giacometti": "Q157194",
    
    # Divers
    "Marc Chagall": "Q93284",
    "Fernand Léger": "Q157183",
    "Georges Braque": "Q153793",
    "Piet Mondrian": "Q151803",
    "Kazimir Malevitch": "Q130777",
    "Marcel Duchamp": "Q5912"
}

# ============================================
# FONCTION POUR RÉCUPÉRER LES ŒUVRES D'UN ARTISTE
# ============================================
def requete_oeuvres_artistes(artiste_id, artiste_nom, limite=1000):
    """Récupère les œuvres d'un artiste spécifique avec limite élevée"""
    
    requete = f"""
    SELECT DISTINCT ?œuvre ?œuvreLabel ?date ?image ?lieuLabel ?genreLabel ?mouvementLabel
    WHERE {{
      # L'œuvre doit être une peinture (Q3305213) ou une sculpture (Q860861) ou un dessin (Q93184)
      {{ ?œuvre wdt:P31/wdt:P279* wd:Q3305213. }} UNION
      {{ ?œuvre wdt:P31/wdt:P279* wd:Q860861. }} UNION
      {{ ?œuvre wdt:P31/wdt:P279* wd:Q93184. }}
      
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

# ============================================
# FONCTION PRINCIPALE DE RÉCUPÉRATION
# ============================================
def fetch_all_artworks():
    """Récupère les œuvres de tous les artistes célèbres"""
    
    print("=" * 70)
    print("🖼️  MUSEUMWIKI - RÉCUPÉRATION MASSIVE D'ŒUVRES D'ART")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎨 {len(ARTISTES_CONNUS)} artistes sélectionnés")
    print(f"⚡ Mode : récupération intensive (max 1000 œuvres par artiste)")
    print("=" * 70)
    
    toutes_oeuvres = []
    total_artistes = len(ARTISTES_CONNUS)
    
    for i, (artiste, artiste_id) in enumerate(ARTISTES_CONNUS.items(), 1):
        print(f"\n📌 [{i}/{total_artistes}] Récupération des œuvres de {artiste}...")
        
        try:
            # Créer la connexion
            sparql = SPARQLWrapper(ENDPOINT_URL)
            sparql.setQuery(requete_oeuvres_artistes(artiste_id, artiste, limite=1000))
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
            
            # Pause pour ne pas surcharger Wikidata (important pour les grosses requêtes)
            time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Erreur pour {artiste}: {e}")
            time.sleep(5)  # Pause plus longue en cas d'erreur
    
    return toutes_oeuvres

# ============================================
# SAUVEGARDE DES DONNÉES
# ============================================
def save_data(artworks):
    """Sauvegarde les données avec statistiques détaillées"""
    
    os.makedirs("data", exist_ok=True)
    os.makedirs("../data", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Statistiques
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)
    print(f"📈 TOTAL GÉNÉRAL : {len(artworks)} œuvres")
    
    if artworks:
        df = pd.DataFrame(artworks)
        
        # Stats par artiste
        print("\n🏆 TOP 20 DES ARTISTES:")
        artist_stats = df['createur'].value_counts().head(20)
        for artiste, count in artist_stats.items():
            print(f"   {artiste}: {count} œuvres")
        
        # Stats images
        avec_image = len(df[df['image_url'] != ''])
        sans_image = len(artworks) - avec_image
        print(f"\n🖼️  Avec image: {avec_image} ({avec_image/len(artworks)*100:.1f}%)")
        print(f"📄 Sans image: {sans_image} ({sans_image/len(artworks)*100:.1f}%)")
        
        # Stats par type (approximatif via les IDs)
        print(f"\n🏛️  Musées représentés: {df['lieu'].nunique()}")
        print(f"🎨 Genres représentés: {df['genre'].nunique()}")
        
        # Sauvegarde JSON
        json_file = f"data/artworks_{timestamp}.json"
        df.to_json(json_file, orient='records', indent=2, force_ascii=False)
        print(f"\n💾 JSON sauvegardé: {json_file}")
        
        # Sauvegarde CSV
        csv_file = f"data/artworks_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"💾 CSV sauvegardé: {csv_file}")
        
        # Copie vers le dossier data principal (pour l'app)
        latest_file = "../data/artworks_latest.csv"
        df.to_csv(latest_file, index=False, encoding='utf-8')
        print(f"💾 Fichier principal mis à jour: {latest_file}")
        
        return json_file, csv_file
    
    return None, None

# ============================================
# MAIN
# ============================================
def main():
    """Fonction principale"""
    
    print("\n" + "=" * 70)
    print("🚀 LANCEMENT DE LA RÉCUPÉRATION MASSIVE")
    print("=" * 70)
    
    # Récupérer les œuvres
    artworks = fetch_all_artworks()
    
    # Sauvegarder
    if artworks:
        save_data(artworks)
        print("\n" + "=" * 70)
        print("✨ MISE À JOUR TERMINÉE AVEC SUCCÈS !")
        print(f"📊 Total: {len(artworks)} œuvres")
        print("=" * 70)
    else:
        print("\n❌ Aucune donnée récupérée")

if __name__ == "__main__":
    main()
