import streamlit as st
import pandas as pd
import requests

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================

st.set_page_config(page_title="Polla Champions League", page_icon="🏆", layout="wide")

st.title("🏆 Polla Champions League – Puntajes en vivo")
st.caption("Fuente de datos: Football-Data.org / UEFA")

# 👉 Ingresa tu API Key de Football-Data.org aquí
API_KEY = "b9bd06dcfcd84b9781783e84613c76f5"

# Equipos seleccionados por cada jugador
JUGADORES = {
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


# ==============================
# FUNCIONES AUXILIARES
# ==============================

def obtener_tabla_uefa(api_key: str) -> pd.DataFrame:
    """Obtiene los standings actuales de la Champions desde la API."""
    url = "https://api.football-data.org/v4/competitions/CL/standings"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers, timeout=15)

    if r.status_code != 200:
        raise Exception(f"Error al consultar la API (HTTP {r.status_code})")

    data = r.json()
    rows = []

    for group in data["standings"]:
        for team in group["table"]:
            rows.append({
                "Grupo": group["group"].replace("GROUP_", ""),
                "Equipo": team["team"]["name"],
                "PJ": team["playedGames"],
                "PG": team["won"],
                "PE": team["draw"],
                "PP": team["lost"],
                "GF": team["goalsFor"],
                "GC": team["goalsAgainst"],
                "Dif. Goles": team["goalDifference"],
                "Pts": team["points"]
            })

    df = pd.DataFrame(rows)
    return df


def calcular_ranking(standings_df: pd.DataFrame, jugadores: dict) -> pd.DataFrame:
    """Calcula el puntaje total por jugador basado en los standings."""
    puntos = {row["Equipo"]: row["Pts"] for _, row in standings_df.iterrows()}

    ranking = []
    for jugador, equipos in jugadores.items():
        total = 0
        detalle = []
        for eq in equipos:
            pts = puntos.get(eq, 0)
            total += pts
            detalle.append(f"{eq}: {pts} pts")
        ranking.append({
            "Jugador": jugador,
            "Equipos": " | ".join(detalle),
            "Total Pts": total
        })

    df_ranking = pd.DataFrame(ranking).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return df_ranking


# ==============================
# MENÚ PRINCIPAL
# ==============================

st.sidebar.title("⚽ Menú principal")
seccion = st.sidebar.radio(
    "Selecciona una vista:",
    ["Tabla de posiciones (equipos)", "Puntajes por jugador"]
)


# ==============================
# SECCIÓN: TABLA DE POSICIONES
# ==============================

if seccion == "Tabla de posiciones (equipos)":
    st.header("🏆 Tabla de posiciones (equipos elegidos)")

    try:
        standings_df = obtener_tabla_uefa(API_KEY)

        # Filtrar solo equipos elegidos
        equipos_elegidos = sorted({e for lista in JUGADORES.values() for e in lista})
        standings_df = standings_df[standings_df["Equipo"].isin(equipos_elegidos)]

        # Ordenar por puntos y diferencia de goles
        standings_df = standings_df.sort_values(
            by=["Pts", "Dif. Goles"], ascending=False
        ).reset_index(drop=True)

        st.dataframe(standings_df, hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"No se pudo obtener la información de la UEFA (verifica tu API key o límite de uso).")
        st.caption(f"Detalles técnicos: {e}")


# ==============================
# SECCIÓN: PUNTAJES POR JUGADOR
# ==============================

elif seccion == "Puntajes por jugador":
    st.header("👤 Puntajes por jugador")

    try:
        standings_df = obtener_tabla_uefa(API_KEY)
        ranking_df = calcular_ranking(standings_df, JUGADORES)

        st.dataframe(ranking_df, hide_index=True, use_container_width=True)
        st.caption("Fuente de datos: Football-Data.org / UEFA")

    except Exception as e:
        st.error(f"No se pudo obtener la información de la UEFA (verifica tu API key o límite de uso).")
        st.caption(f"Detalles técnicos: {e}")
