import streamlit as st
import pandas as pd
import requests

# --------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------
API_KEY = "b9bd06dcfcd84b9781783e84613c76f5"  # ⚠️ Reemplaza con tu clave válida de football-data.org
USE_STREAMLIT = True

# Lista de equipos de tu polla
EQUIPOS_ELEGIDOS = [
    "Borussia Dortmund", "Atalanta", "Barcelona", "Eintracht Frankfurt",
    "Bayern München", "Inter", "Napoli", "Paris Saint-Germain",
    "Marseille", "Newcastle United", "Atlético de Madrid", "Juventus",
    "Chelsea", "Tottenham Hotspur", "Manchester City", "Galatasaray",
    "Benfica", "Real Madrid", "Arsenal", "Liverpool"
]

# --------------------------------------------------------
# FUNCIÓN: Obtener posiciones de la UEFA Champions
# --------------------------------------------------------
@st.cache_data(ttl=3600)
def obtener_tabla_posiciones():
    url = "https://api.football-data.org/v4/competitions/CL/standings"
    headers = {"X-Auth-Token": API_KEY}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None

    data = response.json()
    equipos = []
    for grupo in data["standings"]:
        for team in grupo["table"]:
            nombre = team["team"]["name"]
            if nombre in EQUIPOS_ELEGIDOS:
                equipos.append({
                    "Grupo": grupo["group"],
                    "Equipo": nombre,
                    "PJ": team["playedGames"],
                    "PG": team["won"],
                    "PE": team["draw"],
                    "PP": team["lost"],
                    "GF": team["goalsFor"],
                    "GC": team["goalsAgainst"],
                    "Dif. Goles": team["goalDifference"],
                    "Pts": team["points"]
                })

    df = pd.DataFrame(equipos)

    # Ordenar como UEFA
    df = df.sort_values(by=["Pts", "Dif. Goles", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    return df

# --------------------------------------------------------
# FUNCIÓN: Calcular puntos por jugador
# --------------------------------------------------------
def calcular_puntajes_jugadores(df_posiciones):
    jugadores_data = [
        {"Jugador": "Diego", "Equipos": ["Borussia Dortmund", "Atalanta"]},
        {"Jugador": "Renzo", "Equipos": ["Barcelona", "Eintracht Frankfurt"]},
        {"Jugador": "Carlos", "Equipos": ["Bayern München", "Inter"]},
        {"Jugador": "Daniela", "Equipos": ["Napoli", "Paris Saint-Germain"]},
        {"Jugador": "Bryan", "Equipos": ["Marseille", "Newcastle United"]},
        {"Jugador": "Andrés", "Equipos": ["Atlético de Madrid", "Juventus"]},
        {"Jugador": "Nicolás", "Equipos": ["Chelsea", "Tottenham Hotspur"]},
        {"Jugador": "Lina", "Equipos": ["Manchester City", "Galatasaray"]},
        {"Jugador": "Felipe", "Equipos": ["Benfica", "Real Madrid"]},
        {"Jugador": "Giovany", "Equipos": ["Arsenal", "Liverpool"]},
    ]

    resultados = []
    for jugador in jugadores_data:
        total_puntos = 0
        equipos_detalle = []
        for equipo in jugador["Equipos"]:
            fila = df_posiciones[df_posiciones["Equipo"] == equipo]
            if not fila.empty:
                pts = fila.iloc[0]["Pts"]
                total_puntos += pts
                equipos_detalle.append(f"{equipo}: {pts} pts")
            else:
                equipos_detalle.append(f"{equipo}: 0 pts ❌")

        resultados.append({
            "Jugador": jugador["Jugador"],
            "Equipos": " | ".join(equipos_detalle),
            "Total Pts": total_puntos
        })

    df_jugadores = pd.DataFrame(resultados)
    df_jugadores = df_jugadores.sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return df_jugadores

# --------------------------------------------------------
# INTERFAZ STREAMLIT
# --------------------------------------------------------
if USE_STREAMLIT:
    st.set_page_config(page_title="Polla Champions League", page_icon="🏆", layout="wide")

    st.title("🏆 Polla Champions League – Puntajes en vivo")
    st.caption("Fuente de datos: Football-Data.org / UEFA")

    df_posiciones = obtener_tabla_posiciones()
    if df_posiciones is None or df_posiciones.empty:
        st.error("No se pudo obtener la información de la UEFA (verifica tu API key o el límite de uso).")
    else:
        # Tabla de posiciones
        st.subheader("🏆 Tabla de posiciones (equipos elegidos)")
        st.dataframe(df_posiciones, use_container_width=True)

        # Tabla de jugadores
        st.subheader("👥 Puntajes por jugador")
        df_jugadores = calcular_puntajes_jugadores(df_posiciones)
        st.dataframe(df_jugadores, use_container_width=True)
