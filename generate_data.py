"""
Génère les fichiers SQL du projet GlowShop Analytics.
Exécuter une seule fois : python generate_data.py
"""
import random
from datetime import datetime, timedelta, date
import os

random.seed(42)

# ─── Données de référence ─────────────────────────────────────────────────────

CATEGORIES = [
    (1, 'Soins Visage',  'Crèmes, sérums et masques pour le visage'),
    (2, 'Maquillage',    'Rouge à lèvres, fond de teint, mascara et plus'),
    (3, 'Soins Corps',   'Lotions, gommages et huiles pour le corps'),
    (4, 'Parfums',       'Eaux de parfum et eaux de toilette'),
    (5, 'Accessoires',   'Pinceaux, éponges et outils de beauté'),
]

PRODUCTS = [
    (1,  'Sérum Vitamine C Éclat',       'Sérum illuminateur à la vitamine C pure',             1, 38.90, 150),
    (2,  'Crème Hydratante Jour SPF30',  'Hydratation intense avec protection solaire',          1, 32.50, 200),
    (3,  'Crème Nuit Régénérante',       'Crème de nuit au rétinol et acide hyaluronique',       1, 45.00, 120),
    (4,  'Masque Éclat Kaolin',          'Masque purifiant à l\'argile kaolin',                  1, 22.90, 180),
    (5,  'Lotion Tonique Rose',          'Lotion tonique à l\'eau de rose',                      1, 18.50, 250),
    (6,  'Soin Contour des Yeux',        'Soin anti-cernes et anti-poches',                      1, 42.00,  90),
    (7,  'Sérum Anti-Âge Peptides',      'Sérum concentré aux peptides actifs',                  1, 55.00,  75),
    (8,  'Rouge à Lèvres Satin Rouge',   'Rouge à lèvres longue tenue fini satin',               2, 19.90, 300),
    (9,  'Foundation Hydratante 24h',    'Fond de teint couvrant et hydratant',                  2, 28.50, 220),
    (10, 'Mascara Volume Extrême',       'Mascara volumisant et allongeant',                     2, 22.00, 280),
    (11, 'Palette Fards Nude',           'Palette 12 couleurs tons nude',                        2, 35.00, 150),
    (12, 'Crayon Liner Noir Intense',    'Crayon liner longue tenue',                            2, 12.50, 350),
    (13, 'Blush Rose Poudre',            'Blush poudre fini naturel',                            2, 24.90, 200),
    (14, 'BB Cream Perfectrice',         'BB Cream unifiante SPF15',                             2, 21.00, 190),
    (15, 'Lotion Corps Hydratante',      'Lotion légère hydratation quotidienne',                3, 16.90, 300),
    (16, 'Gommage Corps Sucre',          'Gommage exfoliant sucre et huile d\'amande',           3, 20.00, 180),
    (17, 'Huile Sèche Corps Dorée',      'Huile sèche sublimatrice avec paillettes',             3, 26.50, 140),
    (18, 'Beurre de Karité Pur',         'Beurre de karité non raffiné 200ml',                  3, 14.90, 250),
    (19, 'Crème Mains Nourrissante',     'Crème mains intensive à la glycérine',                 3, 11.50, 400),
    (20, 'Lait Corps Parfumé Rose',      'Lait corps hydratant parfum rose',                     3, 18.90, 220),
    (21, 'Gel Douche Luxe Jasmin',       'Gel douche onctueux parfum jasmin',                    3, 13.50, 350),
    (22, 'Eau de Parfum Floral 50ml',    'Fragrance florale légère et fraîche',                  4, 65.00,  80),
    (23, 'Eau de Toilette Boisé 100ml',  'Fragrance boisée et chaleureuse',                      4, 48.00, 100),
    (24, 'Eau de Parfum Oriental 50ml',  'Fragrance orientale et enivrante',                     4, 75.00,  60),
    (25, 'Brume Corps Rose 200ml',       'Brume parfumée légère à la rose',                      4, 22.00, 200),
    (26, 'Eau de Cologne Citrus 100ml',  'Eau de cologne fraîche agrumes',                       4, 38.00, 120),
    (27, 'Parfum Intense Nuit 30ml',     'Parfum intense et mystérieux',                         4, 82.00,  50),
    (28, 'Roller Parfumé Fleur Blanche', 'Roller parfumé pratique et discret',                   4, 15.90, 250),
    (29, 'Set 12 Pinceaux Maquillage',  'Set complet de pinceaux professionnels',                5, 35.90, 120),
    (30, 'Éponge Teint Beautyblender',   'Éponge applicateur fond de teint',                     5, 12.90, 350),
    (31, 'Bandeau Cheveux Soin',         'Bandeau élastique pour soins du visage',               5,  8.50, 400),
    (32, 'Trousse Beauté Voyage',        'Trousse imperméable format voyage',                    5, 19.90, 180),
    (33, 'Miroir Compact LED',           'Miroir grossissant avec éclairage LED',                5, 24.50, 150),
    (34, 'Recourbe-Cils Ergonomique',    'Recourbe-cils précision et confort',                   5,  9.90, 300),
    (35, 'Kit Soins Ongles 7 pièces',   'Kit manucure complet professionnel',                   5, 18.00, 200),
]

FIRST_NAMES = [
    'Emma','Léa','Camille','Sophie','Marie','Chloé','Manon','Inès','Sarah','Julie',
    'Charlotte','Alice','Laura','Pauline','Claire','Mathilde','Lucie','Océane','Margot','Justine',
    'Thomas','Lucas','Nathan','Nicolas','Julien','Antoine','Maxime','Pierre','Louis','Hugo',
    'Léonie','Nora','Yasmine','Amina','Sofia','Elena','Giulia','Ana','Maria','Eva',
    'Romain','Alexandre','Théo','Baptiste','Kevin','Axel','Enzo','Raphaël','Clément','Paul',
]

LAST_NAMES = [
    'Martin','Bernard','Thomas','Petit','Robert','Richard','Durand','Dubois','Moreau','Laurent',
    'Simon','Michel','Lefebvre','Leroy','Roux','David','Bertrand','Morel','Fournier','Girard',
    'Bonnet','Dupont','Lambert','Fontaine','Rousseau','Vincent','Muller','Lefevre','Faure','Andre',
    'Meyer','Robin','Blanc','Guerin','Adam','Roy','Jourdan','Barbier','Arnaud','Pierre',
    'Colin','Marchand','Renard','Legrand','Garnier','Gautier','Perrin','Chevalier','Gaillard','Gauthier',
]

COUNTRY_CITY = [
    ('FR','Paris'),('FR','Lyon'),('FR','Marseille'),('FR','Bordeaux'),('FR','Toulouse'),
    ('FR','Nice'),('FR','Nantes'),('FR','Strasbourg'),('FR','Montpellier'),('FR','Rennes'),
    ('FR','Paris'),('FR','Lyon'),('FR','Paris'),('FR','Lille'),('FR','Grenoble'),
    ('FR','Rouen'),('FR','Toulon'),('FR','Dijon'),('FR','Angers'),('FR','Nîmes'),
    ('FR','Villeurbanne'),('FR','Clermont-Ferrand'),('FR','Saint-Étienne'),('FR','Aix-en-Provence'),('FR','Le Mans'),
    ('FR','Brest'),('FR','Caen'),('FR','Amiens'),('FR','Limoges'),('FR','Tours'),
    ('BE','Bruxelles'),('BE','Liège'),('BE','Anvers'),('BE','Gand'),('BE','Bruges'),
    ('CH','Genève'),('CH','Zürich'),('CH','Lausanne'),('CH','Berne'),('CH','Bâle'),
    ('CA','Montréal'),('CA','Québec'),('CA','Toronto'),
    ('DE','Berlin'),('DE','Munich'),('DE','Hambourg'),
    ('ES','Madrid'),('ES','Barcelone'),
    ('IT','Rome'),('IT','Milan'),
]

STATUTS = ['livree','livree','livree','livree','livree','expediee','confirmee','annulee']

# ─── Génération des données ────────────────────────────────────────────────────

def normalize(s):
    replacements = {'é':'e','è':'e','ê':'e','ë':'e','î':'i','ï':'i',
                    'ô':'o','û':'u','ù':'u','ü':'u','à':'a','â':'a','ç':'c'}
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s

customers = []
for i in range(50):
    fn = FIRST_NAMES[i]
    ln = LAST_NAMES[i]
    email = f"{normalize(fn.lower())}.{normalize(ln.lower())}{i+1}@gmail.com"
    pays, ville = COUNTRY_CITY[i]
    days_back = random.randint(60, 1200)
    date_insc = (date(2026, 3, 1) - timedelta(days=days_back)).isoformat()
    phone = f"+33 6 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}"
    customers.append((i+1, fn, ln, email, pays, ville, date_insc, phone))

orders = []
order_items = []
item_id = 1

for order_id in range(1, 131):
    customer_id = random.randint(1, 50)
    days_back = random.randint(1, 800)
    order_dt = (datetime(2026, 3, 1) - timedelta(days=days_back)).strftime('%Y-%m-%d %H:%M:%S')
    statut = random.choice(STATUTS)

    num_items = random.randint(2, 4)
    chosen_pids = random.sample(range(1, 36), num_items)

    total = 0.0
    for pid in chosen_pids:
        qty = random.randint(1, 3)
        price = PRODUCTS[pid - 1][5]
        total += qty * price
        order_items.append((item_id, order_id, pid, qty, price))
        item_id += 1

    city = COUNTRY_CITY[customer_id - 1][1]
    orders.append((order_id, customer_id, order_dt, statut, round(total, 2), city))

# ─── Écriture du fichier SQL ───────────────────────────────────────────────────

os.makedirs('sql', exist_ok=True)

lines = ["-- Généré automatiquement par generate_data.py", "-- GlowShop Analytics - Données d'exemple", ""]

# Categories
lines.append("INSERT INTO categories (id, nom, description) VALUES")
rows = [f"  ({c[0]}, '{c[1]}', '{c[2]}')" for c in CATEGORIES]
lines.append(",\n".join(rows) + ";\n")

# Products
def esc(s):
    return s.replace("'", "\\'")

lines.append("INSERT INTO products (id, nom, description, category_id, prix, stock) VALUES")
rows = [f"  ({p[0]}, '{esc(p[1])}', '{esc(p[2])}', {p[3]}, {p[4]}, {p[5]})" for p in PRODUCTS]
lines.append(",\n".join(rows) + ";\n")

# Customers
lines.append("INSERT INTO customers (id, prenom, nom, email, pays_code, ville, date_inscription, telephone) VALUES")
rows = [f"  ({c[0]}, '{esc(c[1])}', '{esc(c[2])}', '{esc(c[3])}', '{c[4]}', '{esc(c[5])}', '{c[6]}', '{c[7]}')" for c in customers]
lines.append(",\n".join(rows) + ";\n")

# Orders
lines.append("INSERT INTO orders (id, customer_id, date_commande, statut, montant_total, adresse_livraison) VALUES")
rows = [f"  ({o[0]}, {o[1]}, '{o[2]}', '{o[3]}', {o[4]}, '{o[5]}')" for o in orders]
lines.append(",\n".join(rows) + ";\n")

# Order items
lines.append("INSERT INTO order_items (id, order_id, product_id, quantite, prix_unitaire) VALUES")
rows = [f"  ({it[0]}, {it[1]}, {it[2]}, {it[3]}, {it[4]})" for it in order_items]
lines.append(",\n".join(rows) + ";\n")

with open('sql/02_insert_data.sql', 'w', encoding='utf-8') as f:
    f.write("\n".join(lines))

print(f"Généré avec succès :")
print(f"  {len(CATEGORIES)} catégories")
print(f"  {len(PRODUCTS)} produits")
print(f"  {len(customers)} clients")
print(f"  {len(orders)} commandes")
print(f"  {len(order_items)} lignes de commande")
print("  -> sql/02_insert_data.sql")
