#!/usr/bin/env python3
"""
Application Flask pour MuseumWiki
Affiche les œuvres d'art récupérées de Wikidata
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
import plotly.express as px
import plotly.utils
import json
from datetime import datetime

app = Flask(__name__)

# Chemin vers les données
DATA_PATH = os.getenv('DATA_PATH', '/app/data/artworks_latest.csv')

def load_artworks():
    """Charge les œuvres depuis le CSV"""
    try:
        df = pd.read_csv(DATA_PATH)
        print("✅ CSV chargé avec succès")
        print(f"📊 Colonnes trouvées : {list(df.columns)}")
        print(f"📊 Nombre de lignes : {len(df)}")
        
        # Nettoyer les données
        df = df.fillna('Inconnu')
        return df
    except Exception as e:
        print(f"❌ Erreur de chargement: {e}")
        return pd.DataFrame()



@app.route('/')
def index():
    """Page d'accueil avec galerie et pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    df = load_artworks()
    total = len(df)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    artworks_page = df.iloc[start:end]
    
    total_pages = (total + per_page - 1) // per_page
    
    stats = {
        'total': total,
        'with_image': len(df[df['image_url'] != '']),
        'without_image': total - len(df[df['image_url'] != '']),
        'last_update': datetime.now().strftime('%d/%m/%Y'),
        'page': page,
        'total_pages': total_pages,
        'per_page': per_page
    }
    
    return render_template('index.html', 
                         artworks=artworks_page.to_dict('records'),
                         stats=stats)




@app.route('/search')
def search():
    """Page de recherche avec pagination"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    df = load_artworks()
    
    if query:
        # Recherche dans titre, createur, lieu, genre
        mask = (
            df['titre'].str.contains(query, case=False, na=False) |
            df['createur'].str.contains(query, case=False, na=False) |
            df['lieu'].str.contains(query, case=False, na=False) |
            df['genre'].str.contains(query, case=False, na=False)
        )
        all_results = df[mask]
        total = len(all_results)
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        results_page = all_results.iloc[start:end]
        total_pages = (total + per_page - 1) // per_page
    else:
        results_page = pd.DataFrame()
        total = 0
        total_pages = 1
    
    return render_template('search.html', 
                         query=query,
                         results=results_page.to_dict('records'),
                         count=total,
                         page=page,
                         total_pages=total_pages)

@app.route('/api/artworks')
def api_artworks():
    """API JSON pour les œuvres"""
    df = load_artworks()
    limit = request.args.get('limit', 100, type=int)
    return jsonify(df.head(limit).to_dict('records'))

@app.route('/artist/<artist_name>')
def artist_works(artist_name):
    """Filtre par artiste"""
    df = load_artworks()
    artist_works = df[df['createur'].str.contains(artist_name, case=False, na=False)]
    return render_template('artist.html', 
                         artist=artist_name,
                         artworks=artist_works.to_dict('records'))

@app.route('/stats')
def statistics():
    """Page de statistiques"""
    df = load_artworks()
    
    # Top 10 artistes
    top_artists = df['createur'].value_counts().head(10).to_dict()
    
    # Répartition par genre
    genres = df['genre'].value_counts().head(10).to_dict()
    
    # Graphique avec Plotly
    fig = px.bar(x=list(top_artists.keys()), 
                 y=list(top_artists.values()),
                 title="Top 10 des artistes",
                 labels={'x': 'Artiste', 'y': "Nombre d'œuvres"})
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('stats.html',
                         top_artists=top_artists,
                         genres=genres,
                         graph_json=graph_json)

@app.route('/about')
def about():
    """Page à propos"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
