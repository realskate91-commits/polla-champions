import streamlit as st
import pandas as pd
import requests
from rapidfuzz import process

st.title("🏆 Polla Champions League – Puntajes en vivo")

st.caption("Fuente de datos: Football-Data.org / UEFA")

# ======= CONFIGURACIÓN =======
API_URL = "https://api.football-data.org/v4/competitions/CL/standings"
API_KEY = st.secrets["FOOTBALL_DATA_API_KEY"] if "FOOTBALL_DATA_API_KEY" in st.secrets else "YOUR_API_KEY_HERE"

headers = {"X-Auth-Token": API_KEY}

# ======= DATOS DE LOS PARTICIPANTES =======
data = {
    "Jugador": [
        "Diego", "Renzo", "Carlos", "Daniela", "Bryan",
        "Andrés", "Nicolás", "Lina", "Felipe", "Giovany"
    ],
    "Equipos": [
        ["Borussia Dortmund", "Atalanta"],
        ["Barcelona", "Eintracht Frankfurt"],
        ["Bayern München", "Inter"],
        ["Napoli", "Paris Saint-Germain"],
        ["Marseille", "Newcastle United"],
        ["Atlético de Madrid", "Juventus"],
        ["Chelsea", "Tottenham Hotspur"],
        ["Manchester City", "Galatasaray"],
        ["Benfica", "Real Madrid"],
        ["Arsenal", "Liverpool"]
    ]
}

df = pd.DataFrame(data)

# ======= OBTENER CLASIFICACIÓN ACTUAL =======
resp = requests.get(API_URL, headers=headers)

if resp.status_code != 200:
    st.error("No se pudo obtener la información de la UEFA (verifica tu API key o el límite de uso).")
else:
    standings = resp.json()
    teams_info = {}
    corrections = []

    for group in standings["standings"]:
        for t in group["table"]:
            teams_info[t["team"]["name"]] = t["points"]

    # Lista real de nombres de equipos
    official_names = list(teams_info.keys())

    # ======= CALCULAR PUNTAJES =======
    total_points = []
    for _, row in df.iterrows():
        equipos = row["Equipos"]
        puntos = 0
        for team in equipos:
            if team in teams_info:
                puntos += teams_info[team]
            else:
                match, score, _ = process.extractOne(team, official_names)
                if score > 70:
                    puntos += teams_info[match]
                    corrections.append(f"🔹 '{team}' → '{match}' ({int(score)}%)")
                else:
                    corrections.append(f"⚠️ '{team}' no encontrado")
        total_points.append(puntos)

    df["Total Pts"] = total_points

    st.dataframe(df.sort_values("Total Pts", ascending=False), use_container_width=True)

    if corrections:
        st.subheader("🧩 Ajustes automáticos / Avisos")
        for c in corrections:
            st.write(c)
