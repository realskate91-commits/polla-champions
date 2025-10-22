"""
Polla Champions - Versión con datos reales desde la API Football-Data.org
"""

from typing import Dict, List
import sys
import requests
import pandas as pd

# Intentar importar streamlit; si no existe, seguimos en modo consola
USE_STREAMLIT = True
try:
    import streamlit as st
except Exception:
    st = None
    USE_STREAMLIT = False


# --- CONFIGURACIÓN ---
API_KEY = "b9bd06dcfcd84b9781783e84613c76f5"  # 👈 Pega aquí tu clave de football-data.org
COMPETITION_ID = "2001"  # Champions League

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


# --- FUNCIONES ---

def norm(s: str) -> str:
    """Normaliza nombre para comparación."""
    import re
    return re.sub(r"\W+", "", s).lower()


def obtener_tabla_uefa_api(api_key: str) -> pd.DataFrame:
    """Obtiene standings de la Champions desde la API oficial."""
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION_ID}/standings"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"Error {r.status_code}: {r.text}")

    data = r.json()
    rows = []
    for group in data.get("standings", []):
        for team in group.get("table", []):
            rows.append({
                "Team": team["team"]["name"],
                "Pts": team["points"]
            })
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Team"])
    return df


def calcular_ranking(standings_df: pd.DataFrame, jugadores: Dict[str, List[str]]) -> pd.DataFrame:
    lookup = {norm(row.Team): int(row.Pts) for _, row in standings_df.iterrows()}
    resultados = []
    for jugador, equipos in jugadores.items():
        total = 0
        detalles = []
        for eq in equipos:
            pts = lookup.get(norm(eq))
            if pts is None:
                detalles.append(f"{eq}: ❌")
            else:
                total += pts
                detalles.append(f"{eq}: {pts} pts")
        resultados.append({
            "Jugador": jugador,
            "Equipos": " | ".join(detalles),
            "Total Pts": total
        })
    return pd.DataFrame(resultados).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)


def run_streamlit_app(standings_df: pd.DataFrame, ranking_df: pd.DataFrame) -> None:
    st.set_page_config(page_title="Polla Champions", page_icon="⚽", layout="wide")
    st.title("⚽ Polla Millonaria - Champions League")
    st.markdown("Ranking actualizado automáticamente (fuente: Football-Data.org)")

    with st.expander("Tabla de posiciones actual (Champions)"):
        st.dataframe(standings_df.sort_values('Pts', ascending=False), use_container_width=True)

    st.subheader("Ranking de la polla 🏆")
    st.dataframe(ranking_df, use_container_width=True)

    st.caption("Fuente de datos: Football-Data.org / UEFA")


def run_console(standings_df: pd.DataFrame, ranking_df: pd.DataFrame) -> None:
    print("Standings actuales (Champions):")
    print(standings_df.sort_values('Pts', ascending=False).head(10).to_string(index=False))
    print("\nRanking de la polla:")
    print(ranking_df.to_string(index=False))
    ranking_df.to_csv("ranking.csv", index=False)
    print("\nRanking guardado en 'ranking.csv'")


# --- MAIN ---

def main():
    try:
        standings = obtener_tabla_uefa_api(API_KEY)
        source = "Football-Data.org"
    except Exception as e:
        print(f"❌ Error al obtener standings: {e}")
        sys.exit(1)

    ranking = calcular_ranking(standings, JUGADORES)

    if USE_STREAMLIT and st is not None:
        run_streamlit_app(standings, ranking)
    else:
        run_console(standings, ranking)


if __name__ == "__main__":
    main()
