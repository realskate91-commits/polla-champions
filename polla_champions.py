"""
Polla Champions - versión combinada (equipos + ranking por persona) con alias de nombres corregidos
Requiere: streamlit, pandas, requests, rapidfuzz
"""

from typing import Dict, List, Tuple, Optional
import sys
import re
import requests
import pandas as pd

# Intentar importar streamlit; si no existe, seguimos en modo consola
USE_STREAMLIT = True
try:
    import streamlit as st
except Exception:
    st = None
    USE_STREAMLIT = False

# rapidfuzz para fuzzy matching
try:
    from rapidfuzz import process, fuzz
except Exception:
    process = None
    fuzz = None

# --------------------------
# CONFIGURACIÓN
# --------------------------
API_KEY = None
if USE_STREAMLIT and st is not None:
    API_KEY = st.secrets["football_data"]["api_key"] if "football_data" in st.secrets and "api_key" in st.secrets["football_data"] else None

COMPETITION_ID = "2001"  # Champions League

# Participantes y equipos
JUGADORES: Dict[str, List[str]] = {
    "Daniela": ["Napoli", "Paris Saint-Germain"],
    "Carlos": ["Bayern München", "Inter"],
    "Andrés": ["Atlético de Madrid", "Juventus"],
    "Bryan": ["Marseille", "Newcastle United"],
    "Nicolás": ["Chelsea", "Tottenham Hotspur"],
    "Diego": ["Borussia Dortmund", "Atalanta"],
    "Lina": ["Manchester City", "Galatasaray"],
    "Felipe": ["Benfica", "Real Madrid"],
    "Giovany": ["Arsenal", "Liverpool"],
    "Renzo": ["Barcelona", "Eintracht Frankfurt"]
}

# Alias para mejorar el reconocimiento de nombres
ALIASES = {
    "Inter": ["FC Internazionale Milano", "Internazionale", "Inter Milan"],
    "Marseille": ["Olympique de Marseille", "OM"],
    "Benfica": ["SL Benfica", "S.L. Benfica"],
    "Bayern München": ["FC Bayern München", "Bayern Munich"],
    "Paris Saint-Germain": ["Paris Saint Germain", "PSG"],
    "Atlético de Madrid": ["Atletico Madrid"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"],
    "Manchester City": ["Man City", "Manchester City FC"],
    "Real Madrid": ["Real Madrid CF"],
    "Arsenal": ["Arsenal FC"],
    "Juventus": ["Juventus FC"],
}

# --------------------------
# UTILIDADES
# --------------------------
def norm(s: str) -> str:
    return re.sub(r"\W+", "", s).lower() if isinstance(s, str) else ""

def best_match(name: str, choices: List[str], cutoff: int = 60) -> Tuple[Optional[str], int]:
    """Devuelve (mejor_coincidencia, score) usando rapidfuzz o matching simple."""
    if process is None:
        n = norm(name)
        for c in choices:
            if n in norm(c) or norm(c) in n:
                return (c, 100)
        return (None, 0)
    match = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
    if match:
        candidate, score, _ = match
        return (candidate, int(score))
    return (None, 0)

# --------------------------
# OBTENER STANDINGS vía API
# --------------------------
def obtener_standings_api(api_key: str) -> pd.DataFrame:
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION_ID}/standings"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text}")
    data = r.json()
    rows = []
    for group in data.get("standings", []):
        for entry in group.get("table", []):
            team_name = entry["team"]["name"]
            pts = entry.get("points", 0)
            gf = entry.get("goalsFor", 0)
            ga = entry.get("goalsAgainst", 0)
            diff = gf - ga
            rows.append({
                "Team": team_name,
                "PJ": entry.get("playedGames", 0),
                "PG": entry.get("won", 0),
                "PE": entry.get("draw", 0),
                "PP": entry.get("lost", 0),
                "GF": gf,
                "GC": ga,
                "Dif. Goles": diff,
                "Pts": int(pts)
            })
    df = pd.DataFrame(rows).drop_duplicates(subset=["Team"]).reset_index(drop=True)
    return df

# --------------------------
# FALLBACK: datos de ejemplo
# --------------------------
def ejemplo_standings() -> pd.DataFrame:
    data = [
        {"Team": "Manchester City", "Pts": 13, "Dif. Goles": 8},
        {"Team": "Paris Saint-Germain", "Pts": 12, "Dif. Goles": 7},
        {"Team": "Real Madrid", "Pts": 12, "Dif. Goles": 6},
        {"Team": "Bayern München", "Pts": 11, "Dif. Goles": 9},
        {"Team": "Arsenal", "Pts": 11, "Dif. Goles": 5},
        {"Team": "Napoli", "Pts": 10, "Dif. Goles": 3},
        {"Team": "Borussia Dortmund", "Pts": 10, "Dif. Goles": 4},
        {"Team": "Liverpool", "Pts": 10, "Dif. Goles": 6},
        {"Team": "Inter", "Pts": 9, "Dif. Goles": 2},
        {"Team": "Benfica", "Pts": 9, "Dif. Goles": 2},
        {"Team": "Atlético de Madrid", "Pts": 8, "Dif. Goles": 1},
        {"Team": "Barcelona", "Pts": 8, "Dif. Goles": 0},
        {"Team": "Juventus", "Pts": 7, "Dif. Goles": 1},
        {"Team": "Marseille", "Pts": 6, "Dif. Goles": -1},
        {"Team": "Newcastle United", "Pts": 5, "Dif. Goles": -2},
        {"Team": "Eintracht Frankfurt", "Pts": 4, "Dif. Goles": -3},
        {"Team": "Chelsea", "Pts": 4, "Dif. Goles": -2},
        {"Team": "Tottenham Hotspur", "Pts": 3, "Dif. Goles": -4},
        {"Team": "Atalanta", "Pts": 2, "Dif. Goles": -5},
        {"Team": "Galatasaray", "Pts": 1, "Dif. Goles": -6}
    ]
    return pd.DataFrame(data)

# --------------------------
# CÁLCULO RANKING POR PERSONA
# --------------------------
def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> Tuple[pd.DataFrame, List[str]]:
    official_names = list(standings_df["Team"].astype(str))
    lookup = {team: int(standings_df.loc[standings_df['Team'] == team, 'Pts'].values[0]) for team in official_names}
    rows, corrections = [], []

    for jugador, equipos in jugadores.items():
        eq1, eq2 = equipos
        found = []
        for eq in [eq1, eq2]:
            posibles = [eq] + ALIASES.get(eq, [])
            best, score = None, 1
            for p in posibles:
                candidate, s = best_match(p, official_names)
                if s > score:
                    best, score = candidate, s
            pts = lookup.get(best, 1) if best else 1
            detalle = f"{best}: {pts} pts" if best else f"{eq}: ❌"
            found.append((detalle, pts))
            if best and score < 100:
                corrections.append(f"'{eq}' → '{best}' ({score}%)")
            elif not best:
                corrections.append(f"No encontrado: {eq}")

        total = found[0][1] + found[1][1]
        rows.append({
            "Jugador": jugador,
            "Equipo 1": found[0][0],
            "Equipo 2": found[1][0],
            "Total Pts": total
        })

    df = pd.DataFrame(rows).sort_values("Total Pts", ascending=False).reset_index(drop=True)
    return df, corrections

# --------------------------
# INTERFAZ STREAMLIT
# --------------------------
def run_streamlit(standings_df: pd.DataFrame, ranking_df: pd.DataFrame, corrections: List[str]) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="🏆", layout="wide")
    st.markdown("<h1 style='margin-bottom:0.2rem;'>🏆 Polla Champions League — Puntajes en vivo</h1>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📋 Tabla de posiciones (equipos)")
        st.dataframe(standings_df.sort_values(["Pts", "Dif. Goles"], ascending=[False, False]).reset_index(drop=True), use_container_width=True)
    with col2:
        st.subheader("🏅 Ranking de la polla (por persona)")
        st.dataframe(ranking_df, use_container_width=True)

   # if corrections:
   #     st.markdown("---")
   #     st.subheader("🛠️ Ajustes automáticos / Avisos")
   #     for c in corrections:
   #         st.write("• " + c)

# --------------------------
# MAIN
# --------------------------
def main():
    global API_KEY
    standings_df, corrections = None, []
    try:
        standings_df = obtener_standings_api(API_KEY) if API_KEY else ejemplo_standings()
    except Exception as e:
        print(f"Error API: {e}")
        standings_df = ejemplo_standings()

    # Filtrar solo los equipos elegidos
    equipos_elegidos = sorted({e for lista in JUGADORES.values() for e in lista})
    oficiales = standings_df["Team"].tolist()
    equipos_filtrados = []

    for e in equipos_elegidos:
        posibles = [e] + ALIASES.get(e, [])
        match, score = None, 0
        for p in posibles:
            candidate, s = best_match(p, oficiales)
            if s > score:
                match, score = candidate, s
        if match and score > 55:
            equipos_filtrados.append(match)

    standings_df = standings_df[standings_df["Team"].isin(equipos_filtrados)].reset_index(drop=True)

    ranking_df, corrections = calcular_ranking(standings_df, JUGADORES)

    if USE_STREAMLIT and st is not None:
        run_streamlit(standings_df, ranking_df, corrections)
    else:
        print(ranking_df)

if __name__ == "__main__":
    main()
