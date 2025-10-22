"""
Polla Champions - App Streamlit (nombres tal como aparecen en UEFA)

Descripción
-----------
Este archivo implementa una app que extrae los standings oficiales de la UEFA Champions League
(y sus puntos oficiales) y calcula un ranking entre participantes (cada participante tiene 2 equipos).

Uso:
- Con Streamlit instalado: `streamlit run polla_champions.py`
- Sin Streamlit: `python polla_champions.py` (imprime ranking en consola y genera ranking.csv)
"""

from typing import Dict, List, Any, Optional
import sys
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Intentar importar streamlit; si no existe, seguimos en modo consola
USE_STREAMLIT = True
try:
    import streamlit as st
except Exception:
    st = None
    USE_STREAMLIT = False

# --------------------------
# Config: jugadores (como antes)
# --------------------------
JUGADORES: Dict[str, List[str]] = {
    "Daniela": ["Napoli", "PSG"],
    "Carlos": ["Bayern", "Inter"],
    "Andrés": ["Atlético", "Juventus"],
    "Bryan": ["Marseille", "Newcastle"],
    "Nicolás": ["Chelsea", "Tottenham"],
    "Diego": ["Borussia", "Atalanta"],
    "Lina": ["Man City", "Galatasaray"],
    "Felipe": ["Benfica", "Real Madrid"],
    "Giovany": ["Arsenal", "Liverpool"],
    "Renzo": ["Barcelona", "Eintracht"]
}

UEFA_STANDINGS_URL = "https://www.uefa.com/uefachampionsleague/standings/"

# --------------------------
# Utilidades
# --------------------------
def norm(s: str) -> str:
    return re.sub(r"\W+", "", s).lower() if isinstance(s, str) else ""

def best_match_team(query: str, teams: List[str]) -> Optional[str]:
    """Busca la mejor coincidencia por substring (insensible) entre query y la lista teams.
    Retorna el nombre tal como aparece en teams o None si no encuentra.
    """
    q = norm(query)
    # coincidencias exactas (normalizadas)
    for t in teams:
        if norm(t) == q:
            return t
    # substring (query dentro de t)
    candidates = [t for t in teams if q in norm(t)]
    if candidates:
        # devuelve el más corto (heurística) para evitar coincidencias amplias
        return sorted(candidates, key=lambda x: len(x))[0]
    # substring inverso (t dentro de query)
    candidates = [t for t in teams if norm(t) in q]
    if candidates:
        return sorted(candidates, key=lambda x: len(x))[0]
    return None

# --------------------------
# Scraping: obtener tabla de la UEFA
# --------------------------
def obtener_tabla_uefa() -> pd.DataFrame:
    """
    Extrae el listado de equipos y puntos desde la página de standings de la UEFA.
    Retorna DataFrame con columnas ['Team','Pts'] usando el nombre tal cual aparece en UEFA.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PollaBot/1.0)"}
    r = requests.get(UEFA_STANDINGS_URL, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"Respuesta HTTP {r.status_code} desde UEFA")

    soup = BeautifulSoup(r.text, "lxml")

    teams_extracted: List[Dict[str, Any]] = []

    # Estrategia 1: buscar tablas <table> y extraer filas
    tables = soup.find_all("table")
    for table in tables:
        # cada fila tr representa una entrada (evitar headers)
        for tr in table.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
            if not cols:
                continue
            # heurística: el nombre del equipo suele estar en una celda con texto y puede contener letras
            team = None
            pts = None
            # identificar puntos: último número en la fila
            nums = [re.sub(r"[^0-9]", "", c) for c in cols if re.search(r"\d", c)]
            if nums:
                try:
                    pts = int(nums[-1])
                except Exception:
                    pts = None
            # encontrar texto con letras para equipo
            for c in cols:
                if re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]", c):
                    team = c
                    break
            if team:
                teams_extracted.append({"Team": team, "Pts": pts})

    # Si no extrajimos nada útil, intentar estrategia alternativa con bloques de divs (por si es JS-rendered)
    if not teams_extracted:
        # Buscar etiquetas que contengan "standings" dentro de scripts (no parseamos JSON complejo aquí)
        scripts = soup.find_all("script")
        for s in scripts:
            text = s.get_text()
            if 'standings' in text.lower() or 'teams' in text.lower():
                # no implementamos parser JSON complejo aquí; fallback
                break
        raise Exception("No se pudo extraer standings desde UEFA (estructura inesperada).")

    df = pd.DataFrame(teams_extracted)
    # Normalizar nombres (limpiar paréntesis) y tomar último valor numérico como puntos
    df["Team"] = df["Team"].apply(lambda x: re.sub(r"\s*\(.*\)", "", x).strip())
    df["Pts"] = pd.to_numeric(df["Pts"], errors="coerce")
    # eliminar duplicados manteniendo primera aparición
    df = df.drop_duplicates(subset=["Team"]).reset_index(drop=True)

    return df[["Team","Pts"]]

# --------------------------
# Cálculo del ranking
# --------------------------
def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> pd.DataFrame:
    teams = list(standings_df["Team"].astype(str))
    lookup = {team: int(standings_df.loc[standings_df['Team'] == team, 'Pts'].values[0]) if pd.notna(standings_df.loc[standings_df['Team'] == team, 'Pts'].values[0]) else 0 for team in teams}

    resultados = []
    for jugador, equipos in jugadores.items():
        detalles = []
        total = 0
        for equipo_query in equipos:
            match = best_match_team(equipo_query, teams)
            if match:
                pts = lookup.get(match, 0)
                detalles.append(f"{match}: {pts} pts")
                total += int(pts)
            else:
                detalles.append(f"{equipo_query}: No encontrado")
        resultados.append({"Jugador": jugador, "Equipos": ' | '.join(detalles), "Total Pts": total})

    res_df = pd.DataFrame(resultados).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return res_df

# --------------------------
# Fallback: datos de ejemplo
# --------------------------
def ejemplo_standings() -> pd.DataFrame:
    data = [
        {"Team": "Manchester City", "Pts": 13},
        {"Team": "Paris Saint-Germain", "Pts": 12},
        {"Team": "Real Madrid", "Pts": 12},
        {"Team": "Bayern", "Pts": 11},
        {"Team": "Arsenal", "Pts": 11},
        {"Team": "Napoli", "Pts": 10},
        {"Team": "Borussia Dortmund", "Pts": 10},
        {"Team": "Liverpool", "Pts": 10},
        {"Team": "Inter", "Pts": 9},
        {"Team": "Benfica", "Pts": 9},
        {"Team": "Atlético", "Pts": 8},
        {"Team": "Barcelona", "Pts": 8},
        {"Team": "Juventus", "Pts": 7},
        {"Team": "Marseille", "Pts": 6},
        {"Team": "Newcastle", "Pts": 5},
        {"Team": "Eintracht", "Pts": 4},
        {"Team": "Chelsea", "Pts": 4},
        {"Team": "Tottenham", "Pts": 3},
        {"Team": "Atalanta", "Pts": 2},
        {"Team": "Galatasaray", "Pts": 1}
    ]
    return pd.DataFrame(data)

# --------------------------
# Interfaz: Streamlit o Consola
# --------------------------
def run_streamlit_app(standings_df: pd.DataFrame, ranking_df: pd.DataFrame) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="⚽", layout="wide")
    st.title("⚽ Polla Millonaria - Champions League")
    st.markdown("Ranking actualizado con nombres tal como aparecen en UEFA.")

    with st.expander("Standings extraídos (UEFA)"):
        st.dataframe(standings_df.sort_values('Pts', ascending=False).reset_index(drop=True))

    st.markdown("---")
    st.subheader("Ranking de la polla")
    st.dataframe(ranking_df, use_container_width=True)

    st.markdown("---")
    st.caption("Fuente de datos: uefa.com")

def run_console(standings_df: pd.DataFrame, ranking_df: pd.DataFrame) -> None:
    print("Polla Champions - Modo consola")
    print("Standings (muestra):")
    print(standings_df.sort_values('Pts', ascending=False).head(10).to_string(index=False))
    print("\nRanking: ")
    print(ranking_df.to_string(index=False))
    ranking_df.to_csv("ranking.csv", index=False)
    print("\nRanking guardado en 'ranking.csv'")

# --------------------------
# Tests simples
# --------------------------
def test_mapping():
    df = ejemplo_standings()
    res = calcular_ranking(df, JUGADORES)
    assert len(res) == len(JUGADORES), "El número de jugadores en el ranking no coincide"
    assert 'Total Pts' in res.columns
    assert pd.api.types.is_numeric_dtype(res['Total Pts']), "Total Pts debe ser numérico"

# --------------------------
# Main
# --------------------------
def main():
    try:
        standings = obtener_tabla_uefa()
        source = 'UEFA (scrape)'
    except Exception as e:
        print(f"Advertencia: no fue posible obtener standings desde UEFA: {e}")
        print("Usando datos de ejemplo como fallback.")
        standings = ejemplo_standings()
        source = 'Ejemplo (fallback)'

    ranking = calcular_ranking(standings, JUGADORES)

    if USE_STREAMLIT and st is not None:
        run_streamlit_app(standings, ranking)
    else:
        run_console(standings, ranking)

if __name__ == '__main__':
    try:
        test_mapping()
    except AssertionError as ae:
        print(f"Fallo en pruebas internas: {ae}")
        sys.exit(1)
    main()
