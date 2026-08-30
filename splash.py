import sys
import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

import runtime_manager


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"


class SplashScreen(ctk.CTkToplevel):
    """Pantalla de inicio de SpotDown.

    Además de mostrarse mientras carga la interfaz, aquí se prepara
    (o actualiza) el entorno de spotDL/yt-dlp cuando la app corre
    empaquetada (.app), para que las descargas sigan funcionando
    aunque YouTube cambie algo desde la última vez que se instaló
    SpotDown.
    """

    def __init__(self, app: ctk.CTk, duration_ms: int = 1800):
        super().__init__(app)
        self.app = app
        self.duration_ms = duration_ms
        self.logo = None
        self._entorno_listo = False

        self.overrideredirect(True)
        self.geometry("420x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self._centrar()
        self._crear_interfaz()

        if getattr(sys, "frozen", False):
            # Solo la app empaquetada necesita el entorno gestionado;
            # en modo desarrollo se usa el Python/venv del propio VSC.
            hilo = threading.Thread(
                target=self._preparar_entorno,
                daemon=True
            )
            hilo.start()
        else:
            self._entorno_listo = True
            self.after(self.duration_ms, self._cerrar)

    def _preparar_entorno(self):
        listo = runtime_manager.asegurar_entorno(self._actualizar_estado)
        self._entorno_listo = listo
        # Aseguramos un mínimo de tiempo visible aunque la
        # preparación sea instantánea (entorno ya actualizado).
        self.after(self.duration_ms, self._cerrar)

    def _actualizar_estado(self, mensaje: str):
        self.after(
            0,
            lambda: self.lbl_estado.configure(text=mensaje)
        )

    def _centrar(self):
        self.update_idletasks()
        ancho = 420
        alto = 300
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _crear_interfaz(self):
        contenedor = ctk.CTkFrame(self, corner_radius=16)
        contenedor.pack(fill="both", expand=True, padx=8, pady=8)

        ruta_logo = ASSETS_DIR / "logo.png"
        if ruta_logo.exists():
            imagen = Image.open(ruta_logo)
            self.logo = ctk.CTkImage(
                light_image=imagen,
                dark_image=imagen,
                size=(105, 105),
            )
            ctk.CTkLabel(contenedor, image=self.logo, text="").pack(
                pady=(28, 8)
            )
        else:
            ctk.CTkLabel(
                contenedor,
                text="♫",
                font=("Segoe UI", 56, "bold"),
            ).pack(pady=(28, 8))

        ctk.CTkLabel(
            contenedor,
            text="SpotDown",
            font=("Segoe UI", 30, "bold"),
        ).pack()

        self.lbl_estado = ctk.CTkLabel(
            contenedor,
            text="Inicializando aplicación...",
            font=("Segoe UI", 13),
        )
        self.lbl_estado.pack(pady=(8, 16))

        progreso = ctk.CTkProgressBar(contenedor, width=280, mode="indeterminate")
        progreso.pack()
        progreso.start()
        self.progreso = progreso

    def _cerrar(self):
        self.progreso.stop()
        self.destroy()
        self.app.deiconify()
        self.app.lift()
        self.app.focus_force()

        if not self._entorno_listo:
            self.app.after(
                300,
                lambda: self.app.mostrar_error_entorno(
                    "No se pudo preparar spotDL/yt-dlp. Verifica tu "
                    "conexión a internet y que Python 3 esté instalado, "
                    "luego vuelve a abrir SpotDown."
                )
            )