#!/usr/bin/env python3
"""
Script d'import du JSON MBA Lyon vers PostgreSQL local
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
DB_CONFIG = {
    "host": "localhost",
    "database": "museumwiki",
    "user": "superadmin",
    "password": "Lahess!2"
}

JSON_FILE = "mba_lyon_complet.json"

def connect_db():
    """Connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion à PostgreSQL établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return None

def extract_year(date_str):
    """Extrait l'année d'une date ISO"""
    if not date_str or not isinstance(date_str, str):
        return None
    if date_str.startswith('http'):  # Ignorer les URLs
        return None
    if len(date_str) >= 4 and date_str[:4].isdigit():
        return date_str[:4]
    return None

def prepare_artwork_for_db(oeuvre):
    """Prépare une œuvre pour l'insertion en base"""
    
    # Extraire l'année de la date
    date_complete = oeuvre.get('date_creation', '')
    annee = extract_year(date_complete)
    
    return {
        'id': oeuvre.get('id'),
        'titre': oeuvre.get('titre_fr') or oeuvre.get('titre_en') or oeuvre.get('titre_fallback', 'Sans titre'),
        'createur': oeuvre.get('createur_nom', 'Inconnu'),
        'createur_id': oeuvre.get('createur_id'),
        'date': annee,  # On garde seulement l'année
        'date_complete': date_complete,  # Optionnel : garder la date complète
        'image_url': oeuvre.get('image_url', ''),
        'lieu': oeuvre.get('lieu', ''),
        'genre': oeuvre.get('type', ''),  # Dans ta table, 'genre' correspond au type
        'mouvement': oeuvre.get('mouvement', ''),
        'wikidata_url': oeuvre.get('wikidata_url', ''),
        'technique': oeuvre.get('technique', ''),
        'collection': oeuvre.get('collection', ''),
        'inventaire': '',  # À remplir si disponible
        'createur_naissance': None,
        'createur_deces': None,
        'createur_nationalite': None,
        'instance_of': 'peinture' if 'peinture' in oeuvre.get('type', '').lower() else 'œuvre d\'art',
        'pays': None,
        'copyright': 'Domaine public' if annee and int(annee) < 1920 else None
    }

def insert_artworks(conn, oeuvres):
    """Insère les œuvres dans la base"""
    cur = conn.cursor()
    
    inserted = 0
    updated = 0
    errors = 0
    
    print("\n📦 Import en base...")
    
    for i, oeuvre in enumerate(oeuvres, 1):
        try:
            data = prepare_artwork_for_db(oeuvre)
            
            # Vérifier si l'œuvre existe déjà
            cur.execute("SELECT id FROM artworks WHERE id = %s", (data['id'],))
            exists = cur.fetchone()
            
            if exists:
                # Mise à jour
                cur.execute("""
                    UPDATE artworks SET
                        titre = %s,
                        createur = %s,
                        createur_id = %s,
                        date = %s,
                        image_url = %s,
                        lieu = %s,
                        genre = %s,
                        mouvement = %s,
                        wikidata_url = %s,
                        technique = %s,
                        collection = %s
                    WHERE id = %s
                """, (
                    data['titre'],
                    data['createur'],
                    data['createur_id'],
                    data['date'],
                    data['image_url'],
                    data['lieu'],
                    data['genre'],
                    data['mouvement'],
                    data['wikidata_url'],
                    data['technique'],
                    data['collection'],
                    data['id']
                ))
                updated += 1
            else:
                # Insertion
                cur.execute("""
                    INSERT INTO artworks (
                        id, titre, createur, createur_id, date, image_url,
                        lieu, genre, mouvement, wikidata_url, technique,
                        collection, instance_of, copyright
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data['id'],
                    data['titre'],
                    data['createur'],
                    data['createur_id'],
                    data['date'],
                    data['image_url'],
                    data['lieu'],
                    data['genre'],
                    data['mouvement'],
                    data['wikidata_url'],
                    data['technique'],
                    data['collection'],
                    data['instance_of'],
                    data['copyright']
                ))
                inserted += 1
            
            # Progression
            if i % 50 == 0:
                conn.commit()
                print(f"  ⏳ Progression: {i}/{len(oeuvres)} (insert: {inserted}, update: {updated})")
                
        except Exception as e:
            print(f"  ⚠️ Erreur sur {oeuvre.get('id', 'inconnu')}: {e}")
            errors += 1
    
    # Commit final
    conn.commit()
    cur.close()
    
    return inserted, updated, errors

def verify_import(conn):
    """Vérifie que les données sont bien en base"""
    cur = conn.cursor()
    
    # Compter les œuvres du MBA Lyon
    cur.execute("""
        SELECT COUNT(*) FROM artworks 
        WHERE collection LIKE '%Lyon%' OR lieu LIKE '%Lyon%'
    """)
    count = cur.fetchone()[0]
    
    # Quelques exemples
    cur.execute("""
        SELECT titre, createur, date 
        FROM artworks 
        WHERE collection LIKE '%Lyon%'
        LIMIT 5
    """)
    exemples = cur.fetchall()
    
    cur.close()
    return count, exemples

def main():
    print("="*80)
    print("📥 IMPORT DU MBA LYON VERS BASE LOCALE")
    print("="*80)
    
    # 1. Charger le JSON
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            oeuvres = json.load(f)
        print(f"✅ {len(oeuvres)} œuvres chargées depuis {JSON_FILE}")
    except Exception as e:
        print(f"❌ Erreur chargement JSON: {e}")
        return
    
    # 2. Connexion à la base
    conn = connect_db()
    if not conn:
        return
    
    # 3. Demander confirmation
    print(f"\n📊 Prêt à importer {len(oeuvres)} œuvres")
    print(f"   - Nouvelles insertions: à déterminer")
    print(f"   - Mises à jour: à déterminer")
    
    reponse = input("\n👉 Démarrer l'import ? (o/n): ")
    if reponse.lower() != 'o':
        print("⏸️ Import annulé")
        conn.close()
        return
    
    # 4. Lancer l'import
    inserted, updated, errors = insert_artworks(conn, oeuvres)
    
    # 5. Résultats
    print("\n" + "="*80)
    print("📊 RÉSULTATS DE L'IMPORT")
    print("="*80)
    print(f"✅ Nouvelles œuvres: {inserted}")
    print(f"🔄 Mises à jour: {updated}")
    print(f"⚠️ Erreurs: {errors}")
    print(f"📦 Total traité: {len(oeuvres)}")
    
    # 6. Vérification
    count, exemples = verify_import(conn)
    print(f"\n📊 Vérification: {count} œuvres du MBA Lyon en base")
    
    if exemples:
        print("\n🖼️  Exemples:")
        for titre, createur, date in exemples:
            print(f"  • {titre} - {createur} ({date or 'date inconnue'})")
    
    conn.close()
    print("\n✅ Import terminé!")

if __name__ == "__main__":
    main()
