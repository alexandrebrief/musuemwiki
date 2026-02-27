#!/usr/bin/env python3
"""
Script d'extraction ULTRA SIMPLE - 100K œuvres
Évite les timeouts en faisant des requêtes très simples
"""

import time
import random
import json
import os
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import psycopg2
from psycopg2.extras import execute_values

# ============================================
# CONFIGURATION
# ============================================
USER_AGENT = "MuseumWikiBot/6.0 (https://github.com/alexandrebrief/museumwiki)"
ENDPOINT_URL = "https://query.wikidata.org/sparql"
TARGET = 100000
BATCH_SIZE = 20  # Encore plus petit
TIMEOUT = 60  # Plus long
MAX_RETRIES = 5
PAUSE_BASE = 2
CHECKPOINT_FILE = "checkpoint_simple.json"

# Connexion PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "database": "museumwiki",
    "user": "superadmin",
    "password": "Lahess!2"
}

# ============================================
# REQUÊTES TRÈS SIMPLES
# ============================================

def get_artists_simple(offset=0):
    """Récupère des artistes - requête ultra simple"""
    return f"""
    SELECT DISTINCT ?artiste ?artisteLabel WHERE {{
      ?artiste wdt:P31 wd:Q5.  # Humain
      ?artiste wdt:P106 wd:Q1028181.  # Peintre
    }}
    LIMIT {BATCH_SIZE}
    OFFSET {offset}
    """

def get_artworks_simple(artist_id):
    """Récupère les œuvres d'un artiste - requête ultra simple"""
    return f"""
    SELECT DISTINCT ?œuvre ?œuvreLabel ?date ?image WHERE {{
      ?œuvre wdt:P31/wdt:P279* wd:Q3305213.  # Peinture
      ?œuvre wdt:P170 wd:{artist_id}.
      OPTIONAL {{ ?œuvre wdt:P571 ?date. }}
      OPTIONAL {{ ?œuvre wdt:P18 ?image. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    LIMIT 50
    """

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def get_sparql():
    """Crée une connexion SPARQL avec timeout long"""
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(TIMEOUT)
    sparql.addCustomParameter("User-Agent", USER_AGENT)
    return sparql

def fetch_with_retry(query, description=""):
    """Exécute une requête avec retry et pauses adaptatives"""
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"   🔄 Tentative {attempt}/{MAX_RETRIES}...")
            sparql = get_sparql()
            sparql.setQuery(query)
            results = sparql.query().convert()
            
            # Pause adaptative
            time.sleep(random.uniform(PAUSE_BASE, PAUSE_BASE * 1.5))
            return results
            
        except Exception as e:
            error_str = str(e)
            wait_time = attempt * 30  # 30s, 60s, 90s...
            
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                print(f"   ⏳ Timeout, pause {wait_time}s...")
            elif "429" in error_str:
                print(f"   ⏳ Rate limit, pause {wait_time}s...")
            else:
                print(f"   ⚠️ Erreur: {error_str[:100]}")
            
            time.sleep(wait_time)
    
    print(f"   ❌ Échec après {MAX_RETRIES} tentatives")
    return None

def load_checkpoint():
    """Charge la progression"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {
        'artist_offset': 0,
        'processed_artists': [],
        'total_artworks': 0
    }

def save_checkpoint(artist_offset, processed_artists, total_artworks):
    """Sauvegarde la progression"""
    # Ne garder que les 100 derniers pour éviter un fichier trop gros
    recent_artists = processed_artists[-100:] if len(processed_artists) > 100 else processed_artists
    
    checkpoint = {
        'artist_offset': artist_offset,
        'processed_artists': recent_artists,
        'total_artworks': total_artworks,
        'timestamp': datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"   💾 Checkpoint: {total_artworks} œuvres")

def save_to_postgresql(artworks):
    """Sauvegarde en base (version simple)"""
    if not artworks:
        return 0
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    query = """
        INSERT INTO artworks (
            id, titre, createur, date, image_url, wikidata_url, last_updated
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            titre = EXCLUDED.titre,
            createur = EXCLUDED.createur,
            date = EXCLUDED.date,
            image_url = EXCLUDED.image_url,
            wikidata_url = EXCLUDED.wikidata_url,
            last_updated = NOW()
    """
    
    values = [[
        a['id'], a['titre'], a['createur'], a['date'], 
        a['image_url'], a['wikidata_url']
    ] for a in artworks]
    
    execute_values(cur, query, values)
    conn.commit()
    
    inserted = cur.rowcount
    cur.close()
    conn.close()
    
    return inserted

def process_artists_results(results):
    """Extrait la liste des artistes des résultats"""
    artists = []
    if not results or 'results' not in results:
        return artists
    
    for binding in results['results']['bindings']:
        artist_id = binding.get('artiste', {}).get('value', '').split('/')[-1]
        artist_name = binding.get('artisteLabel', {}).get('value', 'Inconnu')
        if artist_id:
            artists.append((artist_id, artist_name))
    
    return artists

def process_artworks_results(results, artist_name):
    """Traite les résultats d'œuvres"""
    artworks = []
    if not results or 'results' not in results:
        return artworks
    
    for binding in results['results']['bindings']:
        try:
            artwork_id = binding.get('œuvre', {}).get('value', '').split('/')[-1]
            if not artwork_id:
                continue
            
            artwork = {
                'id': artwork_id,
                'titre': binding.get('œuvreLabel', {}).get('value', ''),
                'createur': artist_name,
                'date': binding.get('date', {}).get('value', '')[:10] if binding.get('date') else '',
                'image_url': binding.get('image', {}).get('value', ''),
                'wikidata_url': f"https://www.wikidata.org/wiki/{artwork_id}"
            }
            artworks.append(artwork)
        except Exception as e:
            continue
    
    return artworks

# ============================================
# MAIN
# ============================================

def main():
    print("="*80)
    print("🖼️  EXTRACTION SIMPLE - 100K ŒUVRES")
    print("="*80)
    print(f"📅 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objectif: {TARGET} œuvres")
    print(f"📦 Lots de {BATCH_SIZE} artistes")
    print(f"⏱️  Timeout: {TIMEOUT}s")
    print("="*80)
    
    # Charger progression
    checkpoint = load_checkpoint()
    artist_offset = checkpoint['artist_offset']
    processed_artists = set(checkpoint['processed_artists'])
    total_artworks = checkpoint['total_artworks']
    
    print(f"📊 Reprise: {total_artworks} œuvres déjà récupérées")
    print(f"📌 Offset artistes: {artist_offset}")
    print(f"🎨 Artistes déjà traités: {len(processed_artists)}")
    print("-"*80)
    
    batch_count = artist_offset // BATCH_SIZE + 1
    start_time = time.time()
    
    try:
        while total_artworks < TARGET:
            print(f"\n📦 Lot artistes #{batch_count} (offset {artist_offset})...")
            
            # 1. Récupérer des artistes
            artists_query = get_artists_simple(artist_offset)
            artists_results = fetch_with_retry(artists_query, "artistes")
            
            if not artists_results:
                print("   🏁 Plus d'artistes disponibles")
                break
            
            artists = process_artists_results(artists_results)
            
            if not artists:
                print("   🏁 Aucun artiste trouvé")
                artist_offset += BATCH_SIZE
                batch_count += 1
                continue
            
            print(f"   📋 {len(artists)} artistes trouvés")
            
            # 2. Traiter chaque artiste
            for artist_id, artist_name in artists:
                if total_artworks >= TARGET:
                    break
                
                if artist_id in processed_artists:
                    continue
                
                print(f"   🎨 {artist_name or 'Inconnu'}...")
                
                artworks_query = get_artworks_simple(artist_id)
                artworks_results = fetch_with_retry(artworks_query, f"œuvres de {artist_name}")
                
                if artworks_results:
                    artworks = process_artworks_results(artworks_results, artist_name or "Inconnu")
                    
                    if artworks:
                        saved = save_to_postgresql(artworks)
                        total_artworks += saved
                        print(f"      ✅ +{saved} œuvres (total: {total_artworks}/{TARGET})")
                
                # Marquer comme traité
                processed_artists.add(artist_id)
                
                # Sauvegarde périodique
                if len(processed_artists) % 10 == 0:
                    save_checkpoint(artist_offset, list(processed_artists), total_artworks)
                
                # Stats de progression
                elapsed = time.time() - start_time
                speed = total_artworks / elapsed if elapsed > 0 else 0
                print(f"      ⚡ {speed:.1f} œuvres/sec")
            
            artist_offset += BATCH_SIZE
            batch_count += 1
            
            # Checkpoint toutes les 5 itérations
            if batch_count % 5 == 0:
                save_checkpoint(artist_offset, list(processed_artists), total_artworks)
    
    except KeyboardInterrupt:
        print("\n⏸️ Interruption - Sauvegarde...")
        save_checkpoint(artist_offset, list(processed_artists), total_artworks)
    
    finally:
        elapsed = time.time() - start_time
        print("\n" + "="*80)
        print("📊 RÉSULTATS FINAUX")
        print("="*80)
        print(f"✅ Total œuvres: {total_artworks}")
        print(f"🎨 Artistes traités: {len(processed_artists)}")
        print(f"⏱️  Durée: {elapsed/60:.1f} minutes")
        print(f"⚡ Vitesse moyenne: {total_artworks/elapsed:.1f} œuvres/sec")
        print("="*80)

if __name__ == "__main__":
    main()
