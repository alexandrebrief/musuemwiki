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
DATA_PATH = os.getenv('DATA_PATH', '../data/artworks_latest.csv')

def load_artworks():
    """Charge les œuvres depuis le CSV"""
    try:
        df = pd.read_csv(DATA_PATH)
        # Nettoyer les données
        df = df.fillna('Inconnu')
        return df
    except Exception as e:
        print(f"Erreur de chargement: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    """Page d'accueil avec galerie"""
    df = load_artworks()
    total = len(df)
    with_image = len(df[df['image_url'] != ''])
    
    stats = {
        'total': total,
        'with_image': with_image,
        'without_image': total - with_image,
        'last_update': datetime.now().strftime('%d/%m/%Y')
    }
    
    return render_template('index.html', 
                         artworks=df.head(20).to_dict('records'),
                         stats=stats)

@app.route('/search')
def search():
    """Page de recherche"""
    query = request.args.get('q', '')
    df = load_artworks()
    
    if query:
        # Recherche dans titre, createur, lieu, genre
        mask = (
            df['titre'].str.contains(query, case=False, na=False) |
            df['createur'].str.contains(query, case=False, na=False) |
            df['lieu'].str.contains(query, case=False, na=False) |
            df['genre'].str.contains(query, case=False, na=False)
        )
        results = df[mask]
    else:
        results = pd.DataFrame()
    
    return render_template('search.html', 
                         query=query,
                         results=results.to_dict('records'),
                         count=len(results))


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
