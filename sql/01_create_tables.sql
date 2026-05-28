-- ============================================================
-- GlowShop Analytics — Création de la base de données
-- MSc2 Manager Data Marketing — Algo & BDD 2026
-- ============================================================

CREATE DATABASE IF NOT EXISTS glowshop_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE glowshop_db;

-- ─── Table 1 : catégories de produits ────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id          INT           PRIMARY KEY AUTO_INCREMENT,
    nom         VARCHAR(100)  NOT NULL,
    description TEXT,
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table 2 : produits ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id          INT             PRIMARY KEY AUTO_INCREMENT,
    nom         VARCHAR(200)    NOT NULL,
    description TEXT,
    category_id INT             NOT NULL,
    prix        DECIMAL(10,2)   NOT NULL,
    stock       INT             DEFAULT 0,
    actif       BOOLEAN         DEFAULT TRUE,
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id)
        REFERENCES categories(id) ON DELETE RESTRICT
);

-- ─── Table 3 : clients ───────────────────────────────────────
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
);

-- ─── Table 4 : commandes ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id                  INT          PRIMARY KEY AUTO_INCREMENT,
    customer_id         INT          NOT NULL,
    date_commande       DATETIME     NOT NULL,
    statut              ENUM('en_attente','confirmee','expediee','livree','annulee')
                                     DEFAULT 'en_attente',
    montant_total       DECIMAL(10,2),
    adresse_livraison   VARCHAR(200),
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE RESTRICT
);

-- ─── Table 5 : lignes de commande (many-to-many orders ↔ products) ───
CREATE TABLE IF NOT EXISTS order_items (
    id              INT           PRIMARY KEY AUTO_INCREMENT,
    order_id        INT           NOT NULL,
    product_id      INT           NOT NULL,
    quantite        INT           NOT NULL DEFAULT 1,
    prix_unitaire   DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_item_order   FOREIGN KEY (order_id)
        REFERENCES orders(id)   ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id)
        REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT chk_quantite CHECK (quantite > 0)
);

-- ─── Table 6 : scores RFM (remplie par le pipeline Python) ───
CREATE TABLE IF NOT EXISTS rfm_scores (
    id              INT           PRIMARY KEY AUTO_INCREMENT,
    customer_id     INT           NOT NULL UNIQUE,
    recency_days    INT           NOT NULL,
    frequency       INT           NOT NULL,
    monetary        DECIMAL(10,2) NOT NULL,
    r_score         INT           NOT NULL,
    f_score         INT           NOT NULL,
    m_score         INT           NOT NULL,
    rfm_score       INT           NOT NULL,
    segment         VARCHAR(50)   NOT NULL,
    computed_at     DATETIME      DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rfm_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════════════
-- VUES
-- ═══════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_ca_mensuel AS
    SELECT
        DATE_FORMAT(date_commande, '%Y-%m') AS mois,
        COUNT(*)                            AS nb_commandes,
        ROUND(SUM(montant_total), 2)        AS ca_total,
        ROUND(AVG(montant_total), 2)        AS panier_moyen
    FROM orders
    WHERE statut != 'annulee'
    GROUP BY DATE_FORMAT(date_commande, '%Y-%m')
    ORDER BY mois;

CREATE OR REPLACE VIEW v_top_produits AS
    SELECT
        p.id,
        p.nom,
        c.nom            AS categorie,
        SUM(oi.quantite) AS unites_vendues,
        ROUND(SUM(oi.quantite * oi.prix_unitaire), 2) AS ca_produit
    FROM order_items oi
    JOIN products p ON p.id = oi.product_id
    JOIN categories c ON c.id = p.category_id
    JOIN orders o ON o.id = oi.order_id
    WHERE o.statut != 'annulee'
    GROUP BY p.id, p.nom, c.nom
    ORDER BY unites_vendues DESC;

CREATE OR REPLACE VIEW v_clients_actifs AS
    SELECT
        cu.id,
        CONCAT(cu.prenom, ' ', cu.nom) AS client,
        cu.email,
        cu.pays_code,
        COUNT(DISTINCT o.id)           AS nb_commandes,
        ROUND(SUM(o.montant_total), 2) AS ca_total,
        MAX(o.date_commande)           AS derniere_commande
    FROM customers cu
    JOIN orders o ON o.customer_id = cu.id
    WHERE o.statut != 'annulee'
    GROUP BY cu.id, cu.prenom, cu.nom, cu.email, cu.pays_code;

-- ═══════════════════════════════════════════════════════════════
-- FONCTION : calcul du niveau de dépense d'un client
-- ═══════════════════════════════════════════════════════════════

DELIMITER $$

DROP FUNCTION IF EXISTS fn_niveau_client;
CREATE FUNCTION fn_niveau_client(p_customer_id INT)
RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total_ca DECIMAL(10,2);
    DECLARE niveau   VARCHAR(20);

    SELECT COALESCE(SUM(montant_total), 0)
    INTO   total_ca
    FROM   orders
    WHERE  customer_id = p_customer_id
      AND  statut != 'annulee';

    IF total_ca >= 500 THEN
        SET niveau = 'VIP';
    ELSEIF total_ca >= 200 THEN
        SET niveau = 'Fidèle';
    ELSEIF total_ca >= 50 THEN
        SET niveau = 'Régulier';
    ELSE
        SET niveau = 'Nouveau';
    END IF;

    RETURN niveau;
END$$

-- ═══════════════════════════════════════════════════════════════
-- PROCÉDURE : mise à jour du stock après livraison
-- ═══════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_update_stock;
CREATE PROCEDURE sp_update_stock(IN p_order_id INT)
BEGIN
    UPDATE products p
    JOIN order_items oi ON oi.product_id = p.id
    SET p.stock = p.stock - oi.quantite
    WHERE oi.order_id = p_order_id;
END$$

DELIMITER ;
