import os
import threading
import customtkinter as ctk

from PIL import Image
from pathlib import Path
from historial import guardar_descarga, cargar_historial
from config import cargar_configuracion, guardar_configuracion


from tkinter import filedialog, messagebox
from downloader import (
    CODIGO_CANCELADO,
    ejecutar_spotdl,
    cancelar_descarga as detener_spotdl
)
from power import (
    evitar_suspension,
    permitir_suspension
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"


class SpotifyDownloaderApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Spotify Downloader")
        self.geometry("700x665")
        self.resizable(False, False)

        icono = ASSETS_DIR / "icon.ico"
        if not icono.exists():
            icono = ASSETS_DIR / "icono.ico"
        if icono.exists():
            try:
                self.iconbitmap(str(icono))
            except (OSError, RuntimeError):
                pass

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        from tkinter import Menu
        barra_menu = Menu(self)
        
        self.menu_bar = Menu(self)
        self.config(menu=self.menu_bar)
        
        menu_archivo = Menu(self.menu_bar, tearoff=0)
        menu_archivo.add_command(
            label="📁 Abrir carpeta",
            command=self.abrir_carpeta
        )
        menu_archivo.add_separator()
        menu_archivo.add_command(
            label="🚪 Salir",
            command=self.destroy
        )
        
        barra_menu.add_cascade(
            label="Archivo",
            menu=menu_archivo
        )
        
        menu_ayuda = Menu(self.menu_bar, tearoff=0)
        menu_ayuda.add_command(
            label="ℹ️ Acerca de...",
            command=self.mostrar_acerca_de
        )
        barra_menu.add_cascade(
            label="Ayuda",
            menu=menu_ayuda
        )
        
        self.config(menu=barra_menu)
                        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=1, column=0, columnspan=2, pady=(10, 15))

        ruta_logo = ASSETS_DIR / "logo.png"
        self.logo = None
        if ruta_logo.exists():
            imagen_logo = Image.open(ASSETS_DIR / "logo.png")
            self.logo = ctk.CTkImage(
                light_image=imagen_logo,
                dark_image=imagen_logo,
                size=(96, 96)
            )
            ctk.CTkLabel(
                self.header_frame,
                image=self.logo,
                text=""
            ).pack()

        ctk.CTkLabel(
            self.header_frame,
            text="SpotDown",
            font=("Segoe UI", 28, "bold")
        ).pack(pady=(8,0))

        
        self.configuracion = cargar_configuracion()
        self.cancelacion_solicitada = False

        
        
        self.lbl_link = ctk.CTkLabel(
            self,
            text="Enlace de Spotify:"
        )

        self.lbl_link.grid(
            row=2,
            column=0,
            padx=20,
            sticky="w"
        )

        # Entrada enlace
        self.entrada_link = ctk.CTkEntry(
            self,
            width=500,
            placeholder_text="Pega aquí el enlace..."
        )

        self.entrada_link.grid(
            row=2,
            column=1,
            padx=20,
            pady=10
        )

        # Texto carpeta
        self.lbl_carpeta = ctk.CTkLabel(
            self,
            text="Carpeta destino:"
        )

        self.lbl_carpeta.grid(
            row=3,
            column=0,
            padx=20,
            pady=15,
            sticky="w"
        )
        
        
        # Entrada carpeta
        self.entrada_carpeta = ctk.CTkEntry(
            self,
            width=400
        )

        self.entrada_carpeta.grid(
            row=3,
            column=1,
            padx=(20, 5),
            sticky="w"
        )
        
        carpeta_guardada = self.configuracion.get("carpeta", "")

        if carpeta_guardada:
            self.entrada_carpeta.insert(
            0,
            carpeta_guardada
        )

        # Botón seleccionar carpeta
        self.btn_carpeta = ctk.CTkButton(
            self,
            text="Examinar",
            width=90,
            command=self.seleccionar_carpeta
        )

        self.btn_carpeta.grid(
            row=3,
            column=1,
            padx=(430, 20),
            sticky="ew"
        )

        # Botón descargar
        self.btn_descargar = ctk.CTkButton(
            self,
            text="⬇ Descargar",
            width=180,
            command=self.descargar
        )

        self.btn_descargar.grid(
            row=4,
            column=0,
            columnspan=2,
            pady=(30, 10)
        )

        # Botón cancelar descarga
        self.btn_cancelar = ctk.CTkButton(
            self,
            text="❌ Cancelar descarga",
            width=180,
            state="disabled",
            fg_color="#C62828",
            hover_color="#B71C1C",
            command=self.cancelar_descarga_actual
        )

        self.btn_cancelar.grid(
            row=5,
            column=0,
            columnspan=2,
            pady=(0, 10)
        )
        
        self.btn_historial = ctk.CTkButton(
            self,
            text="📜 Historial",
            width=180,
            command=self.mostrar_historial
        )

        self.btn_historial.grid(
            row=6,
            column=0,
            columnspan=2,
            pady=(0, 10)
        )

        # Botón abrir carpeta
        self.btn_abrir_carpeta = ctk.CTkButton(
            self,
            text="📁 Abrir carpeta",
            width=180,
            command=self.abrir_carpeta
        )

        self.btn_abrir_carpeta.grid(
            row=7,
            column=0,
            columnspan=2,
            pady=(0, 10)
        )
        
        self.barra_progreso = ctk.CTkProgressBar(
            self,
            width=400,
            mode="determinate"
        )
        
        self.barra_progreso.set(0)

        self.barra_progreso.grid(
            row=8,
            column=0,
            columnspan=2,
            pady=(5, 10)
        )
        
        self.lbl_progreso = ctk.CTkLabel(
            self,
            text="0%",
            font=("Arial", 13)
        )

        self.lbl_progreso.grid(
            row=9,
            column=0,
            columnspan=2,
            pady=(0, 5)
        )
        

        # Estado
        self.estado = ctk.CTkLabel(
            self,
            text="Estado: Esperando...",
            font=("Arial", 14)
        )

        self.estado.grid(
            row=10,
            column=0,
            columnspan=2,
            pady=10
        )

        # Registro
        self.registro = ctk.CTkTextbox(
            self,
            width=650,
            height=150
        )

        self.registro.grid(
            row=11,
            column=0,
            columnspan=2,
            padx=20,
            pady=(10, 20)
        )

        self.registro.insert(
            "end",
            "Programa listo.\n"
        )

        self.registro.configure(
            state="disabled"
        )
        
    def actualizar_barra_progreso(
        self,
        progreso: float
    ):
        self.after(
            0,
            lambda valor=progreso: 
            self.mostrar_progreso(valor)
        )
    def mostrar_progreso(
        self,
        progreso: float
    ):
        progreso = max(
            0.0,
            min(progreso, 1.0)
        )

        self.barra_progreso.set(progreso)

        porcentaje = int(progreso * 100)

        self.lbl_progreso.configure(
            text=f"{porcentaje}%"
        )

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory()

        if carpeta:
            self.entrada_carpeta.delete(
                0,
                "end"
            )

            self.entrada_carpeta.insert(
                0,
                carpeta
            )

            guardar_configuracion(carpeta)

    def abrir_carpeta(self):
        carpeta = self.entrada_carpeta.get().strip()

        if not carpeta:
            messagebox.showwarning(
                "Carpeta requerida",
                "Primero selecciona una carpeta."
            )
            return

        if not os.path.isdir(carpeta):
            messagebox.showerror(
                "Carpeta no encontrada",
                "La carpeta seleccionada ya no existe."
            )
            return

        os.startfile(carpeta)

    def agregar_registro(self, mensaje: str):
        self.registro.configure(
            state="normal"
        )

        self.registro.insert(
            "end",
            mensaje
        )

        self.registro.see("end")

        self.registro.configure(
            state="disabled"
        )    
        
    def obtener_archivos_audio(self, carpeta: str):
        extensiones_audio = {
            ".mp3",
            ".m4a",
            ".flac",
            ".wav",
            ".ogg",
            ".opus"
        }

        ruta = Path(carpeta)

        if not ruta.exists():
            return set()

        return {
            str(archivo.resolve())
            for archivo in ruta.rglob("*")
            if archivo.is_file()
            and archivo.suffix.lower() in extensiones_audio
        }
    
    def detectar_tipo_enlace(self, enlace: str) -> str:
        enlace = enlace.lower()

        if "/playlist/" in enlace:
            return "playlist"

        if "/album/" in enlace:
            return "álbum"

        if "/track/" in enlace:
            return "canción"

        return "enlace"
        
    def descargar(self):
        enlace = self.entrada_link.get().strip()
        carpeta = self.entrada_carpeta.get().strip()
        
        tipo_enlace = self.detectar_tipo_enlace(enlace)

        if not enlace:
            self.estado.configure(
                text="Estado: Falta el enlace."
            )

            messagebox.showwarning(
                "Enlace requerido",
                "Debes pegar un enlace de Spotify."
            )
            return

        if not carpeta:
            self.estado.configure(
                text="Estado: Falta seleccionar la carpeta."
            )

            messagebox.showwarning(
                "Carpeta requerida",
                "Debes seleccionar una carpeta de destino."
            )
            return
        
        self.enlace_actual = enlace
        self.carpeta_actual = carpeta
        
        self.tipo_enlace_actual = tipo_enlace
        
        self.archivos_antes = self.obtener_archivos_audio(
            carpeta
        )
        
        self.estado.configure(
            text=f"Estado: Preparando {tipo_enlace}..."
        )

        self.cancelacion_solicitada = False

        self.btn_descargar.configure(
            state="disabled",
            text="Descargando..."
        )

        self.btn_cancelar.configure(
            state="normal"
        )
        
        self.barra_progreso.set(0)

        self.lbl_progreso.configure(
            text="0%"
        )
        
        self.agregar_registro(
            f"\nIniciando descarga de {tipo_enlace}...\n"
        )

        evitar_suspension()
        
        hilo = threading.Thread(
            target=self.procesar_descarga,
            args=(enlace, carpeta),
            daemon=True
        )

        hilo.start()

    def procesar_descarga(
        self,
        enlace: str,
        carpeta: str
    ):
        self.after(
            0,
            lambda: self.estado.configure(
                text="Estado: Descargando..."
            )
        )

        codigo_salida = ejecutar_spotdl(
            enlace,
            carpeta,
            self.tipo_enlace_actual,
            self.enviar_linea_al_registro,
            self.actualizar_barra_progreso
        )
        
        if (
            codigo_salida == CODIGO_CANCELADO
            or self.cancelacion_solicitada
        ):
            self.after(
                0,
                self.descarga_cancelada
            )

        elif codigo_salida == 0:
            archivos_despues = self.obtener_archivos_audio(
                carpeta
            )

            archivos_nuevos = (
                archivos_despues - self.archivos_antes
            )

            canciones = sorted(
                Path(archivo).stem
                for archivo in archivos_nuevos
            )

            self.after(
                0,
                lambda nombres=canciones:
                self.descarga_exitosa(nombres)
            )
        else:
            self.after(
                0,
                self.descarga_fallida
            )

        self.after(
            0,
            self.finalizar_descarga
        )
     
    def cancelar_descarga_actual(self):
        if self.cancelacion_solicitada:
            return

        confirmar = messagebox.askyesno(
            "Cancelar descarga",
            "¿Seguro que deseas cancelar la descarga actual?"
        )

        if not confirmar:
            return

        self.cancelacion_solicitada = True

        self.btn_cancelar.configure(
            state="disabled",
            text="Cancelando..."
        )

        self.estado.configure(
            text="Estado: Cancelando descarga..."
        )

        self.agregar_registro(
            "\nCancelación solicitada por el usuario...\n"
        )

        detenido = detener_spotdl()

        if not detenido:
            self.agregar_registro(
                "El proceso ya había terminado.\n"
            )

    def descarga_cancelada(self):
        self.estado.configure(
            text="Estado: Descarga cancelada."
        )

        self.agregar_registro(
            "Descarga cancelada correctamente.\n"
        )

    def enviar_linea_al_registro(
        self,
        linea: str
    ):
        self.after(
            0,
            lambda texto=linea:
            self.agregar_registro(texto)
        )

    def finalizar_descarga(self):
        permitir_suspension()
        self.barra_progreso.stop()
        self.barra_progreso.set(0)

        self.lbl_progreso.configure(
            text="0%"
        )

        self.btn_descargar.configure(
            state="normal",
            text="⬇ Descargar"
        )

        self.btn_cancelar.configure(
            state="disabled",
            text="❌ Cancelar descarga"
        )

        self.cancelacion_solicitada = False
        
    def descarga_exitosa(
        self,
        canciones: list[str]
    ):
        guardado = guardar_descarga(
            self.enlace_actual,
            self.carpeta_actual,
            canciones
        )

        self.estado.configure(
            text="Estado: Descarga finalizada ✔"
        )

        if canciones:
            self.agregar_registro(
                "\nArchivos nuevos detectados:\n"
            )

            for cancion in canciones:
                self.agregar_registro(
                    f"• {cancion}\n"
                )
        else:
            self.agregar_registro(
                "\nNo se pudo identificar un archivo nuevo.\n"
            )

        if guardado:
            self.agregar_registro(
                "Descarga agregada al historial.\n"
            )
        else:
            self.agregar_registro(
                "No se pudo guardar el historial.\n"
            )

        cantidad = len(canciones)

        self.agregar_registro(
            f"\nTotal de archivos nuevos: {cantidad}\n"
        )
        
        if self.tipo_enlace_actual == "playlist":
            mensaje = (
                "La playlist terminó de descargarse.\n\n"
                f"Canciones nuevas descargadas: {cantidad}"
            )

        elif self.tipo_enlace_actual == "álbum":
            mensaje = (
                "El álbum terminó de descargarse.\n\n"
                f"Canciones nuevas descargadas: {cantidad}"
            )

        else:
            mensaje = "La canción se descargó correctamente." 
        
        messagebox.showinfo(
            "Descarga completada",
            mensaje
        )

    def descarga_fallida(self):
        self.estado.configure(
            text="Estado: Error durante la descarga ❌"
        )
        
        messagebox.showerror(
            "Error de descarga",
            "No se pudo completar la descarga.\n\n"
            "Revisa el registro para conocer el error."
        )

    def mostrar_historial(self):

        historial = cargar_historial()

        ventana = ctk.CTkToplevel(self)
        ventana.title("Historial")
        ventana.geometry("700x450")

        texto = ctk.CTkTextbox(
            ventana,
            width=650,
            height=380
        )

        texto.pack(
            padx=20,
            pady=20,
            fill="both",
            expand=True
        )

        if not historial:
            texto.insert(
                "end",
                "No hay descargas registradas."
            )
        else:

            for descarga in reversed(historial):

                texto.insert(
                    "end",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )

                texto.insert(
                    "end",
                    f"📅 Fecha\n"
                    f"{descarga.get('fecha', 'Sin fecha')}\n\n"
                )

                texto.insert(
                    "end",
                    f"🎵 Canción\n"
                    f"{descarga.get('cancion', 'Sin identificar')}\n\n"
                )

                texto.insert(
                    "end",
                    f"📂 Carpeta\n"
                    f"{descarga.get('carpeta', 'Sin carpeta')}\n\n"
                )

                texto.insert(
                    "end",
                    f"🔗 Enlace\n"
                    f"{descarga.get('enlace', 'Sin enlace')}\n\n"
        )

        texto.configure(
            state="disabled"
        )
    
    def mostrar_acerca_de(self):
        
        ventana = ctk.CTkToplevel(self)
        ventana.title("Acerca de Spotify Downloader")
        ventana.geometry("420x420")
        ventana.resizable(False, False)
        
        ctk.CTkLabel(
            ventana,
            text="Spotify Downloader",
            font=("Arial", 24, "bold")
        ).pack(
            pady=(20, 5))
        
        ctk.CTkLabel(
            ventana,
            text="Versión 1.0 beta",
            font=("Arial", 16)
        ).pack(
            pady=(0, 15))
        
        ctk.CTkLabel(
            ventana,
            text="Información",
            justify="left",
            wraplength=340,
            font=("Arial", 14, "bold")
        ).pack(padx=20, pady=(0, 20))
       
        informacion = (
            "Spotify Downloader es una aplicación de escritorio "
            "que permite descargar canciones, álbumes y playlists "
            "de Spotify de manera sencilla y rápida.\n\n"
            "Desarrollado por:\n"
            "Jonathan Pedro Torres Álvarez\n\n"
            "Interfaz gráfica:\n"
            "• CustomTkinter\n\n"
            "• Python 3.12\n"
            "• SpotDL \n"
            "Versión: 1.0 beta\n"
            "© 2026"
        )

        ctk.CTkLabel(
            ventana,
            text=informacion,
            justify="left",
            wraplength=360,
            font=("Arial", 13)
        ).pack(padx=25, pady=(0, 20))

        ctk.CTkButton(
            ventana,
            text="Cerrar",
            width=120,
            command=ventana.destroy
        ).pack(pady=(0, 20))

        ventana.transient(self)
        ventana.grab_set()
    
if __name__ == "__main__":
    app = SpotifyDownloaderApp()

    try:
        from splash import SplashScreen
        app.withdraw()
        SplashScreen(app)
    except (ImportError, AttributeError, OSError, RuntimeError) as error:
        print(f"No se pudo mostrar el splash: {error}")
        app.deiconify()

    app.mainloop()