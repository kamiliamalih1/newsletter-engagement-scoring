-- ============================================================
-- GlowShop Analytics — Requêtes SQL d'analyse
-- MSc2 Manager Data Marketing — Algo & BDD 2026
-- ============================================================

USE glowshop_db;

-- ─── Requête 1 : Top 10 clients par chiffre d'affaires ───────
-- WHERE, GROUP BY, ORDER BY, LIMIT
SELECT
    cu.id,
    CONCAT(cu.prenom, ' ', cu.nom)  AS client,
    cu.email,
    cu.pays_code                     AS pays,
    COUNT(o.id)                      AS nb_commandes,
    ROUND(SUM(o.montant_total), 2)   AS ca_total,
    fn_niveau_client(cu.id)          AS niveau
FROM customers cu
JOIN orders o ON o.customer_id = cu.id
WHERE o.statut != 'annulee'
GROUP BY cu.id, cu.prenom, cu.nom, cu.email, cu.pays_code
ORDER BY ca_total DESC
LIMIT 10;

-- ─── Requête 2 : Chiffre d'affaires mensuel ≥ 200 € ─────────
-- GROUP BY, HAVING, ORDER BY
SELECT
    DATE_FORMAT(date_commande, '%Y-%m') AS mois,
    COUNT(*)                             AS nb_commandes,
    ROUND(SUM(montant_total), 2)         AS ca_mensuel,
    ROUND(AVG(montant_total), 2)         AS panier_moyen
FROM orders
WHERE statut != 'annulee'
GROUP BY DATE_FORMAT(date_commande, '%Y-%m')
HAVING ca_mensuel >= 200
ORDER BY mois DESC;

-- ─── Requête 3 : Produits les plus vendus par catégorie ──────
-- JOIN 3 tables, GROUP BY, ORDER BY
SELECT
    c.nom                                        AS categorie,
    p.nom                                        AS produit,
    SUM(oi.quantite)                             AS unites_vendues,
    ROUND(SUM(oi.quantite * oi.prix_unitaire),2) AS ca_produit
FROM order_items oi
JOIN products    p  ON p.id  = oi.product_id
JOIN categories  c  ON c.id  = p.category_id
JOIN orders      o  ON o.id  = oi.order_id
WHERE o.statut != 'annulee'
GROUP BY c.nom, p.nom
ORDER BY c.nom, unites_vendues DESC;

-- ─── Requête 4 : Clients inactifs depuis plus de 180 jours ───
-- Sous-requête, WHERE, ORDER BY
SELECT
    cu.id,
    CONCAT(cu.prenom, ' ', cu.nom)  AS client,
    cu.email,
    MAX(o.date_commande)             AS derniere_commande,
    DATEDIFF(NOW(), MAX(o.date_commande)) AS jours_inactif
FROM customers cu
JOIN orders o ON o.customer_id = cu.id
WHERE o.statut != 'annulee'
  AND cu.id NOT IN (
      SELECT DISTINCT customer_id
      FROM   orders
      WHERE  date_commande >= DATE_SUB(NOW(), INTERVAL 180 DAY)
        AND  statut != 'annulee'
  )
GROUP BY cu.id, cu.prenom, cu.nom, cu.email
ORDER BY jours_inactif DESC;

-- ─── Requête 5 : Catégories avec panier moyen > 50 € ─────────
-- GROUP BY, HAVING, ORDER BY
SELECT
    c.nom                            AS categorie,
    COUNT(DISTINCT o.id)             AS nb_commandes_avec_categorie,
    SUM(oi.quantite)                 AS unites_totales,
    ROUND(AVG(oi.prix_unitaire), 2)  AS prix_moyen_produit,
    ROUND(SUM(oi.quantite * oi.prix_unitaire), 2) AS ca_categorie
FROM order_items oi
JOIN products   p ON p.id = oi.product_id
JOIN categories c ON c.id = p.category_id
JOIN orders     o ON o.id = oi.order_id
WHERE o.statut != 'annulee'
GROUP BY c.nom
HAVING prix_moyen_produit > 25
ORDER BY ca_categorie DESC;

-- ─── Requête 6 : CTE — Clients et leur rang RFM ──────────────
WITH rfm_base AS (
    SELECT
        customer_id,
        DATEDIFF(NOW(), MAX(date_commande))  AS recency,
        COUNT(*)                             AS frequency,
        ROUND(SUM(montant_total), 2)         AS monetary
    FROM orders
    WHERE statut != 'annulee'
    GROUP BY customer_id
),
rfm_ranked AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency ASC)   AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)  AS m_score
    FROM rfm_base
)
SELECT
    r.customer_id,
    CONCAT(cu.prenom, ' ', cu.nom) AS client,
    r.recency,
    r.frequency,
    r.monetary,
    (r.r_score + r.f_score + r.m_score) AS rfm_total
FROM rfm_ranked r
JOIN customers cu ON cu.id = r.customer_id
ORDER BY rfm_total DESC
LIMIT 20;

-- ─── Requête 7 : Panier moyen par pays ───────────────────────
SELECT
    cu.pays_code,
    COUNT(DISTINCT cu.id)           AS nb_clients,
    COUNT(o.id)                     AS nb_commandes,
    ROUND(AVG(o.montant_total), 2)  AS panier_moyen,
    ROUND(SUM(o.montant_total), 2)  AS ca_total
FROM customers cu
JOIN orders o ON o.customer_id = cu.id
WHERE o.statut != 'annulee'
GROUP BY cu.pays_code
ORDER BY ca_total DESC;

-- ─── Utilisation de la vue v_top_produits ────────────────────
SELECT * FROM v_top_produits LIMIT 10;

-- ─── Utilisation de la vue v_ca_mensuel ──────────────────────
SELECT * FROM v_ca_mensuel;

-- ─── Test de la fonction fn_niveau_client ────────────────────
SELECT
    id,
    CONCAT(prenom, ' ', nom) AS client,
    fn_niveau_client(id)     AS niveau
FROM customers
ORDER BY id
LIMIT 10;
