"""
GlowShop Analytics — Pipeline Python
  1. Connexion à MySQL et chargement des données
  2. Enrichissement via l'API REST Countries
  3. Algorithme RFM (Recency, Frequency, Monetary)
  4. Écriture des résultats dans la table rfm_scores
"""

import os
import time
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────

DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASS = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "glowshop_db")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


# ─── Connexion ────────────────────────────────────────────────────────────────

def get_engine():
    engine = create_engine(DB_URL, echo=False)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[OK] Connexion MySQL réussie")
    return engine


# ─── Chargement des données ───────────────────────────────────────────────────

def load_data(engine):
    """Charge les tables customers et orders depuis MySQL."""
    customers = pd.read_sql("SELECT * FROM customers", engine)
    orders    = pd.read_sql(
        "SELECT * FROM orders WHERE statut != 'annulee'", engine
    )
    print(f"[OK] {len(customers)} clients | {len(orders)} commandes chargés")
    return customers, orders


# ─── Enrichissement API REST Countries ───────────────────────────────────────

def fetch_country_info(alpha2_code: str) -> dict:
    """Appelle l'API REST Countries pour enrichir les données géographiques."""
    url = f"https://restcountries.com/v3.1/alpha/{alpha2_code}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()[0]
        return {
            "region":      data.get("region", ""),
            "sous_region": data.get("subregion", ""),
        }
    except Exception as e:
        print(f"  [WARN] API {alpha2_code} : {e}")
        return {"region": "", "sous_region": ""}


def enrich_customers(engine, df_customers: pd.DataFrame) -> pd.DataFrame:
    """Enrichit les clients avec les infos pays (région, sous-région)."""
    pays_codes = df_customers["pays_code"].unique()
    country_map = {}

    print(f"[API] Enrichissement pour {len(pays_codes)} pays ...")
    for code in pays_codes:
        country_map[code] = fetch_country_info(code)
        time.sleep(0.3)  # respect rate limit

    df_customers = df_customers.copy()
    df_customers["pays_region"]      = df_customers["pays_code"].map(
        lambda c: country_map.get(c, {}).get("region", "")
    )
    df_customers["pays_sous_region"] = df_customers["pays_code"].map(
        lambda c: country_map.get(c, {}).get("sous_region", "")
    )

    # Mise à jour dans MySQL
    with engine.begin() as conn:
        for _, row in df_customers.iterrows():
            conn.execute(text("""
                UPDATE customers
                   SET pays_region = :region, pays_sous_region = :sous_region
                 WHERE id = :id
            """), {
                "region":      row["pays_region"],
                "sous_region": row["pays_sous_region"],
                "id":          int(row["id"]),
            })

    print(f"[OK] Enrichissement pays terminé")
    return df_customers


# ─── Algorithme RFM ───────────────────────────────────────────────────────────

def calculate_rfm(df_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les scores RFM pour chaque client :
      R (Recency)   : jours depuis la dernière commande   → score 1–5
      F (Frequency) : nombre de commandes                 → score 1–5
      M (Monetary)  : montant total dépensé               → score 1–5
    Segmentation basée sur R+F :
      Champions, Clients Fidèles, Nouveaux Clients, À Risque, Perdus, Potentiels
    """
    df_orders["date_commande"] = pd.to_datetime(df_orders["date_commande"])
    reference_date = df_orders["date_commande"].max() + pd.Timedelta(days=1)

    rfm = df_orders.groupby("customer_id").agg(
        recency_days=("date_commande", lambda x: (reference_date - x.max()).days),
        frequency=("id", "count"),
        monetary=("montant_total", "sum"),
    ).reset_index()

    rfm["monetary"] = rfm["monetary"].round(2)

    # Scores 1–5 via quintiles
    rfm["r_score"] = pd.qcut(rfm["recency_days"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype(int)

    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    rfm["segment"] = rfm.apply(_assign_segment, axis=1)

    print(f"[OK] RFM calculé pour {len(rfm)} clients")
    print(rfm["segment"].value_counts().to_string())
    return rfm


def _assign_segment(row) -> str:
    """Retourne le segment marketing en fonction du score R et F."""
    r, f = row["r_score"], row["f_score"]
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Clients Fidèles"
    if r >= 4 and f <= 2:
        return "Nouveaux Clients"
    if r <= 2 and f >= 3:
        return "À Risque"
    if r <= 2 and f <= 2:
        return "Perdus"
    return "Potentiels"


# ─── Écriture des résultats ───────────────────────────────────────────────────

def write_rfm_to_db(engine, df_rfm: pd.DataFrame):
    """Écrit les scores RFM dans la table rfm_scores (upsert)."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE rfm_scores"))

    df_rfm.rename(columns={"customer_id": "customer_id"}, inplace=True)
    df_rfm[["customer_id","recency_days","frequency","monetary",
            "r_score","f_score","m_score","rfm_score","segment"]].to_sql(
        "rfm_scores",
        engine,
        if_exists="append",
        index=False,
    )
    print(f"[OK] {len(df_rfm)} scores RFM écrits dans rfm_scores")


# ─── Point d'entrée ───────────────────────────────────────────────────────────

def run_pipeline():
    print("=" * 50)
    print("  GlowShop Analytics — Pipeline")
    print("=" * 50)

    engine                  = get_engine()
    df_customers, df_orders = load_data(engine)
    df_customers            = enrich_customers(engine, df_customers)
    df_rfm                  = calculate_rfm(df_orders)
    write_rfm_to_db(engine, df_rfm)

    print("\n[DONE] Pipeline terminé avec succès.")
    print("       Lancez maintenant : python dashboard.py")


if __name__ == "__main__":
    run_pipeline()
