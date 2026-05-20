"""
Pipeline Python — Newsletter Engagement Scoring
"""

import os
import requests
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
from datetime import date

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "newsletter_scoring")

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def load_engagement_data():
    conn = get_connection()
    query = "SELECT * FROM vue_engagement_abonnes"
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"[✓] {len(df)} abonnés chargés depuis la base.")
    return df

def enrich_with_country_data(df):
    pays_uniques = df["pays"].dropna().unique()
    mapping = {}
    nom_en = {"France": "France", "Espagne": "Spain", "UK": "United Kingdom"}
    for pays in pays_uniques:
        nom_api = nom_en.get(pays, pays)
        try:
            resp = requests.get(f"https://restcountries.com/v3.1/name/{nom_api}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()[0]
                mapping[pays] = {"region": data.get("region", "Inconnu"), "subregion": data.get("subregion", "Inconnu")}
            else:
                mapping[pays] = {"region": "Inconnu", "subregion": "Inconnu"}
        except Exception as e:
            print(f"[!] API indisponible pour '{pays}' : {e}")
            mapping[pays] = {"region": "Inconnu", "subregion": "Inconnu"}
    df["region"] = df["pays"].map(lambda p: mapping.get(p, {}).get("region", "Inconnu"))
    df["subregion"] = df["pays"].map(lambda p: mapping.get(p, {}).get("subregion", "Inconnu"))
    print(f"[✓] Enrichissement API terminé pour {len(pays_uniques)} pays.")
    return df

def compute_engagement_score(nb_ouvertures, nb_clics, nb_envois, nb_desabo, date_inscription, derniere_ouverture):
    if nb_envois == 0:
        return 0.0
    tx_ouverture = 100.0 * nb_ouvertures / nb_envois
    tx_clic = 100.0 * nb_clics / nb_envois
    score = (tx_ouverture * 0.4) + (tx_clic * 0.6)
    if isinstance(date_inscription, str):
        date_inscription = pd.to_datetime(date_inscription).date()
    elif hasattr(date_inscription, 'date'):
        date_inscription = date_inscription.date()
    anciennete_jours = (date.today() - date_inscription).days
    if anciennete_jours > 730:
        score += 10
    elif anciennete_jours > 365:
        score += 5
    if nb_desabo > 0:
        score -= 15
    if derniere_ouverture is not None:
        if isinstance(derniere_ouverture, str):
            derniere_ouverture = pd.to_datetime(derniere_ouverture).date()
        elif hasattr(derniere_ouverture, 'date'):
            derniere_ouverture = derniere_ouverture.date()
        jours_sans_ouverture = (date.today() - derniere_ouverture).days
        if jours_sans_ouverture > 90:
            score -= 10
    return round(max(0.0, min(100.0, score)), 2)

def assign_segment(score):
    if score >= 60:
        return "Champion"
    elif score >= 35:
        return "Actif"
    elif score >= 15:
        return "Passif"
    else:
        return "Inactif"

def apply_scoring(df):
    df["score_engagement"] = df.apply(
        lambda row: compute_engagement_score(
            nb_ouvertures=int(row["nb_ouvertures"]),
            nb_clics=int(row["nb_clics"]),
            nb_envois=int(row["nb_envois_recus"]),
            nb_desabo=int(row["nb_desabonnements"]),
            date_inscription=row["date_inscription"],
            derniere_ouverture=row["derniere_ouverture"]
        ), axis=1
    )
    df["segment_engagement"] = df["score_engagement"].apply(assign_segment)
    print("[✓] Scoring calculé.")
    print(df["segment_engagement"].value_counts().to_string())
    return df

def write_scoring_to_db(df):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scoring_engagement (
            id_abonne INT NOT NULL PRIMARY KEY,
            email VARCHAR(150) NOT NULL,
            prenom VARCHAR(80) NOT NULL,
            nom VARCHAR(80) NOT NULL,
            ville VARCHAR(100),
            pays VARCHAR(60),
            region VARCHAR(80),
            subregion VARCHAR(80),
            segment_age VARCHAR(20),
            date_inscription DATE,
            nb_envois_recus INT,
            nb_ouvertures INT,
            nb_clics INT,
            nb_desabonnements INT,
            taux_ouverture DECIMAL(5,2),
            taux_clic DECIMAL(5,2),
            score_engagement DECIMAL(5,2),
            segment_engagement VARCHAR(20),
            date_calcul DATE,
            FOREIGN KEY (id_abonne) REFERENCES abonnes(id_abonne)
        )
    """)
    upsert_query = """
        INSERT INTO scoring_engagement (
            id_abonne, email, prenom, nom, ville, pays, region, subregion,
            segment_age, date_inscription, nb_envois_recus, nb_ouvertures,
            nb_clics, nb_desabonnements, taux_ouverture, taux_clic,
            score_engagement, segment_engagement, date_calcul
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            score_engagement=VALUES(score_engagement),
            segment_engagement=VALUES(segment_engagement),
            region=VALUES(region),
            subregion=VALUES(subregion),
            date_calcul=VALUES(date_calcul)
    """
    rows = [
        (int(row["id_abonne"]), row["email"], row["prenom"], row["nom"],
         row.get("ville"), row.get("pays"), row.get("region","Inconnu"), row.get("subregion","Inconnu"),
         row.get("segment_age"), row["date_inscription"], int(row["nb_envois_recus"]),
         int(row["nb_ouvertures"]), int(row["nb_clics"]), int(row["nb_desabonnements"]),
         float(row["taux_ouverture"]), float(row["taux_clic"]),
         float(row["score_engagement"]), row["segment_engagement"], date.today())
        for _, row in df.iterrows()
    ]
    cursor.executemany(upsert_query, rows)
    conn.commit()
    conn.close()
    print(f"[✓] {len(rows)} lignes écrites dans scoring_engagement.")

def run_pipeline():
    print("\n=== Démarrage du pipeline Newsletter Scoring ===\n")
    df = load_engagement_data()
    df = enrich_with_country_data(df)
    df = apply_scoring(df)
    write_scoring_to_db(df)
    print("\n=== Pipeline terminé avec succès ===")
    return df

if __name__ == "__main__":
    df_final = run_pipeline()
    cols = ["prenom", "nom", "taux_ouverture", "taux_clic", "score_engagement", "segment_engagement"]
    print(df_final[cols].sort_values("score_engagement", ascending=False).to_string(index=False))
