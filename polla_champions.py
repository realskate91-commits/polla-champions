"""
Polla Champions - versión combinada (equipos + ranking por persona)
Requiere: streamlit, pandas, requests, rapidfuzz
"""

from typing import Dict, List, Tuple, Optional
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
    API_KEY = (
        st.secrets["football_data"]["api_key"]
        if "football_data" in st.secrets
        and "api_key" in st.secrets["football_data"]
        else None
    )

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
    "Renzo": ["Barcelona", "Eintracht Frankfurt"],
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
# OBTENER STANDINGS vía API (mejorado con diagnóstico)
# --------------------------
def obtener_standings_api(api_key: str) -> pd.DataFrame:
    """
    Versión de diagnóstico:
      - Imprime headers HTTP
      - Muestra la estructura 'standings' devuelta por la API
      - Prioriza standings de tipo 'TOTAL' si existen
      - Si no, concatena todas las 'table' encontradas en cualquier standing
    """
    if not api_key:
        raise Exception("No se ha configurado la API key. Verifica tu archivo secrets.toml o asigna la clave directamente.")

    url = f"https://api.football-data.org/v4/competitions/{COMPETITION_ID}/standings"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers, timeout=20)

    # --- DIAGNÓSTICO BÁSICO ---
    print("📡 Consultando API Football-Data... Estado HTTP:", r.status_code)
    print("→ Encabezados relevantes:")
    for k in ["X-API-Version", "X-Authenticated-Client", "X-RequestCounter-Reset", "X-RequestsAvailable"]:
        if k in r.headers:
            print(f"   {k}: {r.headers.get(k)}")
    # Muestra los primeros 2000 chars de la respuesta (para no saturar)
    body_preview = r.text[:2000].replace("\n", " ")
    print("→ Preview respuesta (primeros 2000 chars):", body_preview[:1000])

    if r.status_code != 200:
        # si hay cuerpo JSON explicando el error, mostrarlo acotado
        try:
            err = r.json()
            print("❌ Cuerpo error (recortado):", str(err)[:1000])
        except Exception:
            print("❌ No hay JSON en la respuesta de error.")
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    data = r.json()

    # Mostrar estructura de 'standings' para diagnóstico
    standings_raw = data.get("standings")
    if standings_raw is None:
        print("⚠️ La respuesta NO contiene la clave 'standings'. Claves devueltas:", list(data.keys()))
        raise Exception("Respuesta sin 'standings'")

    print(f"ℹ️ 'standings' contiene {len(standings_raw)} entradas.")
    for i, s in enumerate(standings_raw):
        stype = s.get("type", "<sin tipo>")
        stage = s.get("stage", "<sin stage>")
        group = s.get("group", None)
        table_len = len(s.get("table", [])) if s.get("table") else 0
        print(f"  - entrada {i}: type={stype}, stage={stage}, group={group}, rows={table_len}")

    # 1) Intentar buscar el standing de tipo TOTAL (tabla agregada)
    total_candidates = [s for s in standings_raw if s.get("type", "").upper() == "TOTAL"]
    if total_candidates:
        print("🔎 Se encontró al menos un 'TOTAL' — usaremos la primera entrada TOTAL.")
        chosen = total_candidates[0]
        rows_src = chosen.get("table", [])
        rows = []
        for entry in rows_src:
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
        print(f"✅ Construida tabla desde 'TOTAL' con {len(df)} filas.")
        return df

    # 2) Si no hay 'TOTAL', aplanar todas las tablas (GROUP / HOME / AWAY)
    print("🔎 No se encontró 'TOTAL'. Se van a concatenar todas las 'table' disponibles (GROUP/HOME/AWAY).")
    rows_all = []
    for s in standings_raw:
        table = s.get("table", []) or []
        for entry in table:
            team_name = entry["team"]["name"]
            pts = entry.get("points", 0)
            gf = entry.get("goalsFor", 0)
            ga = entry.get("goalsAgainst", 0)
            diff = gf - ga
            rows_all.append({
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
    if not rows_all:
        print("⚠️ No se encontraron filas en ninguna 'table'. Contenido 'standings' (recortado):", str(standings_raw)[:2000])
        raise Exception("No se obtuvieron rows de standings")

    df_all = pd.DataFrame(rows_all).drop_duplicates(subset=["Team"]).reset_index(drop=True)
    print(f"✅ Construida tabla concatenada con {len(df_all)} filas (tras drop_duplicates).")
    return df_all

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
        {"Team": "Galatasaray", "Pts": 1, "Dif. Goles": -6},
    ]
    return pd.DataFrame(data)


# --------------------------
# CÁLCULO RANKING POR PERSONA
# --------------------------
def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> Tuple[pd.DataFrame, List[str]]:
    official_names = list(standings_df["Team"].astype(str))
    lookup = {
        team: int(standings_df.loc[standings_df["Team"] == team, "Pts"].values[0])
        for team in official_names
    }
    rows, corrections = [], []

    for jugador, equipos in jugadores.items():
        eq1, eq2 = equipos
        found = []
        for eq in [eq1, eq2]:
            posibles = [eq] + ALIASES.get(eq, [])
            best, score = None, 0
            for p in posibles:
                candidate, s = best_match(p, official_names)
                if s > score:
                    best, score = candidate, s
            pts = lookup.get(best, 0) if best else 0
            detalle = f"{best}: {pts} pts" if best else f"{eq}: ❌"
            found.append((detalle, pts))
            if best and score < 100:
                corrections.append(f"'{eq}' → '{best}' ({score}%)")
            elif not best:
                corrections.append(f"No encontrado: {eq}")

        total = found[0][1] + found[1][1]
        rows.append(
            {
                "Jugador": jugador,
                "Equipo 1": found[0][0],
                "Equipo 2": found[1][0],
                "Total Pts": total,
            }
        )

    df = pd.DataFrame(rows).sort_values("Total Pts", ascending=False).reset_index(drop=True)
    return df, corrections


# --------------------------
# INTERFAZ STREAMLIT
# --------------------------
def run_streamlit(standings_df: pd.DataFrame, ranking_df: pd.DataFrame, corrections: list) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="🏆", layout="wide")
    st.markdown("<h1 style='margin-bottom:0.2rem;'>🏆 Polla Champions League — Puntajes en vivo</h1>", unsafe_allow_html=True)

    standings_display = standings_df.copy().reset_index(drop=True)
    standings_display.insert(0, "#", range(1, len(standings_display) + 1))

    ranking_display = ranking_df.copy().reset_index(drop=True)
    ranking_display.insert(0, "#", range(1, len(ranking_display) + 1))

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📋 Tabla de posiciones (equipos)")
        st.dataframe(
            standings_display.sort_values(["Pts", "Dif. Goles"], ascending=[False, False]),
            use_container_width=True,
            height=400,
        )
    with col2:
        st.subheader("🏅 Ranking de la polla (por persona)")
        st.dataframe(
            ranking_display,
            use_container_width=True,
            height=400,
        )


# --------------------------
# MAIN (mejorado con avisos)
# --------------------------
def main():
    global API_KEY
    standings_df, corrections = None, []

    try:
        if not API_KEY:
            API_KEY = "TU_API_KEY_AQUI"  # Asigna tu clave manualmente si no usas secrets.toml
            print("⚠️ Usando API_KEY definida manualmente (modo consola).")

        standings_df = obtener_standings_api(API_KEY)
        usando_api = True
    except Exception as e:
        print(f"⚠️ No se pudieron obtener datos reales: {e}")
        standings_df = ejemplo_standings()
        usando_api = False

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

    standings_df = (
        standings_df[standings_df["Team"].isin(equipos_filtrados)]
        .reset_index(drop=True)
    )

    ranking_df, corrections = calcular_ranking(standings_df, JUGADORES)
    fuente = (
        "🌍 Datos en vivo desde Football-Data.org"
        if usando_api
        else "📊 Usando datos de ejemplo (sin conexión a API)"
    )
    print(fuente)

    if USE_STREAMLIT and st is not None:
        run_streamlit(standings_df, ranking_df, corrections)
    else:
        print(ranking_df)


if __name__ == "__main__":
    main()
