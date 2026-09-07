import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# MOTIVO: todos los módulos comparten ahora los mismos componentes visuales
# (widgets.py) para que la interfaz se vea consistente de principio a fin.
from src.views.widgets import add_scroll_area, card, description, file_field, action_button


class ConveniosAnticiposView(ttk.Frame):
    def __init__(self, parent, convenios_controller, anticipos_controller, main_window_controller):
        super().__init__(parent)
        self.convenios_controller = convenios_controller
        self.anticipos_controller = anticipos_controller

        self.convenios_file_path = tk.StringVar(value="No se ha seleccionado un archivo.")
        self.anticipos_file_path = tk.StringVar(value="No se ha seleccionado un archivo.")

        self.configure(style='TFrame')

        # Área con scroll estándar (igual que en los demás módulos).
        content = add_scroll_area(self)

        # --- Tarjeta: Convenios + Ecollect ---
        convenios_card = card(content, "Cruce de Convenios & Ecollect")
        description(
            convenios_card,
            "Este proceso analiza y cruza la información de Bancolombia, Efecty y "
            "Ecollect para generar un reporte consolidado. Asegúrate de que el "
            "archivo contenga las hojas requeridas.",
        )
        file_field(
            convenios_card,
            "1. Archivo de convenios unificado (.xlsx)",
            self.convenios_file_path,
            self._select_convenios_file,
        )
        action_button(convenios_card, "Generar reporte consolidado", self._generate_convenios_report)

        # --- Tarjeta: Anticipos Online ---
        anticipos_card = card(content, "Anticipos Online")
        description(
            anticipos_card,
            "Este proceso procesa la información de anticipos online. Selecciona el "
            "archivo y haz clic en el botón para comenzar.",
        )
        file_field(
            anticipos_card,
            "1. Archivo de anticipos (.xlsx)",
            self.anticipos_file_path,
            self._select_anticipos_file,
        )
        action_button(anticipos_card, "Generar reporte de anticipos", self._generate_anticipos_report)

    def _select_convenios_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de convenios",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls")])
        if file_path:
            # Solo se muestra el nombre; la ruta completa se guarda para procesar.
            self.convenios_file_path.set(Path(file_path).name)
            self._full_convenios_path = file_path

    def _select_anticipos_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de anticipos",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls")])
        if file_path:
            self.anticipos_file_path.set(Path(file_path).name)
            self._full_anticipos_path = file_path

    def _generate_convenios_report(self):
        if hasattr(self, '_full_convenios_path') and self._full_convenios_path:
            self.convenios_controller.start_report_generation(self._full_convenios_path)
        else:
            messagebox.showerror(
                "Archivo no seleccionado",
                "Por favor, seleccione un archivo de convenios para procesar.")

    def _generate_anticipos_report(self):
        if hasattr(self, '_full_anticipos_path') and self._full_anticipos_path:
            self.anticipos_controller.start_report_generation(self._full_anticipos_path)
        else:
            messagebox.showerror(
                "Archivo no seleccionado",
                "Por favor, seleccione un archivo de anticipos para procesar.")

    # Método auxiliar para actualizar mensajes desde el controlador.
    def update_display(self, message, progress=None):
        print(f"Status: {message} ({progress}%)")
