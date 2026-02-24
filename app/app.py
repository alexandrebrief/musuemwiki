#!/usr/bin/env python3
"""
Application Flask pour MuseumWiki
Version complète avec filtres dynamiques et recherche
"""

# ============================================
# 1. IMPORTS
# ============================================
from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
import plotly.express as px
import plotly.utils
import json
from datetime import datetime

# ============================================
# 2. CONFIGURATION GLOBALE
# ============================================
app = Flask(__name__)

# Cache global pour le DataFrame
_df_cache = None

# ============================================
# 3. DÉTERMINATION DU CHEMIN DES DONNÉES
# ============================================
if os.path.exists('/app/data/artworks_latest.csv'):
    DATA_PATH = '/app/data/artworks_latest.csv'   # Dans Docker
else:
    DATA_PATH = '../data/artworks_latest.csv'     # En local

# ============================================
# 4. FONCTIONS UTILITAIRES
# ============================================

def load_artworks():
    """
    Charge les œuvres depuis le CSV avec mise en cache.
    """
    global _df_cache
    if _df_cache is None:
        try:
            _df_cache = pd.read_csv(DATA_PATH)
            _df_cache = _df_cache.fillna('Inconnu')
            print("✅ CSV chargé en cache")
        except Exception as e:
            print(f"❌ Erreur de chargement: {e}")
            return pd.DataFrame()
    return _df_cache.copy()  # Retourner une copie pour éviter les problèmes d'index

def get_filtered_df(query, artists, museums, movements):
    """
    Retourne un DataFrame filtré selon la recherche et les filtres sélectionnés
    """
    df = load_artworks()
    filtered_df = df.copy()
    
    # Filtre de recherche textuelle
    if query:
        mask = (
            filtered_df['titre'].str.contains(query, case=False, na=False) |
            filtered_df['createur'].str.contains(query, case=False, na=False) |
            filtered_df['lieu'].str.contains(query, case=False, na=False) |
            filtered_df['genre'].str.contains(query, case=False, na=False)
        )
        filtered_df = filtered_df[mask].copy()
    
    # Filtre par artiste
    if artists:
        mask_artist = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for artist in artists:
            mask_artist |= filtered_df['createur'].str.contains(artist, case=False, na=False)
        filtered_df = filtered_df[mask_artist].copy()
    
    # Filtre par musée
    if museums:
        mask_museum = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for museum in museums:
            mask_museum |= filtered_df['lieu'].str.contains(museum, case=False, na=False)
        filtered_df = filtered_df[mask_museum].copy()
    
    # Filtre par mouvement
    if movements:
        mask_movement = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for movement in movements:
            mask_movement |= filtered_df['mouvement'].str.contains(movement, case=False, na=False)
        filtered_df = filtered_df[mask_movement].copy()
    
    return filtered_df

# ============================================
# 5. ROUTE PRINCIPALE
# ============================================

@app.route('/')
def index():
    """Page d'accueil avec recherche, filtres et tris"""
    # Récupération des paramètres
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    artists = request.args.getlist('artist')
    museums = request.args.getlist('museum')
    movements = request.args.getlist('movement')
    sort = request.args.get('sort', 'relevance')
    
    # Chargement des données
    df = load_artworks()
    filtered_df = df.copy()
    
    # Filtre de recherche textuelle
    if query:
        mask = (
            filtered_df['titre'].str.contains(query, case=False, na=False) |
            filtered_df['createur'].str.contains(query, case=False, na=False) |
            filtered_df['lieu'].str.contains(query, case=False, na=False) |
            filtered_df['genre'].str.contains(query, case=False, na=False)
        )
        filtered_df = filtered_df[mask].copy()
    
    # Application des filtres
    if artists:
        mask_artist = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for artist in artists:
            mask_artist |= filtered_df['createur'].str.contains(artist, case=False, na=False)
        filtered_df = filtered_df[mask_artist].copy()
    
    if museums:
        mask_museum = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for museum in museums:
            mask_museum |= filtered_df['lieu'].str.contains(museum, case=False, na=False)
        filtered_df = filtered_df[mask_museum].copy()
    
    if movements:
        mask_movement = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for movement in movements:
            mask_movement |= filtered_df['mouvement'].str.contains(movement, case=False, na=False)
        filtered_df = filtered_df[mask_movement].copy()
    
    # Tri
    if sort == 'date_asc':
        filtered_df = filtered_df.sort_values('date', na_position='last')
    elif sort == 'date_desc':
        filtered_df = filtered_df.sort_values('date', ascending=False, na_position='last')
    elif sort == 'title_asc':
        filtered_df = filtered_df.sort_values('titre')
    elif sort == 'title_desc':
        filtered_df = filtered_df.sort_values('titre', ascending=False)
    elif sort == 'artist_asc':
        filtered_df = filtered_df.sort_values('createur')
    elif sort == 'artist_desc':
        filtered_df = filtered_df.sort_values('createur', ascending=False)
    # relevance = pas de tri
    
    # Pagination
    total = len(filtered_df)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    results_page = filtered_df.iloc[start:end]
    
    return render_template('index.html', 
                         query=query,
                         results=results_page.to_dict('records'),
                         count=total,
                         page=page,
                         total_pages=total_pages,
                         artists=artists,
                         museums=museums,
                         movements=movements,
                         sort=sort)

# ============================================
# 6. API POUR LES FILTRES DYNAMIQUES
# ============================================

@app.route('/api/artists')
def api_artists():
    """Retourne la liste des artistes avec leur nombre d'œuvres, filtrée par la recherche"""
    query = request.args.get('q', '')
    
    # Utiliser la fonction de filtrage
    filtered_df = get_filtered_df(query, [], [], [])
    
    if len(filtered_df) > 0:
        artists = filtered_df['createur'].value_counts().head(30).reset_index()
        artists.columns = ['name', 'count']
        # Filtrer les valeurs vides ou "Inconnu"
        artists = artists[artists['name'] != 'Inconnu']
    else:
        artists = pd.DataFrame(columns=['name', 'count'])
    
    return jsonify(artists.to_dict('records'))

@app.route('/api/museums')
def api_museums():
    """Retourne la liste des musées avec leur nombre d'œuvres, filtrée par la recherche"""
    query = request.args.get('q', '')
    
    # Utiliser la fonction de filtrage
    filtered_df = get_filtered_df(query, [], [], [])
    
    if len(filtered_df) > 0:
        museums = filtered_df['lieu'].value_counts().head(30).reset_index()
        museums.columns = ['name', 'count']
        # Filtrer les valeurs vides ou "Inconnu"
        museums = museums[museums['name'] != 'Inconnu']
    else:
        museums = pd.DataFrame(columns=['name', 'count'])
    
    return jsonify(museums.to_dict('records'))

@app.route('/api/movements')
def api_movements():
    """Retourne la liste des mouvements avec leur nombre d'œuvres, filtrée par la recherche"""
    query = request.args.get('q', '')
    
    # Utiliser la fonction de filtrage
    filtered_df = get_filtered_df(query, [], [], [])
    
    if len(filtered_df) > 0:
        movements = filtered_df['mouvement'].value_counts().head(30).reset_index()
        movements.columns = ['name', 'count']
        # Filtrer les valeurs vides ou "Inconnu"
        movements = movements[movements['name'] != 'Inconnu']
        movements = movements[movements['name'] != 'nan']
    else:
        movements = pd.DataFrame(columns=['name', 'count'])
    
    return jsonify(movements.to_dict('records'))

# ============================================
# 7. ROUTES PAGES STATIQUES
# ============================================

@app.route('/stats')
def statistics():
    """Page de statistiques"""
    df = load_artworks()
    
    # Top 10 artistes
    top_artists = df['createur'].value_counts().head(10).to_dict()
    
    # Répartition par genre
    genres = df['genre'].value_counts().head(10).to_dict()
    
    return render_template('stats.html',
                         top_artists=top_artists,
                         genres=genres)

@app.route('/about')
def about():
    """Page à propos"""
    return render_template('about.html')

@app.route('/oeuvre/<string:oeuvre_id>')
def oeuvre_detail(oeuvre_id):
    """Page détaillée d'une œuvre"""
    df = load_artworks()
    oeuvre_data = df[df['id'] == oeuvre_id].to_dict('records')
    
    if oeuvre_data:
        return render_template('detail.html', oeuvre=oeuvre_data[0])
    else:
        return "Œuvre non trouvée", 404

@app.route('/api/suggestions')
def suggestions():
    """API pour l'autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    df = load_artworks()
    
    mask_artistes = df['createur'].str.contains(query, case=False, na=False)
    mask_oeuvres = df['titre'].str.contains(query, case=False, na=False)
    mask_musees = df['lieu'].str.contains(query, case=False, na=False)
    
    suggestions_list = []
    
    artistes = df[mask_artistes]['createur'].drop_duplicates().head(3).tolist()
    for artiste in artistes:
        suggestions_list.append({'texte': artiste, 'categorie': 'artiste'})
    
    oeuvres = df[mask_oeuvres]['titre'].drop_duplicates().head(3).tolist()
    for oeuvre in oeuvres:
        suggestions_list.append({'texte': oeuvre, 'categorie': 'œuvre'})
    
    musees = df[mask_musees]['lieu'].drop_duplicates().head(3).tolist()
    for musee in musees:
        suggestions_list.append({'texte': musee, 'categorie': 'musée'})
    
    return jsonify(suggestions_list[:9])

# ============================================
# 8. LANCEMENT
# ============================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
