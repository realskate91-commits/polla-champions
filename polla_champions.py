"""
Polla Champions - versión combinada (equipos + ranking por persona)
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
# Si prefieres, guarda tu API Key en Streamlit secrets: .streamlit/secrets.toml
# [football_data]
# api_key = "TU_API_KEY_AQUI"
#
# Si no usas secrets, reemplaza la variable API_KEY aquí (no recomendado en producción).
API_KEY = None
if USE_STREAMLIT and st is not None:
    API_KEY = st.secrets["football_data"]["api_key"] if "football_data" in st.secrets and "api_key" in st.secrets["football_data"] else None
# fallback: si prefieres, puedes poner la clave aquí (no recomendable):
# API_KEY = "TU_API_KEY_AQUI"

COMPETITION_ID = "2001"  # Champions League (football-data.org v4 uses id 2001)

# Participantes y equipos (ajusta si quieres)
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

# --------------------------
# UTILIDADES
# --------------------------
def norm(s: str) -> str:
    return re.sub(r"\W+", "", s).lower() if isinstance(s, str) else ""

def best_match(name: str, choices: List[str], cutoff: int = 70) -> Tuple[Optional[str], int]:
    """Devuelve (mejor_coincidencia, score) usando rapidfuzz o matching simple."""
    if process is None:
        # fallback simple: substring matching
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
    # 'standings' puede contener grupos; iteramos todas
    for group in data.get("standings", []):
        for entry in group.get("table", []):
            team_name = entry["team"]["name"]
            pts = entry.get("points", 0)
            rows.append({"Team": team_name, "Pts": int(pts)})
    df = pd.DataFrame(rows).drop_duplicates(subset=["Team"]).reset_index(drop=True)
    return df

# --------------------------
# FALLBACK: datos de ejemplo
# --------------------------
def ejemplo_standings() -> pd.DataFrame:
    data = [
        {"Team": "Manchester City", "Pts": 13},
        {"Team": "Paris Saint-Germain", "Pts": 12},
        {"Team": "Real Madrid", "Pts": 12},
        {"Team": "Bayern München", "Pts": 11},
        {"Team": "Arsenal", "Pts": 11},
        {"Team": "Napoli", "Pts": 10},
        {"Team": "Borussia Dortmund", "Pts": 10},
        {"Team": "Liverpool", "Pts": 10},
        {"Team": "Inter", "Pts": 9},
        {"Team": "Benfica", "Pts": 9},
        {"Team": "Atlético de Madrid", "Pts": 8},
        {"Team": "Barcelona", "Pts": 8},
        {"Team": "Juventus", "Pts": 7},
        {"Team": "Marseille", "Pts": 6},
        {"Team": "Newcastle United", "Pts": 5},
        {"Team": "Eintracht Frankfurt", "Pts": 4},
        {"Team": "Chelsea", "Pts": 4},
        {"Team": "Tottenham Hotspur", "Pts": 3},
        {"Team": "Atalanta", "Pts": 2},
        {"Team": "Galatasaray", "Pts": 1}
    ]
    return pd.DataFrame(data)

# --------------------------
# CALCULO RANKING POR PERSONA
# --------------------------
def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> Tuple[pd.DataFrame, List[str]]:
    official_names = list(standings_df["Team"].astype(str))
    lookup = {team: int(standings_df.loc[standings_df['Team'] == team, 'Pts'].values[0]) for team in official_names}
    rows = []
    corrections = []
    for jugador, equipos in jugadores.items():
        eq1, eq2 = equipos[0], equipos[1] if len(equipos) > 1 else (equipos[0] if equipos else "")
        # buscar cada equipo con fuzzy matching
        found1, score1 = best_match(eq1, official_names)
        found2, score2 = best_match(eq2, official_names)
        pts1 = lookup.get(found1, None) if found1 else None
        pts2 = lookup.get(found2, None) if found2 else None

        # construir detalles y registro
        detalle1 = f"{found1}: {pts1} pts" if found1 else f"{eq1}: ❌"
        detalle2 = f"{found2}: {pts2} pts" if found2 else f"{eq2}: ❌"

        if found1 and score1 < 100:
            corrections.append(f"Corrección: '{eq1}' → '{found1}' ({score1}%)")
        if found2 and score2 < 100:
            corrections.append(f"Corrección: '{eq2}' → '{found2}' ({score2}%)")
        if (not found1) and (not any(norm(eq1) in norm(t) for t in official_names)):
            corrections.append(f"No encontrado: '{eq1}'")
        if (not found2) and (not any(norm(eq2) in norm(t) for t in official_names)):
            corrections.append(f"No encontrado: '{eq2}'")

        total = (int(pts1) if pts1 is not None else 0) + (int(pts2) if pts2 is not None else 0)
        rows.append({
            "Jugador": jugador,
            "Equipo 1": detalle1,
            "Equipo 2": detalle2,
            "Total Pts": total
        })
    df = pd.DataFrame(rows).sort_values("Total Pts", ascending=False).reset_index(drop=True)
    return df, corrections

# --------------------------
# INTERFAZ STREAMLIT + CONSOLA
# --------------------------
def run_streamlit(standings_df: pd.DataFrame, ranking_df: pd.DataFrame, corrections: List[str]) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="🏆", layout="wide")
    st.markdown("<h1 style='margin-bottom:0.2rem;'>🏆 Polla Champions League — Puntajes en vivo</h1>", unsafe_allow_html=True)
    st.markdown("Fuente de datos: Football-Data.org / UEFA")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📋 Tabla de posiciones (equipos)")
        st.dataframe(standings_df.sort_values("Pts", ascending=False).reset_index(drop=True), use_container_width=True)
    with col2:
        st.subheader("ℹ️ Resumen")
        st.markdown(f"- Fuente: **Football-Data.org** (Competición ID {COMPETITION_ID})")
        st.markdown("- Si algún equipo aparece con ❌ es porque no se encontró una coincidencia confiable.")
        st.markdown("- Si necesitas ajustar nombres, edita la lista `JUGADORES` en el código.")

    st.markdown("---")
    st.subheader("🏅 Ranking de la polla (por persona)")
    st.dataframe(ranking_df, use_container_width=True)

    if corrections:
        st.markdown("---")
        st.subheader("🛠️ Ajustes automáticos / Avisos")
        for c in corrections:
            st.write("• " + c)

    st.markdown("---")
    st.caption("Hecho con ❤️ — recuerda respetar límites de la API (rate limits).")

def run_console(standings_df: pd.DataFrame, ranking_df: pd.DataFrame, corrections: List[str]) -> None:
    print("Polla Champions - Standings (equipos):")
    print(standings_df.sort_values("Pts", ascending=False).to_string(index=False))
    print("\nRanking por persona:")
    print(ranking_df.to_string(index=False))
    if corrections:
        print("\nAjustes / avisos:")
        for c in corrections:
            print("-", c)
    ranking_df.to_csv("ranking.csv", index=False)
    print("\nGuardado ranking.csv")

# --------------------------
# MAIN
# --------------------------
def main():
    # validar API key
    global API_KEY
    if not API_KEY:
        print("Advertencia: no se encontró API_KEY configurada. Usa Streamlit secrets o asigna API_KEY en el fichero.")
    standings_df = None
    corrections = []
    try:
        if API_KEY:
            standings_df = obtener_standings_api(API_KEY)
        else:
            raise Exception("API key no configurada - usando fallback")
    except Exception as e:
        # fallback a ejemplo
        print(f"Advertencia: no fue posible obtener standings desde la API: {e}")
        standings_df = ejemplo_standings()

    ranking_df, corrections = calcular_ranking(standings_df, JUGADORES)

    # Filtrar la tabla de posiciones solo para los equipos elegidos por los jugadores
    equipos_elegidos = sorted({e for lista in JUGADORES.values() for e in lista})
    # Intentamos emparejar los nombres oficiales con fuzzy match
    equipos_filtrados = []
    for e in equipos_elegidos:
        match, score = best_match(e, standings_df["Team"].tolist())
        if match and score > 60:
            equipos_filtrados.append(match)

    standings_df = standings_df[standings_df["Team"].isin(equipos_filtrados)].reset_index(drop=True)

    if USE_STREAMLIT and st is not None:
        run_streamlit(standings_df, ranking_df, corrections)
    else:
        run_console(standings_df, ranking_df, corrections)

if __name__ == "__main__":
    main()
