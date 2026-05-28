-- ============================================================
-- GlowShop Analytics — Fonction + Procédure stockée
-- À exécuter via : File > Run SQL Script (pas le bouton éclair)
-- ============================================================

USE glowshop_db;

DELIMITER $$

DROP FUNCTION IF EXISTS fn_niveau_client$$

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
        SET niveau = 'Fidele';
    ELSEIF total_ca >= 50 THEN
        SET niveau = 'Regulier';
    ELSE
        SET niveau = 'Nouveau';
    END IF;

    RETURN niveau;
END$$

DROP PROCEDURE IF EXISTS sp_update_stock$$

CREATE PROCEDURE sp_update_stock(IN p_order_id INT)
BEGIN
    UPDATE products p
    JOIN order_items oi ON oi.product_id = p.id
    SET p.stock = p.stock - oi.quantite
    WHERE oi.order_id = p_order_id;
END$$

DELIMITER ;
