"""
Pipeline Python — Newsletter Engagement Scoring
================================================
Connexion MySQL → manipulation Pandas → enrichissement API → scoring → écriture BDD

Auteur : Kamilia Malih
Cours  : MSc2 Manager Data Marketing — Algo & BDD 2026
"""

import os
import requests
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
from datetime import date

# ─── Chargement des variables d'environnement ────────────────────────────────
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "newsletter_scoring")


# ─── CONNEXION À LA BASE ──────────────────────────────────────────────────────

def get_connection():
    """Retourne une connexion MySQL active."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )


def fetch_dataframe(query: str) -> pd.DataFrame:
    """
    Exécute une requête SELECT et retourne le résultat sous forme de DataFrame.

    Paramètres
    ----------
    query : str
        Requête SQL SELECT à exécuter.

    Retourne
    --------
    pd.DataFrame
    """
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# ─── EXTRACTION DES DONNÉES D'ENGAGEMENT ─────────────────────────────────────

def load_engagement_data() -> pd.DataFrame:
    """Charge la vue d'engagement depuis MySQL."""
    query = """
        SELECT
            id_abonne,
            email,
            prenom,
            nom,
            ville,
            pays,
            segment_age,
            date_inscription,
            nb_envois_recus,
            nb_ouvertures,
            nb_clics,
            nb_desabonnements,
            taux_ouverture,
            taux_clic,
            derniere_ouverture
        FROM vue_engagement_abonnes
    """
    df = fetch_dataframe(query)
    print(f"[✓] {len(df)} abonnés chargés depuis la base.")
    return df


# ─── ENRICHISSEMENT VIA API EXTERNE (REST Countries) ─────────────────────────

def enrich_with_country_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit le DataFrame avec des données de pays via l'API REST Countries.
    Ajoute la région géographique et le continent pour chaque abonné.

    Paramètres
    ----------
    df : pd.DataFrame
        DataFrame contenant une colonne 'pays'.

    Retourne
    --------
    pd.DataFrame enrichi avec 'region' et 'subregion'.
    """
    pays_uniques = df["pays"].dropna().unique()
    mapping = {}

    # Correspondance nom français → code ou nom anglais pour l'API
    nom_en = {
        "France":  "France",
        "Espagne": "Spain",
        "UK":      "United Kingdom",
    }

    for pays in pays_uniques:
        nom_api = nom_en.get(pays, pays)
        try:
            resp = requests.get(
                f"https://restcountries.com/v3.1/name/{nom_api}",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()[0]
                mapping[pays] = {
                    "region":    data.get("region", "Inconnu"),
                    "subregion": data.get("subregion", "Inconnu"),
                }
            else:
                mapping[pays] = {"region": "Inconnu", "subregion": "Inconnu"}
        except Exception as e:
            print(f"[!] API indisponible pour '{pays}' : {e}")
            mapping[pays] = {"region": "Inconnu", "subregion": "Inconnu"}

    df["region"]    = df["pays"].map(lambda p: mapping.get(p, {}).get("region",    "Inconnu"))
    df["subregion"] = df["pays"].map(lambda p: mapping.get(p, {}).get("subregion", "Inconnu"))

    print(f"[✓] Enrichissement API terminé pour {len(pays_uniques)} pays.")
    return df


# ─── ALGORITHME DE SCORING D'ENGAGEMENT ──────────────────────────────────────

def compute_engagement_score(
    nb_ouvertures: int,
    nb_clics:      int,
    nb_envois:     int,
    nb_desabo:     int,
    date_inscription: str,
    derniere_ouverture
) -> float:
    """
    Calcule un score d'engagement composite entre 0 et 100.

    Formule
    -------
    - Taux ouverture (40 %)
    - Taux clic (60 %)
    - Bonus ancienneté (jusqu'à +10 pts pour > 2 ans)
    - Pénalité désabonnement (-15 pts si désabonné)
    - Pénalité inactivité (-10 pts si pas d'ouverture depuis > 90 jours)

    Paramètres
    ----------
    nb_ouvertures     : nombre d'emails ouverts
    nb_clics          : nombre de clics
    nb_envois         : nombre d'emails reçus
    nb_desabo         : 1 si désabonné, 0 sinon
    date_inscription  : date d'inscription (str ou date)
    derniere_ouverture: date de la dernière ouverture (peut être None)

    Retourne
    --------
    float : score entre 0 et 100
    """
    if nb_envois == 0:
        return 0.0

    tx_ouverture = 100.0 * nb_ouvertures / nb_envois
    tx_clic      = 100.0 * nb_clics      / nb_envois

    score = (tx_ouverture * 0.4) + (tx_clic * 0.6)

    # Bonus ancienneté
    if isinstance(date_inscription, str):
        date_inscription = pd.to_datetime(date_inscription).date()
    anciennete_jours = (date.today() - date_inscription).days
    if anciennete_jours > 730:
        score += 10
    elif anciennete_jours > 365:
        score += 5

    # Pénalité désabonnement
    if nb_desabo > 0:
        score -= 15

    # Pénalité inactivité récente (> 90 jours sans ouverture)
    if derniere_ouverture is not None:
        if isinstance(derniere_ouverture, str):
            derniere_ouverture = pd.to_datetime(derniere_ouverture).date()
        jours_sans_ouverture = (date.today() - derniere_ouverture).days
        if jours_sans_ouverture > 90:
            score -= 10

    return round(max(0.0, min(100.0, score)), 2)


def assign_segment(score: float) -> str:
    """Attribue un segment d'engagement selon le score calculé."""
    if score >= 60:
        return "Champion"
    elif score >= 35:
        return "Actif"
    elif score >= 15:
        return "Passif"
    else:
        return "Inactif"


def apply_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique le scoring et la segmentation à l'ensemble du DataFrame.

    Paramètres
    ----------
    df : pd.DataFrame avec colonnes d'engagement.

    Retourne
    --------
    pd.DataFrame avec colonnes 'score_engagement' et 'segment_engagement'.
    """
    df["score_engagement"] = df.apply(
        lambda row: compute_engagement_score(
            nb_ouvertures    = int(row["nb_ouvertures"]),
            nb_clics         = int(row["nb_clics"]),
            nb_envois        = int(row["nb_envois_recus"]),
            nb_desabo        = int(row["nb_desabonnements"]),
            date_inscription = row["date_inscription"],
            derniere_ouverture = row["derniere_ouverture"]
        ),
        axis=1
    )
    df["segment_engagement"] = df["score_engagement"].apply(assign_segment)

    print("[✓] Scoring d'engagement calculé.")
    print(df["segment_engagement"].value_counts().to_string())
    return df


# ─── ÉCRITURE DES RÉSULTATS DANS MYSQL ───────────────────────────────────────

def write_scoring_to_db(df: pd.DataFrame) -> None:
    """
    Crée (si nécessaire) la table 'scoring_engagement' et y insère les résultats.

    Paramètres
    ----------
    df : pd.DataFrame enrichi avec les colonnes de scoring.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Création de la table de résultats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scoring_engagement (
            id_abonne          INT          NOT NULL PRIMARY KEY,
            email              VARCHAR(150) NOT NULL,
            prenom             VARCHAR(80)  NOT NULL,
            nom                VARCHAR(80)  NOT NULL,
            ville              VARCHAR(100),
            pays               VARCHAR(60),
            region             VARCHAR(80),
            subregion          VARCHAR(80),
            segment_age        VARCHAR(20),
            date_inscription   DATE,
            nb_envois_recus    INT,
            nb_ouvertures      INT,
            nb_clics           INT,
            nb_desabonnements  INT,
            taux_ouverture     DECIMAL(5,2),
            taux_clic          DECIMAL(5,2),
            score_engagement   DECIMAL(5,2),
            segment_engagement VARCHAR(20),
            date_calcul        DATE,
            FOREIGN KEY (id_abonne) REFERENCES abonnes(id_abonne)
        )
    """)

    # Upsert des données
    upsert_query = """
        INSERT INTO scoring_engagement (
            id_abonne, email, prenom, nom, ville, pays, region, subregion,
            segment_age, date_inscription, nb_envois_recus, nb_ouvertures,
            nb_clics, nb_desabonnements, taux_ouverture, taux_clic,
            score_engagement, segment_engagement, date_calcul
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            score_engagement   = VALUES(score_engagement),
            segment_engagement = VALUES(segment_engagement),
            region             = VALUES(region),
            subregion          = VALUES(subregion),
            date_calcul        = VALUES(date_calcul)
    """

    rows = [
        (
            int(row["id_abonne"]),
            row["email"], row["prenom"], row["nom"],
            row.get("ville"), row.get("pays"),
            row.get("region", "Inconnu"), row.get("subregion", "Inconnu"),
            row.get("segment_age"),
            row["date_inscription"],
            int(row["nb_envois_recus"]),
            int(row["nb_ouvertures"]),
            int(row["nb_clics"]),
            int(row["nb_desabonnements"]),
            float(row["taux_ouverture"]),
            float(row["taux_clic"]),
            float(row["score_engagement"]),
            row["segment_engagement"],
            date.today(),
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany(upsert_query, rows)
    conn.commit()
    conn.close()
    print(f"[✓] {len(rows)} lignes écrites dans la table 'scoring_engagement'.")


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def run_pipeline() -> pd.DataFrame:
    """
    Orchestre l'ensemble du pipeline :
    1. Extraction depuis MySQL
    2. Enrichissement API pays
    3. Calcul du scoring d'engagement
    4. Écriture des résultats en base
    """
    print("\n=== Démarrage du pipeline Newsletter Scoring ===\n")

    df = load_engagement_data()
    df = enrich_with_country_data(df)
    df = apply_scoring(df)
    write_scoring_to_db(df)

    print("\n=== Pipeline terminé avec succès ===")
    return df


if __name__ == "__main__":
    df_final = run_pipeline()

    # Aperçu des résultats
    cols = ["prenom", "nom", "taux_ouverture", "taux_clic", "score_engagement", "segment_engagement", "region"]
    print("\n--- Aperçu des scores ---")
    print(df_final[cols].sort_values("score_engagement", ascending=False).to_string(index=False))
