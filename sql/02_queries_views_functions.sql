-- ============================================================
-- PROJET ALGO & BDD — Requêtes analytiques
-- ============================================================

USE newsletter_scoring;

-- ============================================================
-- REQUÊTE 1 — Taux d'ouverture par campagne (WHERE + GROUP BY + ORDER BY)
-- ============================================================
SELECT
    c.nom_campagne,
    c.categorie,
    c.date_envoi,
    COUNT(e.id_envoi)                                          AS nb_envoyes,
    SUM(e.ouvert)                                              AS nb_ouverts,
    ROUND(100.0 * SUM(e.ouvert) / COUNT(e.id_envoi), 2)       AS taux_ouverture_pct,
    ROUND(100.0 * SUM(e.clique) / COUNT(e.id_envoi), 2)       AS taux_clic_pct
FROM campagnes c
JOIN envois e ON c.id_campagne = e.id_campagne
WHERE c.date_envoi BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY c.id_campagne, c.nom_campagne, c.categorie, c.date_envoi
ORDER BY taux_ouverture_pct DESC;

-- ============================================================
-- REQUÊTE 2 — Abonnés avec plus de 8 ouvertures sur l'année (HAVING)
-- ============================================================
SELECT
    a.prenom,
    a.nom,
    a.email,
    a.segment_age,
    COUNT(CASE WHEN e.ouvert = 1 THEN 1 END)  AS nb_ouvertures,
    COUNT(CASE WHEN e.clique = 1 THEN 1 END)  AS nb_clics
FROM abonnes a
JOIN envois e ON a.id_abonne = e.id_abonne
GROUP BY a.id_abonne, a.prenom, a.nom, a.email, a.segment_age
HAVING nb_ouvertures > 8
ORDER BY nb_ouvertures DESC;

-- ============================================================
-- REQUÊTE 3 — Top 5 des abonnés les plus cliqueurs (LIMIT)
-- ============================================================
SELECT
    a.prenom,
    a.nom,
    a.ville,
    COUNT(CASE WHEN e.clique = 1 THEN 1 END) AS nb_clics
FROM abonnes a
JOIN envois e ON a.id_abonne = e.id_abonne
WHERE e.desabonne = 0
GROUP BY a.id_abonne, a.prenom, a.nom, a.ville
ORDER BY nb_clics DESC
LIMIT 5;

-- ============================================================
-- REQUÊTE 4 — Jointure sur 3 tables : produits cliqués par abonné
-- ============================================================
SELECT
    a.prenom,
    a.nom,
    c.nom_campagne,
    p.nom_produit,
    p.categorie          AS categorie_produit,
    cp.date_clic
FROM abonnes a
JOIN envois e         ON a.id_abonne   = e.id_abonne
JOIN clics_produits cp ON e.id_envoi   = cp.id_envoi
JOIN produits p       ON cp.id_produit = p.id_produit
JOIN campagnes c      ON e.id_campagne = c.id_campagne
ORDER BY cp.date_clic;

-- ============================================================
-- REQUÊTE 5 — Segmentation par tranche d'âge (GROUP BY + ORDER BY)
-- ============================================================
SELECT
    a.segment_age,
    COUNT(DISTINCT a.id_abonne)                                          AS nb_abonnes,
    ROUND(100.0 * SUM(e.ouvert) / COUNT(e.id_envoi), 2)                 AS taux_ouverture_pct,
    ROUND(100.0 * SUM(e.clique) / COUNT(e.id_envoi), 2)                 AS taux_clic_pct,
    ROUND(100.0 * SUM(e.desabonne) / COUNT(e.id_envoi), 2)              AS taux_desabonnement_pct
FROM abonnes a
JOIN envois e ON a.id_abonne = e.id_abonne
GROUP BY a.segment_age
ORDER BY taux_clic_pct DESC;

-- ============================================================
-- REQUÊTE 6 — CTE : abonnés dont le taux de clic dépasse la moyenne
-- ============================================================
WITH stats_abonnes AS (
    SELECT
        a.id_abonne,
        a.prenom,
        a.nom,
        COUNT(e.id_envoi)                                    AS nb_envois,
        SUM(e.clique)                                        AS nb_clics,
        ROUND(100.0 * SUM(e.clique) / COUNT(e.id_envoi), 2) AS taux_clic
    FROM abonnes a
    JOIN envois e ON a.id_abonne = e.id_abonne
    GROUP BY a.id_abonne, a.prenom, a.nom
),
moyenne AS (
    SELECT ROUND(AVG(taux_clic), 2) AS moy_clic FROM stats_abonnes
)
SELECT
    s.prenom,
    s.nom,
    s.taux_clic,
    m.moy_clic,
    ROUND(s.taux_clic - m.moy_clic, 2) AS ecart_moyenne
FROM stats_abonnes s
CROSS JOIN moyenne m
WHERE s.taux_clic > m.moy_clic
ORDER BY s.taux_clic DESC;

-- ============================================================
-- VUE — Engagement global par abonné (réutilisable par Python)
-- ============================================================
CREATE OR REPLACE VIEW vue_engagement_abonnes AS
SELECT
    a.id_abonne,
    a.email,
    a.prenom,
    a.nom,
    a.ville,
    a.pays,
    a.segment_age,
    a.date_inscription,
    COUNT(e.id_envoi)                                         AS nb_envois_recus,
    SUM(e.ouvert)                                             AS nb_ouvertures,
    SUM(e.clique)                                             AS nb_clics,
    SUM(e.desabonne)                                          AS nb_desabonnements,
    ROUND(100.0 * SUM(e.ouvert)  / COUNT(e.id_envoi), 2)     AS taux_ouverture,
    ROUND(100.0 * SUM(e.clique)  / COUNT(e.id_envoi), 2)     AS taux_clic,
    MAX(CASE WHEN e.ouvert = 1 THEN e.date_envoi END)         AS derniere_ouverture
FROM abonnes a
LEFT JOIN envois e ON a.id_abonne = e.id_abonne
GROUP BY
    a.id_abonne, a.email, a.prenom, a.nom,
    a.ville, a.pays, a.segment_age, a.date_inscription;

-- ============================================================
-- FONCTION — Calcul du score d'engagement d'un abonné (0 à 100)
-- ============================================================
DELIMITER $$

CREATE FUNCTION IF NOT EXISTS fn_score_engagement(
    p_nb_ouvertures INT,
    p_nb_clics      INT,
    p_nb_envois     INT,
    p_desabonne     INT
)
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    DECLARE score DECIMAL(5,2);
    DECLARE tx_ouverture DECIMAL(5,2);
    DECLARE tx_clic      DECIMAL(5,2);

    IF p_nb_envois = 0 THEN
        RETURN 0;
    END IF;

    SET tx_ouverture = 100.0 * p_nb_ouvertures / p_nb_envois;
    SET tx_clic      = 100.0 * p_nb_clics      / p_nb_envois;

    -- Formule pondérée : ouverture 40 % + clic 60 % - pénalité désabonnement
    SET score = (tx_ouverture * 0.4) + (tx_clic * 0.6) - (p_desabonne * 10);

    -- Borne entre 0 et 100
    IF score < 0 THEN SET score = 0; END IF;
    IF score > 100 THEN SET score = 100; END IF;

    RETURN score;
END $$

DELIMITER ;

-- ============================================================
-- PROCÉDURE — Mise à jour du segment d'engagement dans la vue
-- (Exemple de procédure avec paramètres et logique conditionnelle)
-- ============================================================
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS sp_afficher_segments_engagement()
BEGIN
    SELECT
        v.prenom,
        v.nom,
        v.taux_ouverture,
        v.taux_clic,
        fn_score_engagement(v.nb_ouvertures, v.nb_clics, v.nb_envois_recus, v.nb_desabonnements) AS score,
        CASE
            WHEN fn_score_engagement(v.nb_ouvertures, v.nb_clics, v.nb_envois_recus, v.nb_desabonnements) >= 60 THEN 'Champion'
            WHEN fn_score_engagement(v.nb_ouvertures, v.nb_clics, v.nb_envois_recus, v.nb_desabonnements) >= 35 THEN 'Actif'
            WHEN fn_score_engagement(v.nb_ouvertures, v.nb_clics, v.nb_envois_recus, v.nb_desabonnements) >= 15 THEN 'Passif'
            ELSE 'Inactif'
        END AS segment_engagement
    FROM vue_engagement_abonnes v
    ORDER BY score DESC;
END $$

DELIMITER ;

-- Appel de la procédure
CALL sp_afficher_segments_engagement();
