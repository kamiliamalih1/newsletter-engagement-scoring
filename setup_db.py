"""
GlowShop Analytics — Setup complet de la base de données
Lance ce script UNE SEULE FOIS pour tout créer et insérer les données.
Usage : python setup_db.py
"""

import os
import sys
import pymysql
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "root")
PASS = os.getenv("MYSQL_PASSWORD", "")
DB   = os.getenv("MYSQL_DATABASE", "glowshop_db")

# ─── Connexion sans sélectionner de base (pour pouvoir la créer) ──────────────
print("Connexion à MySQL...")
try:
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASS,
                           charset="utf8mb4", autocommit=True)
    print("  OK")
except Exception as e:
    print(f"  ERREUR : {e}")
    print("\nVérifie ton mot de passe dans le fichier .env (MYSQL_PASSWORD=...)")
    sys.exit(1)

cursor = conn.cursor()

# ─── Création de la base ──────────────────────────────────────────────────────
print("\nCréation de la base glowshop_db...")
cursor.execute("CREATE DATABASE IF NOT EXISTS glowshop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cursor.execute("USE glowshop_db")
print("  OK")

# ─── Création des tables ──────────────────────────────────────────────────────
print("\nCréation des tables...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id          INT           PRIMARY KEY AUTO_INCREMENT,
    nom         VARCHAR(100)  NOT NULL,
    description TEXT,
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id          INT             PRIMARY KEY AUTO_INCREMENT,
    nom         VARCHAR(200)    NOT NULL,
    description TEXT,
    category_id INT             NOT NULL,
    prix        DECIMAL(10,2)   NOT NULL,
    stock       INT             DEFAULT 0,
    actif       BOOLEAN         DEFAULT TRUE,
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES categories(id)
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id                INT          PRIMARY KEY AUTO_INCREMENT,
    prenom            VARCHAR(100) NOT NULL,
    nom               VARCHAR(100) NOT NULL,
    email             VARCHAR(200) NOT NULL UNIQUE,
    pays_code         CHAR(2)      NOT NULL,
    ville             VARCHAR(100),
    date_inscription  DATE         NOT NULL,
    telephone         VARCHAR(30),
    pays_region       VARCHAR(100),
    pays_sous_region  VARCHAR(100),
    created_at        DATETIME     DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id                INT          PRIMARY KEY AUTO_INCREMENT,
    customer_id       INT          NOT NULL,
    date_commande     DATETIME     NOT NULL,
    statut            ENUM('en_attente','confirmee','expediee','livree','annulee') DEFAULT 'en_attente',
    montant_total     DECIMAL(10,2),
    adresse_livraison VARCHAR(200),
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id            INT           PRIMARY KEY AUTO_INCREMENT,
    order_id      INT           NOT NULL,
    product_id    INT           NOT NULL,
    quantite      INT           NOT NULL DEFAULT 1,
    prix_unitaire DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_item_order   FOREIGN KEY (order_id)   REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT chk_quantite    CHECK (quantite > 0)
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS rfm_scores (
    id           INT           PRIMARY KEY AUTO_INCREMENT,
    customer_id  INT           NOT NULL UNIQUE,
    recency_days INT           NOT NULL,
    frequency    INT           NOT NULL,
    monetary     DECIMAL(10,2) NOT NULL,
    r_score      INT           NOT NULL,
    f_score      INT           NOT NULL,
    m_score      INT           NOT NULL,
    rfm_score    INT           NOT NULL,
    segment      VARCHAR(50)   NOT NULL,
    computed_at  DATETIME      DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rfm_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
)""")
print("  6 tables OK")

# ─── Vues ────────────────────────────────────────────────────────────────────
print("\nCréation des vues...")

cursor.execute("""
CREATE OR REPLACE VIEW v_ca_mensuel AS
    SELECT DATE_FORMAT(date_commande, '%Y-%m') AS mois,
           COUNT(*)                            AS nb_commandes,
           ROUND(SUM(montant_total), 2)        AS ca_total,
           ROUND(AVG(montant_total), 2)        AS panier_moyen
    FROM orders WHERE statut != 'annulee'
    GROUP BY DATE_FORMAT(date_commande, '%Y-%m')
    ORDER BY mois
""")

cursor.execute("""
CREATE OR REPLACE VIEW v_top_produits AS
    SELECT p.id, p.nom, c.nom AS categorie,
           SUM(oi.quantite) AS unites_vendues,
           ROUND(SUM(oi.quantite * oi.prix_unitaire), 2) AS ca_produit
    FROM order_items oi
    JOIN products p   ON p.id = oi.product_id
    JOIN categories c ON c.id = p.category_id
    JOIN orders o     ON o.id = oi.order_id
    WHERE o.statut != 'annulee'
    GROUP BY p.id, p.nom, c.nom
    ORDER BY unites_vendues DESC
""")

cursor.execute("""
CREATE OR REPLACE VIEW v_clients_actifs AS
    SELECT cu.id, CONCAT(cu.prenom,' ',cu.nom) AS client,
           cu.email, cu.pays_code,
           COUNT(DISTINCT o.id)           AS nb_commandes,
           ROUND(SUM(o.montant_total),2)  AS ca_total,
           MAX(o.date_commande)           AS derniere_commande
    FROM customers cu
    JOIN orders o ON o.customer_id = cu.id
    WHERE o.statut != 'annulee'
    GROUP BY cu.id, cu.prenom, cu.nom, cu.email, cu.pays_code
""")
print("  3 vues OK")

# ─── Fonction ────────────────────────────────────────────────────────────────
print("\nCréation de la fonction fn_niveau_client...")
cursor.execute("DROP FUNCTION IF EXISTS fn_niveau_client")
cursor.execute("""
CREATE FUNCTION fn_niveau_client(p_customer_id INT)
RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total_ca DECIMAL(10,2);
    DECLARE niveau   VARCHAR(20);
    SELECT COALESCE(SUM(montant_total), 0) INTO total_ca
    FROM orders WHERE customer_id = p_customer_id AND statut != 'annulee';
    IF total_ca >= 500 THEN SET niveau = 'VIP';
    ELSEIF total_ca >= 200 THEN SET niveau = 'Fidele';
    ELSEIF total_ca >= 50  THEN SET niveau = 'Regulier';
    ELSE SET niveau = 'Nouveau';
    END IF;
    RETURN niveau;
END
""")
print("  OK")

# ─── Procédure ───────────────────────────────────────────────────────────────
print("\nCréation de la procédure sp_update_stock...")
cursor.execute("DROP PROCEDURE IF EXISTS sp_update_stock")
cursor.execute("""
CREATE PROCEDURE sp_update_stock(IN p_order_id INT)
BEGIN
    UPDATE products p
    JOIN order_items oi ON oi.product_id = p.id
    SET p.stock = p.stock - oi.quantite
    WHERE oi.order_id = p_order_id;
END
""")
print("  OK")

# ─── Insertion des données ────────────────────────────────────────────────────
# Vérifie si les données existent déjà (on regarde customers, pas categories)
cursor.execute("SELECT COUNT(*) FROM customers")
if cursor.fetchone()[0] > 0:
    print("\nDonnées déjà présentes — insertion ignorée.")
else:
    # Vide toutes les tables avant de réinsérer
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    for t in ["order_items","orders","rfm_scores","customers","products","categories"]:
        cursor.execute(f"TRUNCATE TABLE {t}")
    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    print("\nInsertion des données...")
    sql_path = os.path.join(os.path.dirname(__file__), "sql", "02_insert_data.sql")
    with open(sql_path, encoding="utf-8") as f:
        content = f.read()

    # Sépare les blocs INSERT
    statements = [s.strip() for s in content.split(";") if s.strip() and not s.strip().startswith("--")]
    for stmt in statements:
        if stmt:
            cursor.execute(stmt)
    print("  Données insérées OK")

# ─── Résumé ───────────────────────────────────────────────────────────────────
print("\n" + "="*45)
print("  Setup terminé avec succès !")
print("="*45)
for table in ["categories", "products", "customers", "orders", "order_items"]:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    n = cursor.fetchone()[0]
    print(f"  {table:15s} : {n} lignes")

print("\nProchaine étape :")
print("  python pipeline.py")

cursor.close()
conn.close()
