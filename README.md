# Newsletter Engagement Scoring

**MSc2 Manager Data Marketing — Algo & Bases de Données 2026**  
Auteur : Kamilia Malih

---

# 💄 GlowShop Analytics

**Projet Final — Algo & Bases de Données**
MSc2 Manager Data Marketing · INSEEC Lyon · 2026
Auteur : Kamilia Malih

## Problématique métier

GlowShop est une boutique e-commerce de cosmétiques. L'objectif est d'analyser les performances commerciales et de segmenter les clients avec l'algorithme RFM (Recency, Frequency, Monetary) pour adapter la stratégie marketing.

## Schéma de la base de données

6 tables : categories, products, customers, orders, order_items, rfm_scores

## Lancement

pip install -r requirements.txt
cp .env.example .env  # remplir avec identifiants MySQL
python generate_data.py
python setup_db.py
python pipeline.py
python dashboard.py