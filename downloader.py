import os
import re
import subprocess
import threading
from collections.abc import Callable


# Código especial para distinguir una cancelación de un error real.
CODIGO_CANCELADO = -1

_proceso_actual: subprocess.Popen[str] | None = None
_proceso_lock = threading.Lock()
_cancelacion_solicitada = threading.Event()


def ejecutar_spotdl(
    enlace: str,
    carpeta: str,
    tipo_enlace: str,
    mostrar_linea: Callable[[str], None],
    actualizar_progreso: Callable[[float], None]
) -> int:
    """
    Ejecuta spotDL y transmite su salida a la interfaz.

    Devuelve:
    - 0 cuando la descarga termina correctamente.
    - CODIGO_CANCELADO cuando el usuario la cancela.
    - Otro código cuando spotDL termina con error.
    """
    global _proceso_actual

    _cancelacion_solicitada.clear()

    if tipo_enlace == "playlist":
        formato_salida = os.path.join(
            carpeta,
            "{list-name}",
            "{artists} - {title}.{output-ext}"
        )
    else:
        formato_salida = os.path.join(
            carpeta,
            "{artists} - {title}.{output-ext}"
        )

    comando = [
        "spotdl",
        enlace,
        "--output",
        formato_salida
    ]

    entorno = os.environ.copy()
    entorno["PYTHONUTF8"] = "1"
    entorno["PYTHONIOENCODING"] = "utf-8"
    entorno["NO_COLOR"] = "1"
    entorno["FORCE_COLOR"] = "0"

    opciones_proceso: dict[str, object] = {}

    # En Windows crea un grupo nuevo para poder finalizar spotDL y FFmpeg.
    if os.name == "nt":
        opciones_proceso["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones_proceso["start_new_session"] = True

    try:
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=entorno,
            bufsize=1,
            **opciones_proceso
        )

        with _proceso_lock:
            _proceso_actual = proceso

        if proceso.stdout is not None:
            for linea in proceso.stdout:
                if _cancelacion_solicitada.is_set():
                    break

                mostrar_linea(linea)
                porcentaje = extraer_porcentaje(linea)

                if porcentaje is not None:
                    actualizar_progreso(porcentaje)

        codigo_salida = proceso.wait()

        if _cancelacion_solicitada.is_set():
            return CODIGO_CANCELADO

        return codigo_salida

    except FileNotFoundError:
        mostrar_linea(
            "Error: spotDL no está instalado "
            "o no está disponible en PATH.\n"
        )
        return 1

    except Exception as error:
        if _cancelacion_solicitada.is_set():
            return CODIGO_CANCELADO

        mostrar_linea(
            f"Error inesperado al ejecutar spotDL: {error}\n"
        )
        return 1

    finally:
        with _proceso_lock:
            _proceso_actual = None


def cancelar_descarga() -> bool:
    """
    Cancela el proceso activo de spotDL y sus procesos hijos.

    Devuelve True si había una descarga activa; False en caso contrario.
    """
    _cancelacion_solicitada.set()

    with _proceso_lock:
        proceso = _proceso_actual

    if proceso is None or proceso.poll() is not None:
        return False

    try:
        if os.name == "nt":
            # /T incluye procesos hijos, como yt-dlp y FFmpeg.
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(proceso.pid),
                    "/T",
                    "/F"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        else:
            import signal
            os.killpg(os.getpgid(proceso.pid), signal.SIGTERM)

        return True

    except Exception:
        try:
            proceso.kill()
            return True
        except Exception:
            return False


def extraer_porcentaje(linea: str) -> float | None:
    """
    Busca el último porcentaje dentro de una línea.

    Ejemplos:
    25%   -> 0.25
    72.5% -> 0.725
    100%  -> 1.0
    """
    coincidencias = re.findall(
        r"(\d{1,3}(?:\.\d+)?)\s*%",
        linea
    )

    if not coincidencias:
        return None

    try:
        porcentaje = float(coincidencias[-1])
        porcentaje = max(0.0, min(porcentaje, 100.0))
        return porcentaje / 100

    except ValueError:
        return None