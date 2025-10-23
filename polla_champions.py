import streamlit as st
import pandas as pd
import requests

# --------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------
st.set_page_config(page_title="Champions League Tracker", layout="wide")

API_KEY = st.secrets["API_KEY"] if "API_KEY" in st.secrets else "b9bd06dcfcd84b9781783e84613c76f5"

EQUIPOS_ELEGIDOS = [
    "Borussia Dortmund", "Atalanta", "Barcelona", "Eintracht Frankfurt",
    "Bayern München", "Inter", "Napoli", "Paris Saint-Germain", "Marseille",
    "Newcastle United", "Atlético de Madrid", "Juventus", "Chelsea",
    "Tottenham Hotspur", "Manchester City", "Galatasaray", "Benfica",
    "Real Madrid", "Arsenal", "Liverpool"
]

# --------------------------------------------------------
# FUNCIÓN: Obtener tabla de posiciones
# --------------------------------------------------------
@st.cache_data(ttl=3600)
def obtener_tabla_posiciones():
    url = "https://api.football-data.org/v4/competitions/CL/standings"
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error("No se pudo obtener la información de la Champions League.")
        return pd.DataFrame()

    data = response.json()

    equivalencias = {
        "Inter": "Internazionale Milano",
        "Bayern München": "FC Bayern München",
        "Paris Saint-Germain": "Paris Saint Germain FC",
        "Atlético de Madrid": "Club Atlético de Madrid",
        "Manchester City": "Manchester City FC",
        "Real Madrid": "Real Madrid CF",
        "Liverpool": "Liverpool FC",
        "Arsenal": "Arsenal FC",
        "Barcelona": "FC Barcelona",
        "Benfica": "SL Benfica",
        "Chelsea": "Chelsea FC",
        "Juventus": "Juventus FC",
        "Napoli": "SSC Napoli",
        "Tottenham Hotspur": "Tottenham Hotspur FC",
        "Marseille": "Olympique de Marseille",
        "Borussia Dortmund": "BV Borussia 09 Dortmund",
        "Galatasaray": "Galatasaray SK",
        "Newcastle United": "Newcastle United FC",
        "Eintracht Frankfurt": "Eintracht Frankfurt",
        "Atalanta": "Atalanta BC"
    }

    equipos = []
    for grupo in data["standings"]:
        for team in grupo["table"]:
            nombre_api = team["team"]["name"]
            for alias, oficial in equivalencias.items():
                if nombre_api == oficial and alias in EQUIPOS_ELEGIDOS:
                    equipos.append({
                        "Grupo": grupo["group"],
                        "Equipo": alias,
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
    df = df.sort_values(by=["Pts", "Dif. Goles", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    return df

# --------------------------------------------------------
# FUNCIÓN: Obtener puntajes por personas
# --------------------------------------------------------
def obtener_puntajes_usuarios(tabla_equipos):
    usuarios = {
        "Carlos": ["Real Madrid", "Inter", "PSG", "Liverpool", "Chelsea"],
        "Andrés": ["Barcelona", "Bayern München", "Arsenal", "Juventus", "Napoli"],
        "Laura": ["Manchester City", "Atalanta", "Benfica", "Tottenham Hotspur", "Galatasaray"],
        "Sofía": ["Atlético de Madrid", "Marseille", "Newcastle United", "Borussia Dortmund", "Eintracht Frankfurt"]
    }

    resultados = []
    for nombre, equipos in usuarios.items():
        df_usuario = tabla_equipos[tabla_equipos["Equipo"].isin(equipos)]
        total_puntos = df_usuario["Pts"].sum()
        resultados.append({
            "Usuario": nombre,
            "Total Pts": total_puntos
        })
    df_usuarios = pd.DataFrame(resultados).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
    return df_usuarios, usuarios

# --------------------------------------------------------
# INTERFAZ
# --------------------------------------------------------
st.title("🏆 Champions League Tracker")
st.caption("Actualizado automáticamente con datos de la UEFA (via football-data.org)")

tabla_equipos = obtener_tabla_posiciones()

if not tabla_equipos.empty:
    st.subheader("📊 Tabla de posiciones (Equipos)")
    st.dataframe(tabla_equipos, use_container_width=True)

    df_usuarios, usuarios = obtener_puntajes_usuarios(tabla_equipos)

    st.subheader("👥 Tabla de puntuaciones por persona")
    st.dataframe(df_usuarios, use_container_width=True)

    with st.expander("🔍 Ver equipos por persona"):
        for nombre, equipos in usuarios.items():
            st.markdown(f"**{nombre}** → {', '.join(equipos)}")
else:
    st.warning("Esperando datos de la UEFA...")
