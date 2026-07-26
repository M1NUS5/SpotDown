import json
import os
from datetime import datetime


ARCHIVO_HISTORIAL = "historial.json"


def cargar_historial():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return []

    try:
        with open(
            ARCHIVO_HISTORIAL,
            "r",
            encoding="utf-8"
        ) as archivo:
            datos = json.load(archivo)

            if isinstance(datos, list):
                return datos

            return []

    except (json.JSONDecodeError, OSError):
        return []


def guardar_descarga(
    enlace: str,
    carpeta: str,
    canciones: list[str]
):
    historial = cargar_historial()

    if not canciones:
        canciones = ["Canción sin identificar"]

    for cancion in canciones:
        nueva_descarga = {
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "cancion": cancion,
            "enlace": enlace,
            "carpeta": carpeta
        }

        historial.append(nueva_descarga)

    try:
        with open(
            ARCHIVO_HISTORIAL,
            "w",
            encoding="utf-8"
        ) as archivo:
            json.dump(
                historial,
                archivo,
                ensure_ascii=False,
                indent=4
            )

        return True

    except OSError:
        return False