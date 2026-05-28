"""
GlowShop Analytics — Dashboard Plotly Dash
  - 3 KPIs : CA total, Clients actifs, Panier moyen
  - 4 graphiques : segments RFM, CA mensuel, Top produits, Répartition pays
  - Filtres interactifs : Dropdown segment, Dropdown pays
  - Callbacks : mise à jour dynamique des graphiques
"""

import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

load_dotenv()

# ─── Connexion ────────────────────────────────────────────────────────────────

DB_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER','root')}:"
    f"{os.getenv('MYSQL_PASSWORD','')}@"
    f"{os.getenv('MYSQL_HOST','localhost')}:"
    f"{os.getenv('MYSQL_PORT','3306')}/"
    f"{os.getenv('MYSQL_DATABASE','glowshop_db')}?charset=utf8mb4"
)
engine = create_engine(DB_URL, echo=False)


# ─── Chargement des données ───────────────────────────────────────────────────

def load_dashboard_data():
    rfm = pd.read_sql("""
        SELECT r.*, CONCAT(c.prenom,' ',c.nom) AS client,
               c.pays_code, c.pays_region, c.ville
        FROM rfm_scores r
        JOIN customers c ON c.id = r.customer_id
    """, engine)

    orders = pd.read_sql("""
        SELECT o.*, CONCAT(c.prenom,' ',c.nom) AS client,
               c.pays_code
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        WHERE o.statut != 'annulee'
    """, engine)
    orders["date_commande"] = pd.to_datetime(orders["date_commande"])
    orders["mois"] = orders["date_commande"].dt.to_period("M").astype(str)

    top_products = pd.read_sql(
        "SELECT * FROM v_top_produits LIMIT 15", engine
    )

    return rfm, orders, top_products


rfm_df, orders_df, top_prod_df = load_dashboard_data()

SEGMENTS     = ["Tous"] + sorted(rfm_df["segment"].unique().tolist())
PAYS_OPTIONS = ["Tous"] + sorted(rfm_df["pays_code"].unique().tolist())

# Couleurs par segment
SEGMENT_COLORS = {
    "Champions":       "#6C63FF",
    "Clients Fidèles": "#3ECFCF",
    "Potentiels":      "#F4D03F",
    "Nouveaux Clients":"#2ECC71",
    "À Risque":        "#E67E22",
    "Perdus":          "#E74C3C",
}


# ─── KPIs ────────────────────────────────────────────────────────────────────

def compute_kpis(df_orders):
    ca_total     = df_orders["montant_total"].sum()
    nb_clients   = df_orders["customer_id"].nunique()
    panier_moyen = df_orders["montant_total"].mean()
    return ca_total, nb_clients, panier_moyen


# ─── Layout ───────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="GlowShop Analytics",
)

app.layout = dbc.Container([

    # ── Header
    dbc.Row([
        dbc.Col([
            html.H1("💄 GlowShop Analytics", className="text-primary fw-bold mt-3"),
            html.P("Dashboard d'analyse marketing · RFM · Performances produits",
                   className="text-muted"),
            html.Hr(),
        ])
    ]),

    # ── Filtres
    dbc.Row([
        dbc.Col([
            html.Label("Segment RFM", className="fw-semibold"),
            dcc.Dropdown(
                id="filter-segment",
                options=[{"label": s, "value": s} for s in SEGMENTS],
                value="Tous",
                clearable=False,
            ),
        ], md=4),
        dbc.Col([
            html.Label("Pays", className="fw-semibold"),
            dcc.Dropdown(
                id="filter-pays",
                options=[{"label": p, "value": p} for p in PAYS_OPTIONS],
                value="Tous",
                clearable=False,
            ),
        ], md=4),
        dbc.Col([
            html.Label("Période (mois glissants)", className="fw-semibold"),
            dcc.Slider(
                id="filter-months",
                min=3, max=24, step=3, value=12,
                marks={i: f"{i}m" for i in [3, 6, 12, 18, 24]},
            ),
        ], md=4),
    ], className="mb-4"),

    # ── KPIs
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Chiffre d'Affaires Total", className="text-muted"),
                html.H3(id="kpi-ca", className="text-primary fw-bold"),
            ])
        ], className="shadow-sm"), md=4),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Clients Actifs", className="text-muted"),
                html.H3(id="kpi-clients", className="text-success fw-bold"),
            ])
        ], className="shadow-sm"), md=4),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Panier Moyen", className="text-muted"),
                html.H3(id="kpi-panier", className="text-warning fw-bold"),
            ])
        ], className="shadow-sm"), md=4),
    ], className="mb-4"),

    # ── Graphiques ligne 1
    dbc.Row([
        dbc.Col(dcc.Graph(id="graph-rfm-segments"), md=5),
        dbc.Col(dcc.Graph(id="graph-ca-mensuel"),   md=7),
    ], className="mb-3"),

    # ── Graphiques ligne 2
    dbc.Row([
        dbc.Col(dcc.Graph(id="graph-top-produits"), md=7),
        dbc.Col(dcc.Graph(id="graph-pays"),         md=5),
    ], className="mb-4"),

    html.Footer("GlowShop Analytics · MSc2 Manager Data Marketing · 2026",
                className="text-center text-muted py-3"),

], fluid=True)


# ─── Callbacks ────────────────────────────────────────────────────────────────

@app.callback(
    Output("kpi-ca",      "children"),
    Output("kpi-clients", "children"),
    Output("kpi-panier",  "children"),
    Output("graph-rfm-segments", "figure"),
    Output("graph-ca-mensuel",   "figure"),
    Output("graph-top-produits", "figure"),
    Output("graph-pays",         "figure"),
    Input("filter-segment", "value"),
    Input("filter-pays",    "value"),
    Input("filter-months",  "value"),
)
def update_dashboard(segment, pays, months):
    # ── Filtrage commandes
    cutoff = orders_df["date_commande"].max() - pd.DateOffset(months=months)
    df_ord = orders_df[orders_df["date_commande"] >= cutoff].copy()

    if pays != "Tous":
        df_ord = df_ord[df_ord["pays_code"] == pays]

    # ── Filtrage RFM
    df_rfm = rfm_df.copy()
    if segment != "Tous":
        df_rfm  = df_rfm[df_rfm["segment"] == segment]
        df_ord  = df_ord[df_ord["customer_id"].isin(df_rfm["customer_id"])]
    if pays != "Tous":
        df_rfm = df_rfm[df_rfm["pays_code"] == pays]

    # ── KPIs
    ca, nb_cl, panier = compute_kpis(df_ord)
    kpi_ca      = f"{ca:,.0f} €".replace(",", " ")
    kpi_clients = f"{nb_cl}"
    kpi_panier  = f"{panier:,.2f} €".replace(",", " ") if nb_cl else "—"

    # ── Figure 1 : Répartition segments RFM (donut)
    seg_counts = rfm_df["segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "count"]
    fig_rfm = px.pie(
        seg_counts, names="segment", values="count",
        hole=0.45,
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        title="Segments RFM",
    )
    fig_rfm.update_traces(textinfo="label+percent")
    fig_rfm.update_layout(showlegend=False, margin=dict(t=40, b=0))

    # ── Figure 2 : CA mensuel (courbe)
    ca_mois = (df_ord.groupby("mois")["montant_total"]
               .sum().reset_index()
               .rename(columns={"montant_total": "ca"}))
    ca_mois = ca_mois.sort_values("mois")
    fig_ca = px.line(
        ca_mois, x="mois", y="ca",
        markers=True,
        labels={"mois": "Mois", "ca": "CA (€)"},
        title=f"Chiffre d'Affaires mensuel — {months} derniers mois",
    )
    fig_ca.update_traces(line_color="#6C63FF", line_width=2.5)
    fig_ca.update_layout(margin=dict(t=40, b=0))

    # ── Figure 3 : Top 15 produits (barres horizontales)
    fig_prod = px.bar(
        top_prod_df.sort_values("unites_vendues"),
        x="unites_vendues", y="nom",
        orientation="h",
        color="categorie",
        labels={"unites_vendues": "Unités vendues", "nom": ""},
        title="Top 15 produits par unités vendues",
    )
    fig_prod.update_layout(margin=dict(t=40, b=0), legend_title="Catégorie")

    # ── Figure 4 : CA par pays (barres)
    ca_pays = (df_ord.groupby("pays_code")["montant_total"]
               .sum().reset_index()
               .rename(columns={"montant_total": "ca"})
               .sort_values("ca", ascending=False))
    fig_pays = px.bar(
        ca_pays, x="pays_code", y="ca",
        labels={"pays_code": "Pays", "ca": "CA (€)"},
        title="CA par pays",
        color="ca",
        color_continuous_scale="Purples",
    )
    fig_pays.update_layout(margin=dict(t=40, b=0), coloraxis_showscale=False)

    return (kpi_ca, kpi_clients, kpi_panier,
            fig_rfm, fig_ca, fig_prod, fig_pays)


# ─── Lancement ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Dashboard disponible sur http://127.0.0.1:8050")
    app.run(debug=True)
