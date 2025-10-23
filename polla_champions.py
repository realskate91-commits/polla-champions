"""
Polla Champions - versión final
- Página única: Tabla de posiciones (solo equipos elegidos) + Puntajes por persona
- Orden UEFA: Pts -> Dif. Goles -> GF
- Usa football-data.org (api_key en st.secrets["football_data"]["api_key"])
- Usa rapidfuzz para matching tolerante (si está disponible)
"""

from typing import Dict, List, Tuple, Optional
import re
import requests
import pandas as pd

import streamlit as st

# rapidfuzz para fuzzy matching (opcional)
try:
    from rapidfuzz import process, fuzz
except Exception:
    process = None
    fuzz = None

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="Polla Champions League", page_icon="🏆", layout="wide")

# API key desde Streamlit secrets
API_KEY = None
if "football_data" in st.secrets and "api_key" in st.secrets["football_data"]:
    API_KEY = st.secrets["football_data"]["api_key"]

COMPETITION_ID = "2001"  # Champions League

# Equipos elegidos (los 20 que me diste)
EQUIPOS_ELEGIDOS = [
    "Borussia Dortmund", "Atalanta", "Barcelona", "Eintracht Frankfurt",
    "Bayern München", "Inter", "Napoli", "Paris Saint-Germain",
    "Marseille", "Newcastle United", "Atlético de Madrid", "Juventus",
    "Chelsea", "Tottenham Hotspur", "Manchester City", "Galatasaray",
    "Benfica", "Real Madrid", "Arsenal", "Liverpool"
]

# Participantes y sus dos equipos (mantengo tu lista original)
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

def best_match(name: str, choices: List[str]) -> Tuple[Optional[str], int]:
    """Mejor coincidencia: usa rapidfuzz si está, si no hace substring matching."""
    if process is None:
        n = norm(name)
        for c in choices:
            if n == norm(c):
                return c, 100
            if n in norm(c) or norm(c) in n:
                return c, 90
        return None, 0
    match = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
    if match:
        candidate, score, _ = match
        return candidate, int(score)
    return None, 0

# --------------------------
# OBTENER STANDINGS (API)
# --------------------------
@st.cache_data(ttl=300)
def obtener_standings_api(api_key: str) -> pd.DataFrame:
    """Obtiene tabla completa (Team, PJ, PG, PE, PP, GF, GC, GD, Pts) desde football-data.org"""
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION_ID}/standings"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text}")
    data = r.json()
    rows = []
    for group in data.get("standings", []):
        group_name = group.get("group", "")
        for entry in group.get("table", []):
            t = entry["team"]
            rows.append({
                "Grupo": group_name,
                "Team": t["name"],
                "PJ": entry.get("playedGames", 0),
                "PG": entry.get("won", 0),
                "PE": entry.get("draw", 0),
                "PP": entry.get("lost", 0),
                "GF": entry.get("goalsFor", 0),
                "GC": entry.get("goalsAgainst", 0),
                "Dif. Goles": entry.get("goalDifference", 0),
                "Pts": entry.get("points", 0)
            })
    df = pd.DataFrame(rows).drop_duplicates(subset=["Team"]).reset_index(drop=True)
    return df

# --------------------------
# FALLBACK: ejemplo (cuando API falla)
# --------------------------
def ejemplo_standings_full() -> pd.DataFrame:
    """Fallback: crea filas mínimas con columnas completas para los equipos elegidos (0s)."""
    rows = []
    for team in EQUIPOS_ELEGIDOS:
        rows.append({
            "Grupo": "",
            "Team": team,
            "PJ": 0,
            "PG": 0,
            "PE": 0,
            "PP": 0,
            "GF": 0,
            "GC": 0,
            "Dif. Goles": 0,
            "Pts": 0
        })
    return pd.DataFrame(rows)

# --------------------------
# PREPARAR TABLA FILTRADA (garantiza que aparezcan todos los elegidos)
# --------------------------
def preparar_tabla_mostrada(standings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Toma el DataFrame obtenido de la API y:
    - Mapea/normaliza los nombres devueltos por la API hacia los nombres de EQUIPOS_ELEGIDOS
      usando best_match (para que la tabla muestre los nombres elegidos).
    - Añade filas con ceros para equipos elegidos que no aparezcan en la API.
    - Ordena por Pts -> Dif. Goles -> GF.
    """
    # Lista oficial que devolvió la API
    official = standings_df["Team"].tolist() if not standings_df.empty else []

    # Resultado intermedio por equipo elegido
    filas = []
    for chosen in EQUIPOS_ELEGIDOS:
        match_name, score = best_match(chosen, official)
        if match_name and score >= 60:
            # usar fila oficial pero renombrar la columna 'Team' a chosen para mostrar como tú lo pusiste
            row = standings_df[standings_df["Team"] == match_name].iloc[0].to_dict()
            # reemplazamos Team por chosen (mantenerás la etiqueta que esperas)
            row["Team"] = chosen
            filas.append(row)
        else:
            # no encontrado (agregamos fila vacía con ceros)
            filas.append({
                "Grupo": "",
                "Team": chosen,
                "PJ": 0,
                "PG": 0,
                "PE": 0,
                "PP": 0,
                "GF": 0,
                "GC": 0,
                "Dif. Goles": 0,
                "Pts": 0
            })

    df = pd.DataFrame(filas)
    # ordenar por Pts, Dif. Goles, GF desc
    df = df.sort_values(by=["Pts", "Dif. Goles", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    return df

# --------------------------
# CALCULAR RANKING POR JUGADOR
# --------------------------
def calcular_ranking_por_jugador(tabla_mostrada: pd.DataFrame, jugadores: Dict[str, List[str]]) -> pd.DataFrame:
    # build lookup por el nombre mostrado (Team = chosen name)
    lookup = {row["Team"]: int(row["Pts"]) for _, row in tabla_mostrada.iterrows()}
    rows = []
    for jugador, equipos in jugadores.items():
        detalles = []
        total = 0
        for eq in equipos:
            pts = lookup.get(eq, 0)
            detalles.append(f"{eq}: {pts} pts")
            total += int(pts)
        rows.append({"Jugador": jugador, "Equipos": " | ".join(detalles), "Total Pts": total})
    df = pd.DataFrame(rows).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return df

# --------------------------
# STREAMLIT UI (única página)
# --------------------------
def main():
    st.title("🏆 Polla Champions League — Puntajes en vivo")
    st.caption("Fuente: football-data.org (UEFA standings). Orden: Pts → Dif. Goles → GF")

    # intentar obtener de la API; si falla, usaremos fallback
    try:
        if not API_KEY:
            raise Exception("API key no configurada.")
        raw_df = obtener_standings_api(API_KEY)
    except Exception as e:
        st.warning(f"No se pudieron obtener standings desde la API: {e} — usando fallback con ceros.")
        raw_df = ejemplo_standings_full()

    # preparar tabla que se mostrará (garantiza todos los elegidos)
    tabla_mostrada = preparar_tabla_mostrada(raw_df)

    # mostrar tabla de posiciones (solo equipos elegidos)
    st.subheader("📋 Tabla de posiciones (equipos elegidos)")
    st.dataframe(tabla_mostrada, use_container_width=True)

    # calcular y mostrar ranking por persona
    ranking_df = calcular_ranking_por_jugador(tabla_mostrada, JUGADORES)
    st.subheader("👥 Puntajes por jugador")
    st.dataframe(ranking_df, use_container_width=True)

if __name__ == "__main__":
    main()
