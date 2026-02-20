# 🖼️ MuseumWiki

Base de données d'œuvres d'art provenant de Wikidata, mise à jour automatiquement chaque semaine.

## 🚀 Fonctionnalités

- Récupération automatique des œuvres d'art depuis Wikidata
- Mise à jour hebdomadaire via GitHub Actions
- Données disponibles en CSV et JSON
- Application web pour visualiser les œuvres

## 📦 Structure du projet
museumwiki/
├── .github/workflows/ # Configuration GitHub Actions
├── app/ # Application web
├── scripts/ # Scripts de récupération des données
├── data/ # Données téléchargées
└── tests/ # Tests unitaires


## 🛠️ Installation

```bash
# Cloner le dépôt
git clone https://github.com/alexandrebrief/musuemwiki.git
cd musuemwiki

# Installer les dépendances Python
cd scripts
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Exécuter le script
python fetch_wikidata.py
