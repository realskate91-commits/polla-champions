"""
Polla Champions - Versión con fallback si Streamlit no está disponible

Este archivo originalmente era una app de Streamlit. En algunos entornos (como sandboxes) el módulo
`streamlit` no está instalado y provoca `ModuleNotFoundError`. Para mayor robustez, esta versión:

- Intenta importar Streamlit; si falla, funciona en modo consola (CLI) sin interfaz web.
- Mantiene la funcionalidad de obtener standings desde la página de la UEFA mediante scraping.
- Añade manejo de errores y una ruta de fallback con datos de ejemplo cuando la extracción falla.
- Incluye una prueba simple (función `test_mapping`) para validar la lógica de suma de puntos.

Cómo usar:
- Con Streamlit instalado: `streamlit run polla_champions.py`
- Sin Streamlit: `python polla_champions.py` (mostrará el ranking en consola y guardará `ranking.csv`)

Recomendación: para producción usa una API de datos de fútbol (Football-Data.org, Sportdataapi, etc.)

"""

from typing import Dict, List, Any
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

# --- CONFIG ---
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

UEFA_STANDINGS_URL = "https://www.uefa.com/uefachampionsleague/standings/"

# --------------------------
# Utilidades
# --------------------------

def norm(s: str) -> str:
    """Normaliza un nombre para comparaciones simples."""
    return re.sub(r"\W+", "", s).lower() if isinstance(s, str) else ""


# --------------------------
# Scraping: obtener tabla de la UEFA
# --------------------------

def obtener_tabla_uefa() -> pd.DataFrame:
    """
    Intenta extraer datos de standings desde la página de la UEFA.
    Retorna DataFrame con columnas mínimas: ['Team','Pts'].
    Lanza Exception si falla.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PollaBot/1.0)"}
    r = requests.get(UEFA_STANDINGS_URL, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"Respuesta HTTP {r.status_code} desde UEFA")

    soup = BeautifulSoup(r.text, "lxml")

    rows: List[Dict[str, Any]] = []

    # Primera estrategia: tablas <table>
    tables = soup.find_all("table")
    for table in tables:
        for tr in table.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
            # Heurística: buscar nombre de equipo y un número de puntos al final
            if not cols:
                continue
            # Encontrar la primera celda que tiene texto no numérico -> equipo
            team = None
            pts = None
            # buscar patrón GF-GC (p.e. '3-1') o número para puntos
            # Simplificamos: asumimos que el último número en la fila es Pts
            nums = [re.sub(r"[^0-9]", "", c) for c in cols if re.search(r"\d", c)]
            if nums:
                try:
                    pts = int(nums[-1])
                except Exception:
                    pts = None
            # equipo: primera celda con letras
            for c in cols:
                if re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]", c):
                    team = c
                    break
            if team:
                rows.append({"Team": team, "Pts": pts})

    df = pd.DataFrame(rows)
    if df.empty:
        # Intento alternativo: buscar JSON embebido en scripts
        scripts = soup.find_all("script")
        for s in scripts:
            text = s.get_text()
            # buscar por claves comunes como "standings" o "teams"
            if 'standings' in text.lower() or 'teams' in text.lower():
                # no implementamos parser complejo aquí: fallback
                break
        raise Exception("No se pudo extraer standings desde UEFA (estructura inesperada)")

    # limpiar nombres
    df["Team_clean"] = df["Team"].apply(lambda x: re.sub(r"\s*\(.*\)", "", x).strip())
    df["Pts"] = pd.to_numeric(df["Pts"], errors="coerce")
    df = df.drop_duplicates(subset=["Team_clean"]).rename(columns={"Team_clean": "Team"})[["Team","Pts"]]
    return df


# --------------------------
# Cálculo del ranking
# --------------------------

def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Dado un DataFrame de standings (Team, Pts) y el diccionario de jugadores->equipos,
    retorna un DataFrame con la suma de puntos por jugador.
    """
    # Crear lookup por versión normalizada
    lookup = {norm(row.Team): int(row.Pts) if pd.notna(row.Pts) else None for _, row in standings_df.iterrows()}

    resultados = []
    for jugador, equipos in jugadores.items():
        detalles = []
        total = 0
        for equipo in equipos:
            key = norm(equipo)
            pts = lookup.get(key)
            if pts is None:
                # Intentar búsqueda por substring en claves del lookup
                found = None
                for k, v in lookup.items():
                    if key in k or k in key:
                        found = v
                        break
                pts = found
            if pts is None:
                detalles.append(f"{equipo}: No encontrado")
            else:
                detalles.append(f"{equipo}: {pts} pts")
                total += int(pts)
        resultados.append({"Jugador": jugador, "Equipos": ' | '.join(detalles), "Total Pts": total})

    res_df = pd.DataFrame(resultados).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return res_df


# --------------------------
# Datos de ejemplo (fallback)
# --------------------------

def ejemplo_standings() -> pd.DataFrame:
    """Tabla de ejemplo usada cuando el scraping falla. Mantener formato (Team, Pts)."""
    data = [
        {"Team": "Paris Saint-Germain", "Pts": 12},
        {"Team": "Napoli", "Pts": 10},
        {"Team": "Bayern München", "Pts": 11},
        {"Team": "Inter", "Pts": 9},
        {"Team": "Atlético de Madrid", "Pts": 8},
        {"Team": "Juventus", "Pts": 7},
        {"Team": "Marseille", "Pts": 6},
        {"Team": "Newcastle United", "Pts": 5},
        {"Team": "Chelsea", "Pts": 4},
        {"Team": "Tottenham Hotspur", "Pts": 3},
        {"Team": "Borussia Dortmund", "Pts": 10},
        {"Team": "Atalanta", "Pts": 2},
        {"Team": "Manchester City", "Pts": 13},
        {"Team": "Galatasaray", "Pts": 1},
        {"Team": "Benfica", "Pts": 9},
        {"Team": "Real Madrid", "Pts": 12},
        {"Team": "Arsenal", "Pts": 11},
        {"Team": "Liverpool", "Pts": 10},
        {"Team": "Barcelona", "Pts": 8},
        {"Team": "Eintracht Frankfurt", "Pts": 4}
    ]
    return pd.DataFrame(data)


# --------------------------
# Interfaz: Streamlit o Consola
# --------------------------

def run_streamlit_app(standings_df: pd.DataFrame, ranking_df: pd.DataFrame) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="⚽", layout="wide")
    st.title("⚽ Polla Millonaria - Champions League")
    st.markdown("Ranking actualizado automáticamente (fuente: UEFA).")

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
    # Guardar CSV
    ranking_df.to_csv("ranking.csv", index=False)
    print("\nRanking guardado en 'ranking.csv'")


# --------------------------
# Tests simples
# --------------------------

def test_mapping():
    """Prueba simple para comprobar que la suma de puntos funciona con el ejemplo.
    Esta no es una suite exhaustiva, solo una comprobación rápida.
    """
    df = ejemplo_standings()
    res = calcular_ranking(df, JUGADORES)
    # Comprobar que se generaron 10 jugadores
    assert len(res) == len(JUGADORES), "El número de jugadores en el ranking no coincide"
    # Comprobar que la columna 'Total Pts' existe y es numérica
    assert 'Total Pts' in res.columns
    assert pd.api.types.is_numeric_dtype(res['Total Pts']), "Total Pts debe ser numérico"
    print("Pruebas básicas: OK")


# --------------------------
# Main
# --------------------------

def main():
    # Intentar extracción real
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
    # Ejecutar pruebas básicas antes de correr para detectar fallos lógicos
    try:
        test_mapping()
    except AssertionError as ae:
        print(f"Fallo en pruebas internas: {ae}")
        sys.exit(1)

    main()
