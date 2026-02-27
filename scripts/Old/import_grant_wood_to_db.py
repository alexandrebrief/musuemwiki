#!/usr/bin/env python3
"""
Script d'import des œuvres de Grant Wood
Adapté à la structure exacte de ta base de données
"""

import json
import psycopg2
from datetime import datetime
import re

# Configuration de ta base locale
DB_CONFIG = {
    "host": "localhost",
    "database": "museumwiki",
    "user": "superadmin",
    "password": "Lahess!2"
}

# Ton fichier JSON
JSON_FILE = "grant_wood_artworks.json"

def connect_db():
    """Établit la connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion à PostgreSQL établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return None

def load_json_data(filename):
    """Charge les données depuis le fichier JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Fichier JSON chargé: {len(data)} œuvres trouvées")
        return data
    except FileNotFoundError:
        print(f"❌ Fichier {filename} non trouvé")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de parsing JSON: {e}")
        return None

def extract_year_from_date(date_str):
    """Extrait l'année d'une date (ex: "1930-01-01" -> 1930)"""
    if not date_str:
        return None
    match = re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', date_str)
    return match.group(0) if match else None

def convert_to_float(value_str):
    """Convertit une chaîne en nombre flottant (pour hauteur/largeur)"""
    if not value_str:
        return None
    try:
        # Extrait les nombres d'une chaîne comme "78 cm" -> 78.0
        numbers = re.findall(r'\d+\.?\d*', str(value_str))
        return float(numbers[0]) if numbers else None
    except (ValueError, IndexError):
        return None

def get_pays_from_lieu(lieu):
    """Déduit le pays du lieu de conservation"""
    if not lieu:
        return None
    
    lieu_lower = lieu.lower()
    pays_mapping = {
        'france': 'France',
        'paris': 'France',
        'louvre': 'France',
        'usa': 'États-Unis',
        'united states': 'États-Unis',
        'new york': 'États-Unis',
        'chicago': 'États-Unis',
        'uk': 'Royaume-Uni',
        'london': 'Royaume-Uni',
        'angleterre': 'Royaume-Uni',
        'allemagne': 'Allemagne',
        'berlin': 'Allemagne',
        'italie': 'Italie',
        'florence': 'Italie',
        'espagne': 'Espagne',
        'madrid': 'Espagne'
    }
    
    for key, pays in pays_mapping.items():
        if key in lieu_lower:
            return pays
    return None

def insert_artwork(cur, artwork):
    """Insère ou met à jour une œuvre"""
    
    # Conversion des données
    wikidata_id = artwork.get('wikidata_id')
    titre = artwork.get('titre', 'Sans titre')
    createur = artwork.get('createur', 'Grant Wood')
    createur_id = artwork.get('createur_qid')
    
    # La date : essayer d'extraire l'année
    date_raw = artwork.get('date_creation', '')
    date = extract_year_from_date(date_raw)
    
    image_url = artwork.get('image_url', '')
    lieu = artwork.get('lieu_conservation', '')
    genre = artwork.get('genre', '')
    mouvement = artwork.get('mouvement', '')
    wikidata_url = artwork.get('wikidata_url', '')
    
    # Dimensions (conversion en float)
    hauteur = convert_to_float(artwork.get('hauteur'))
    largeur = convert_to_float(artwork.get('largeur'))
    
    technique = artwork.get('technique', '')
    inventaire = artwork.get('inventaire', '')
    collection = artwork.get('collection', '')
    
    # Champs supplémentaires à compléter plus tard
    createur_naissance = None  # À enrichir plus tard
    createur_deces = None      # À enrichir plus tard
    createur_nationalite = "Américaine"  # Grant Wood est américain
    instance_of = "peinture"   # Par défaut
    pays = get_pays_from_lieu(lieu)
    copyright = "Domaine public" if not date or int(date) < 1920 else "Sous droit d'auteur"
    
    # Requête d'insertion avec gestion de conflit
    query = """
        INSERT INTO artworks (
            id, titre, createur, createur_id, date, image_url, lieu,
            genre, mouvement, wikidata_url, hauteur, largeur, technique,
            inventaire, collection, createur_naissance, createur_deces,
            createur_nationalite, instance_of, pays, copyright
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO UPDATE SET
            titre = EXCLUDED.titre,
            date = EXCLUDED.date,
            image_url = EXCLUDED.image_url,
            lieu = EXCLUDED.lieu,
            genre = EXCLUDED.genre,
            mouvement = EXCLUDED.mouvement,
            hauteur = EXCLUDED.hauteur,
            largeur = EXCLUDED.largeur,
            technique = EXCLUDED.technique,
            collection = EXCLUDED.collection,
            pays = EXCLUDED.pays,
            copyright = EXCLUDED.copyright,
            last_updated = NOW()
        WHERE artworks.titre IS DISTINCT FROM EXCLUDED.titre
           OR artworks.image_url IS DISTINCT FROM EXCLUDED.image_url
    """
    
    cur.execute(query, (
        wikidata_id, titre, createur, createur_id, date, image_url, lieu,
        genre, mouvement, wikidata_url, hauteur, largeur, technique,
        inventaire, collection, createur_naissance, createur_deces,
        createur_nationalite, instance_of, pays, copyright
    ))
    
    return cur.rowcount

def main():
    print("="*80)
    print("📥 IMPORT DES ŒUVRES DE GRANT WOOD")
    print("="*80)
    
    # 1. Connexion à la base
    conn = connect_db()
    if not conn:
        return
    
    # 2. Charger le JSON
    artworks = load_json_data(JSON_FILE)
    if not artworks:
        conn.close()
        return
    
    print(f"\n📦 Prêt à importer {len(artworks)} œuvres")
    print("-"*80)
    
    # 3. Demander confirmation
    response = input("👉 Démarrer l'import ? (o/n): ")
    if response.lower() != 'o':
        print("⏸️ Import annulé")
        conn.close()
        return
    
    # 4. Lancer l'import
    cur = conn.cursor()
    inserted = 0
    updated = 0
    errors = 0
    
    print("\n🔄 Import en cours...")
    
    for i, artwork in enumerate(artworks, 1):
        try:
            result = insert_artwork(cur, artwork)
            if result == 1:
                inserted += 1
            elif result == 2:  # UPDATE
                updated += 1
            
            # Progression tous les 10
            if i % 10 == 0:
                print(f"  ⏳ Progression: {i}/{len(artworks)}")
                conn.commit()
                
        except Exception as e:
            print(f"  ⚠️ Erreur sur {artwork.get('titre', 'Inconnu')}: {e}")
            errors += 1
    
    # Commit final
    conn.commit()
    cur.close()
    
    print("\n" + "="*80)
    print("📊 RÉSULTATS DE L'IMPORT")
    print("="*80)
    print(f"✅ Nouvelles œuvres: {inserted}")
    print(f"🔄 Mises à jour: {updated}")
    print(f"⚠️ Erreurs: {errors}")
    print(f"📦 Total traité: {len(artworks)}")
    
    # 5. Vérification
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM artworks WHERE createur LIKE '%Grant Wood%'")
    count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT titre, date, collection, lieu 
        FROM artworks 
        WHERE createur LIKE '%Grant Wood%'
        LIMIT 5
    """)
    examples = cur.fetchall()
    
    print(f"\n📊 Vérification: {count} œuvres de Grant Wood en base")
    
    if examples:
        print("\n🖼️  Exemples:")
        for titre, date, collection, lieu in examples:
            print(f"  • {titre} ({date or 'date inconnue'})")
            print(f"    Collection: {collection or 'inconnue'} - Lieu: {lieu or 'inconnu'}")
    
    cur.close()
    conn.close()
    print("\n✅ Import terminé!")

if __name__ == "__main__":
    main()
