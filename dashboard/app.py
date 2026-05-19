"""
Dashboard interactif — Newsletter Engagement Scoring
=====================================================
Visualisation des KPIs et segments d'engagement des abonnés newsletter.

Auteur : Kamilia Malih
Cours  : MSc2 Manager Data Marketing — Algo & BDD 2026

Lancement : python dashboard/app.py
Accès     : http://127.0.0.1:8050
"""

import os
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
from dotenv import load_dotenv

load_dotenv()

# ─── CONNEXION ET CHARGEMENT ──────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    """Charge la table de scoring depuis MySQL."""
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "newsletter_scoring")
    )
    df = pd.read_sql("SELECT * FROM scoring_engagement", conn)
    conn.close()
    return df


def load_campagnes() -> pd.DataFrame:
    """Charge les statistiques de campagne."""
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "newsletter_scoring")
    )
    query = """
        SELECT
            c.nom_campagne,
            c.categorie,
            c.date_envoi,
            ROUND(100.0 * SUM(e.ouvert) / COUNT(e.id_envoi), 2)  AS taux_ouverture,
            ROUND(100.0 * SUM(e.clique) / COUNT(e.id_envoi), 2)  AS taux_clic
        FROM campagnes c
        JOIN envois e ON c.id_campagne = e.id_campagne
        GROUP BY c.id_campagne, c.nom_campagne, c.categorie, c.date_envoi
        ORDER BY c.date_envoi
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# Chargement initial des données
df = load_data()
df_camp = load_campagnes()

# ─── INITIALISATION DASH ──────────────────────────────────────────────────────

app = Dash(
    __name__,
    title="Newsletter Engagement Dashboard",
    suppress_callback_exceptions=True
)

# Palette de couleurs par segment
COULEURS_SEGMENT = {
    "Champion": "#2563EB",
    "Actif":    "#16A34A",
    "Passif":   "#D97706",
    "Inactif":  "#DC2626",
}

# ─── MISE EN PAGE ─────────────────────────────────────────────────────────────

app.layout = html.Div(
    style={"fontFamily": "Inter, sans-serif", "backgroundColor": "#F8FAFC", "minHeight": "100vh"},
    children=[

        # En-tête
        html.Div(
            style={"backgroundColor": "#1E3A5F", "padding": "24px 40px", "color": "white"},
            children=[
                html.H1("Newsletter Engagement Dashboard", style={"margin": 0, "fontSize": "1.6rem"}),
                html.P("Scoring & segmentation des abonnés — 2024", style={"margin": "4px 0 0", "opacity": 0.7}),
            ]
        ),

        # Filtres
        html.Div(
            style={"backgroundColor": "white", "padding": "20px 40px", "borderBottom": "1px solid #E2E8F0",
                   "display": "flex", "gap": "32px", "alignItems": "center", "flexWrap": "wrap"},
            children=[
                html.Div([
                    html.Label("Segment d'engagement", style={"fontWeight": 600, "fontSize": "0.85rem", "color": "#475569"}),
                    dcc.Dropdown(
                        id="filtre-segment",
                        options=[{"label": s, "value": s} for s in ["Champion", "Actif", "Passif", "Inactif"]],
                        placeholder="Tous les segments",
                        multi=True,
                        style={"width": "260px", "marginTop": "6px"}
                    ),
                ]),
                html.Div([
                    html.Label("Tranche d'âge", style={"fontWeight": 600, "fontSize": "0.85rem", "color": "#475569"}),
                    dcc.Dropdown(
                        id="filtre-age",
                        options=[{"label": a, "value": a} for a in sorted(df["segment_age"].dropna().unique())],
                        placeholder="Toutes tranches",
                        multi=True,
                        style={"width": "200px", "marginTop": "6px"}
                    ),
                ]),
                html.Div([
                    html.Label("Score minimum", style={"fontWeight": 600, "fontSize": "0.85rem", "color": "#475569"}),
                    dcc.Slider(
                        id="filtre-score",
                        min=0, max=100, step=5, value=0,
                        marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"},
                        tooltip={"placement": "bottom"},
                    ),
                ], style={"width": "220px"}),
            ]
        ),

        # KPIs
        html.Div(
            id="kpi-container",
            style={"display": "flex", "gap": "20px", "padding": "28px 40px", "flexWrap": "wrap"}
        ),

        # Graphiques — ligne 1
        html.Div(
            style={"display": "flex", "gap": "20px", "padding": "0 40px 20px", "flexWrap": "wrap"},
            children=[
                html.Div(
                    dcc.Graph(id="graph-segments"),
                    style={"flex": "1", "minWidth": "340px", "backgroundColor": "white",
                           "borderRadius": "12px", "padding": "16px", "boxShadow": "0 1px 4px rgba(0,0,0,.07)"}
                ),
                html.Div(
                    dcc.Graph(id="graph-score-age"),
                    style={"flex": "1", "minWidth": "340px", "backgroundColor": "white",
                           "borderRadius": "12px", "padding": "16px", "boxShadow": "0 1px 4px rgba(0,0,0,.07)"}
                ),
            ]
        ),

        # Graphiques — ligne 2
        html.Div(
            style={"display": "flex", "gap": "20px", "padding": "0 40px 32px", "flexWrap": "wrap"},
            children=[
                html.Div(
                    dcc.Graph(id="graph-campagnes"),
                    style={"flex": "2", "minWidth": "500px", "backgroundColor": "white",
                           "borderRadius": "12px", "padding": "16px", "boxShadow": "0 1px 4px rgba(0,0,0,.07)"}
                ),
                html.Div(
                    dcc.Graph(id="graph-scatter"),
                    style={"flex": "1", "minWidth": "320px", "backgroundColor": "white",
                           "borderRadius": "12px", "padding": "16px", "boxShadow": "0 1px 4px rgba(0,0,0,.07)"}
                ),
            ]
        ),
    ]
)


# ─── CALLBACK PRINCIPAL ───────────────────────────────────────────────────────

@app.callback(
    Output("kpi-container",  "children"),
    Output("graph-segments", "figure"),
    Output("graph-score-age","figure"),
    Output("graph-campagnes","figure"),
    Output("graph-scatter",  "figure"),
    Input("filtre-segment",  "value"),
    Input("filtre-age",      "value"),
    Input("filtre-score",    "value"),
)
def update_dashboard(segments_selectionnes, ages_selectionnes, score_min):
    """Met à jour tous les composants du dashboard selon les filtres actifs."""

    # Filtrage du DataFrame
    dff = df.copy()
    if segments_selectionnes:
        dff = dff[dff["segment_engagement"].isin(segments_selectionnes)]
    if ages_selectionnes:
        dff = dff[dff["segment_age"].isin(ages_selectionnes)]
    dff = dff[dff["score_engagement"] >= score_min]

    # ── KPIs ──────────────────────────────────────────────────────────────────

    nb_abonnes   = len(dff)
    score_moyen  = round(dff["score_engagement"].mean(), 1) if nb_abonnes else 0
    taux_ouv_moy = round(dff["taux_ouverture"].mean(), 1)   if nb_abonnes else 0
    taux_clic_moy= round(dff["taux_clic"].mean(), 1)        if nb_abonnes else 0

    def kpi_card(titre, valeur, unite="", couleur="#1E3A5F"):
        return html.Div(
            style={"backgroundColor": "white", "borderRadius": "12px", "padding": "20px 24px",
                   "boxShadow": "0 1px 4px rgba(0,0,0,.07)", "minWidth": "160px", "flex": "1"},
            children=[
                html.P(titre, style={"margin": 0, "fontSize": "0.82rem", "color": "#64748B", "fontWeight": 500}),
                html.Div(
                    style={"display": "flex", "alignItems": "baseline", "gap": "4px", "marginTop": "8px"},
                    children=[
                        html.Span(str(valeur), style={"fontSize": "2rem", "fontWeight": 700, "color": couleur}),
                        html.Span(unite,       style={"fontSize": "1rem", "color": "#94A3B8"}),
                    ]
                ),
            ]
        )

    kpis = [
        kpi_card("Abonnés filtrés",    nb_abonnes,   "",   "#1E3A5F"),
        kpi_card("Score moyen",         score_moyen,  "/100","#2563EB"),
        kpi_card("Taux ouverture moyen",taux_ouv_moy, " %",  "#16A34A"),
        kpi_card("Taux de clic moyen",  taux_clic_moy," %",  "#D97706"),
    ]

    # ── Graphique 1 : répartition des segments (donut) ──────────────────────

    seg_counts = dff["segment_engagement"].value_counts().reset_index()
    seg_counts.columns = ["segment", "count"]

    fig_seg = px.pie(
        seg_counts, names="segment", values="count",
        title="Répartition des segments d'engagement",
        color="segment",
        color_discrete_map=COULEURS_SEGMENT,
        hole=0.5,
    )
    fig_seg.update_traces(textinfo="label+percent")
    fig_seg.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))

    # ── Graphique 2 : score moyen par tranche d'âge (bar) ───────────────────

    score_age = dff.groupby("segment_age")["score_engagement"].mean().reset_index()
    score_age.columns = ["segment_age", "score_moyen"]
    score_age = score_age.sort_values("score_moyen", ascending=False)

    fig_age = px.bar(
        score_age, x="segment_age", y="score_moyen",
        title="Score d'engagement moyen par tranche d'âge",
        labels={"segment_age": "Tranche d'âge", "score_moyen": "Score moyen"},
        color="score_moyen",
        color_continuous_scale="Blues",
    )
    fig_age.update_layout(coloraxis_showscale=False, margin=dict(t=40, b=40))

    # ── Graphique 3 : taux d'ouverture et clic par campagne (ligne) ─────────

    fig_camp = go.Figure()
    fig_camp.add_trace(go.Scatter(
        x=df_camp["nom_campagne"], y=df_camp["taux_ouverture"],
        mode="lines+markers", name="Taux ouverture (%)",
        line=dict(color="#2563EB", width=2),
        marker=dict(size=7)
    ))
    fig_camp.add_trace(go.Scatter(
        x=df_camp["nom_campagne"], y=df_camp["taux_clic"],
        mode="lines+markers", name="Taux clic (%)",
        line=dict(color="#D97706", width=2, dash="dot"),
        marker=dict(size=7)
    ))
    fig_camp.update_layout(
        title="Performances par campagne (2024)",
        xaxis_title="Campagne",
        yaxis_title="Taux (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60, b=80),
        xaxis=dict(tickangle=-30),
    )

    # ── Graphique 4 : scatter taux ouverture vs score ─────────────────────

    fig_scatter = px.scatter(
        dff,
        x="taux_ouverture", y="score_engagement",
        color="segment_engagement",
        color_discrete_map=COULEURS_SEGMENT,
        hover_data=["prenom", "nom", "taux_clic"],
        title="Taux ouverture vs Score d'engagement",
        labels={"taux_ouverture": "Taux ouverture (%)", "score_engagement": "Score (0–100)"},
        size_max=12,
    )
    fig_scatter.update_layout(
        legend=dict(title="Segment", orientation="v"),
        margin=dict(t=40, b=40)
    )

    return kpis, fig_seg, fig_age, fig_camp, fig_scatter


# ─── LANCEMENT ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=8050)
