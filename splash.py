from pathlib import Path

import customtkinter as ctk
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"


class SplashScreen(ctk.CTkToplevel):
    """Pantalla de inicio sencilla para SpotDown."""

    def __init__(self, app: ctk.CTk, duration_ms: int = 1800):
        super().__init__(app)
        self.app = app
        self.duration_ms = duration_ms
        self.logo = None

        self.overrideredirect(True)
        self.geometry("420x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self._centrar()
        self._crear_interfaz()
        self.after(self.duration_ms, self._cerrar)

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

        ctk.CTkLabel(
            contenedor,
            text="Inicializando aplicación...",
            font=("Segoe UI", 13),
        ).pack(pady=(8, 16))

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