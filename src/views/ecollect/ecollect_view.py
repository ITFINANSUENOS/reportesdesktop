import tkinter as tk
from tkinter import ttk

# MOTIVO: componentes visuales compartidos (consistencia entre módulos).
from src.views.widgets import add_scroll_area, card, file_field, action_button


class EcollectView(ttk.Frame):
    def __init__(self, parent, controller, main_window):
        super().__init__(parent)

        self.controller = controller
        self.main_window = main_window
        self.controller.set_view(self)

        # Claves de archivos (la lógica del controlador no cambia).
        self.file_paths = {
            "PROCESO_VENCIMIENTOS": tk.StringVar(value="No se han seleccionado archivos."),
            "PROCESO_CONSULTA": tk.StringVar(value="No se ha seleccionado un archivo."),
            "PROCESO_COLABORADORES": tk.StringVar(value="No se ha seleccionado un archivo."),
            "PROCESO_MAESTRO_CLIENTES": tk.StringVar(value="No se ha seleccionado un archivo."),
        }

        self._create_widgets()

    def _create_widgets(self):
        """Crea la estructura con el scroll estándar y tarjetas uniformes."""
        self.configure(style='TFrame')
        content = add_scroll_area(self)

        # --- Tarjeta 1: Proceso Clientes ---
        self._create_proceso_unificado_card(content)

        # --- Tarjeta 2: Proceso Colaboradores ---
        self._create_proceso_colaboradores_card(content)

    def _create_proceso_unificado_card(self, parent):
        """Tarjeta del proceso de E-Collect (CLIENTES)."""
        card_frame = card(parent, "Proceso 1: Generación de Planos Clientes")

        file_field(card_frame, "1. Archivo(s) de Vencimientos (.xlsx)",
                   self.file_paths["PROCESO_VENCIMIENTOS"],
                   lambda: self.controller.seleccionar_archivo("PROCESO_VENCIMIENTOS", True))
        file_field(card_frame, "2. Archivo de Ventas (.xlsx)",
                   self.file_paths["PROCESO_CONSULTA"],
                   lambda: self.controller.seleccionar_archivo("PROCESO_CONSULTA", False))
        file_field(card_frame, "3. Archivo de Usuarios cargados (.xlsx)",
                   self.file_paths["PROCESO_MAESTRO_CLIENTES"],
                   lambda: self.controller.seleccionar_archivo("PROCESO_MAESTRO_CLIENTES", False))

        action_button(card_frame, "Iniciar proceso de clientes",
                      self.controller.iniciar_proceso_completo)

    def _create_proceso_colaboradores_card(self, parent):
        """Tarjeta del proceso de Colaboradores."""
        card_frame = card(parent, "Proceso 2: Generación de Planos Colaboradores")

        file_field(card_frame, "1. Archivo de Colaboradores (.xlsx)",
                   self.file_paths["PROCESO_COLABORADORES"],
                   lambda: self.controller.seleccionar_archivo("PROCESO_COLABORADORES", False))

        action_button(card_frame, "Iniciar proceso de colaboradores",
                      self.controller.iniciar_proceso_colaboradores)

    def actualizar_ruta_label(self, key: str, display_text: str):
        """Actualiza el texto del campo de la clave indicada (lo usa el controlador)."""
        if key in self.file_paths:
            self.file_paths[key].set(display_text)
            self.update_idletasks()
