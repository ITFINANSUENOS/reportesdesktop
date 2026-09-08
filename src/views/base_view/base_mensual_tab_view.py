import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

# MOTIVO: la capa visual usa customtkinter (look moderno) conservando la MISMA
# estructura y nombres de métodos que usan los controladores/servicios.
from src.views.widgets import add_scroll_area, card, file_field, action_button, status_area
from src.views.config_view.theme import THEME, FONT_FAMILY
from src.utils.task_runner import main_thread, register_action_button


class BaseMensualView(ctk.CTkFrame):
    """Sub-página 'Reporte Base': carga de archivos para generar la base mensual."""

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.controller.set_view(self)
        self.main_window = None  # lo asigna BaseMensualTabView (progreso global)

        # Valores de texto de los campos (un StringVar por archivo requerido).
        self.file_vars = {}
        self.rutas_grupos = {
            "Reportes de Cartera": {
                "ANALISIS": "Análisis de Cartera (ARP y FNS)",
                "R91": "Reportes R91 (ARP y FS)",
                "VENCIMIENTOS": "Vencimientos (ARP y FNS)",
                "R03": "Reportes R03 (Codeudores)",
            },
            "Desembolsos y Ventas": {
                "SC04": "Desembolsos Arpesod (SC04)",
                "FNZ001": "Desembolsos Finansueños (FNZ001)",
                "CRTMPCONSULTA1": "Reporte de ventas CRTMPCONSULTA1",
            },
            "Datos Complementarios": {
                "FNZ003": "Saldos FNZ003",
                "MATRIZ_CARTERA": "Matriz de Cartera",
                "METAS_FRANJAS": "Metas por Franjas",
                "ASESORES": "Asesores Activos",
            },
        }
        for files in self.rutas_grupos.values():
            for key in files:
                self.file_vars[key] = ctk.StringVar(value="No seleccionado")

        content = add_scroll_area(self)

        # --- Tarjeta: Modo de generación ---
        mode_card = card(content, "Modo de generación")
        self.update_mode_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            mode_card, text="Activar modo de actualización rápida (usar el reporte base del mes anterior)",
            variable=self.update_mode_var, command=self._toggle_base_report_visibility,
            text_color=THEME.text, font=(FONT_FAMILY, 11),
            fg_color=THEME.accent, hover_color=THEME.accent_hover).pack(anchor="w")

        self.base_report_path_var = ctk.StringVar(value="No se ha seleccionado ningún reporte base.")
        self.base_report_row = ctk.CTkFrame(mode_card, fg_color="transparent")
        file_field(self.base_report_row, "Reporte base del mes anterior (.xlsx)",
                   self.base_report_path_var, self.controller.seleccionar_reporte_base)

        # --- Tarjetas de archivos ---
        for title, files in self.rutas_grupos.items():
            self._create_file_group(content, title, files)

        # --- Tarjeta: Rango de fechas ---
        dates_card = card(content, "Rango de fechas del reporte")
        dates_row = ctk.CTkFrame(dates_card, fg_color="transparent")
        dates_row.pack(fill="x")
        dates_row.grid_columnconfigure(0, weight=1)
        dates_row.grid_columnconfigure(1, weight=1)
        for col, label, attr in (
            (0, "Fecha de inicio (DD/MM/AAAA)", "start_date_entry"),
            (1, "Fecha de fin (DD/MM/AAAA)", "end_date_entry"),
        ):
            sub = ctk.CTkFrame(dates_row, fg_color="transparent")
            sub.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 12, 0))
            ctk.CTkLabel(sub, text=label, text_color=THEME.text,
                         font=(FONT_FAMILY, 11), anchor="w").pack(anchor="w", pady=(0, 6))
            entry = ctk.CTkEntry(sub, height=36, corner_radius=8, border_width=1,
                                 border_color=THEME.border, text_color=THEME.text)
            entry.pack(fill="x")
            setattr(self, attr, entry)

        # --- Botón principal y estado/progreso ---
        self.procesar_button = action_button(content, "Procesar base mensual",
                                             self.controller.procesar_archivos)
        self.status_label, self.progress_bar = status_area(content, "Esperando archivos...")

        self._toggle_base_report_visibility()

    def _create_file_group(self, parent, title, files):
        group_card = card(parent, title)
        for key, desc in files.items():
            file_field(group_card, desc, self.file_vars[key],
                       lambda k=key: self.controller.seleccionar_archivo(k))

    def _toggle_base_report_visibility(self):
        """Muestra/oculta el campo del reporte base según el modo de actualización."""
        if self.update_mode_var.get():
            self.base_report_row.pack(fill="x", pady=(12, 0))
        else:
            self.base_report_row.pack_forget()

    @main_thread
    def actualizar_ruta_label(self, tipo_archivo, display_text):
        """Actualiza el texto mostrado del campo (lo llama el controlador)."""
        if tipo_archivo in self.file_vars:
            self.file_vars[tipo_archivo].set(display_text)

    @main_thread
    def actualizar_estado(self, mensaje, progreso=None):
        """Actualiza la etiqueta de estado y la barra de progreso de la página."""
        self.status_label.configure(text=mensaje)
        if progreso is not None:
            self.progress_bar.set(max(0.0, min(float(progreso) / 100.0, 1.0)))
        # MOTIVO (progreso global): además de la barra local, alimenta la barra
        # única del pie de la ventana para que el avance sea visible siempre.
        if getattr(self, "main_window", None) is not None and progreso is not None:
            self.main_window.update_progress(progreso)


class NovedadesView(ctk.CTkFrame):
    """Sub-página 'Reporte Novedades': novedades, análisis y módulo opcional de nómina."""

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.controller.set_view(self)
        self.main_window = None  # lo asigna BaseMensualTabView (progreso global)

        self.rutas_novedades, self.rutas_analisis, self.rutas_r91 = [], [], []
        self.ruta_usuarios, self.ruta_reporte_base, self.ruta_nomina = "", "", ""
        self.rutas_call_center = []
        self.label_novedades_path = ctk.StringVar(value="No seleccionado")
        self.label_analisis_path = ctk.StringVar(value="No seleccionado")
        self.label_r91_path = ctk.StringVar(value="No seleccionado")
        self.label_usuarios_path = ctk.StringVar(value="No seleccionado")
        self.label_base_path = ctk.StringVar(value="No seleccionado")
        self.label_call_center_path = ctk.StringVar(value="No seleccionado")
        self.label_nomina_path = ctk.StringVar(value="No seleccionado")

        content = add_scroll_area(self)

        # --- Tarjeta: Archivos de entrada ---
        inputs_card = card(content, "Archivos de entrada")
        file_inputs = [
            ("1. Cargar Reporte Base Mensual (.xlsx)", self.label_base_path, self.seleccionar_reporte_base),
            ("2. Cargar Archivo(s) de Novedades (.xlsx)", self.label_novedades_path, self.seleccionar_novedades),
            ("3. Cargar Archivo(s) de Análisis (.xlsx)", self.label_analisis_path, self.seleccionar_analisis),
            ("4. Cargar Archivo(s) de Recaudos (R91)", self.label_r91_path, self.seleccionar_r91),
            ("5. Cargar Archivo de Usuarios", self.label_usuarios_path, self.seleccionar_usuarios),
            ("6. Cargar Archivo(s) de Call Center", self.label_call_center_path, self.seleccionar_call_center),
        ]
        for label, var, cmd in file_inputs:
            file_field(inputs_card, label, var, cmd)

        # --- Tarjeta: Opciones (nómina opcional) ---
        options_card = card(content, "Opciones adicionales")
        self.calcular_nomina_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_card, text="Calcular nómina", variable=self.calcular_nomina_var,
                        command=self._toggle_nomina_visibility, text_color=THEME.text,
                        font=(FONT_FAMILY, 11),
                        fg_color=THEME.accent, hover_color=THEME.accent_hover).pack(anchor="w")
        self.nomina_row = ctk.CTkFrame(options_card, fg_color="transparent")
        file_field(self.nomina_row, "Archivo de nómina (.xlsx)",
                   self.label_nomina_path, self.seleccionar_nomina)

        # --- Botón principal ---
        register_action_button("novedades", action_button(
            content, "Procesar y generar reporte", self.procesar))

        self._toggle_nomina_visibility()

    def _toggle_nomina_visibility(self):
        if self.calcular_nomina_var.get():
            self.nomina_row.pack(fill="x", pady=(12, 0))
        else:
            self.nomina_row.pack_forget()

    def _get_excel_file_types(self):
        return [
            ("Archivos de Excel", "*.xlsx *.XLSX *.xlsm *.XLSM *.xls *.XLS"),
            ("Todos los archivos", "*.*"),
        ]

    # --- Selectores de archivos (la lógica no cambia) ---
    def seleccionar_nomina(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Archivo de Nómina",
                                              filetypes=self._get_excel_file_types())
        if filepath:
            self.ruta_nomina = filepath
            self.label_nomina_path.set(Path(filepath).name)

    def seleccionar_r91(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar Archivo(s) R91",
                                                filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_r91 = list(filepaths)
            self.label_r91_path.set(f"{len(self.rutas_r91)} archivo(s) seleccionado(s)")

    def seleccionar_reporte_base(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Reporte Base Mensual",
                                              filetypes=self._get_excel_file_types())
        if filepath:
            self.ruta_reporte_base = filepath
            self.label_base_path.set(Path(filepath).name)

    def seleccionar_novedades(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar Archivo(s) de Novedades",
                                                filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_novedades = list(filepaths)
            self.label_novedades_path.set(f"{len(self.rutas_novedades)} archivo(s) seleccionado(s)")

    def seleccionar_usuarios(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar Archivo(s) de Usuarios",
                                                filetypes=self._get_excel_file_types())
        if filepaths:
            self.ruta_usuarios = list(filepaths)
            self.label_usuarios_path.set(f"{len(self.ruta_usuarios)} archivo(s) seleccionado(s)")

    def seleccionar_analisis(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar Archivo(s) de Análisis",
                                                filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_analisis = list(filepaths)
            self.label_analisis_path.set(f"{len(self.rutas_analisis)} archivo(s) seleccionado(s)")

    def seleccionar_call_center(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar Archivo(s) de Call Center",
                                                filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_call_center = list(filepaths)
            self.label_call_center_path.set(f"{len(self.rutas_call_center)} archivo(s) seleccionado(s)")

    def procesar(self):
        """Envía al controlador todo lo seleccionado en la página."""
        self.controller.procesar_archivos(
            ruta_base=self.ruta_reporte_base, rutas_novedades=self.rutas_novedades,
            rutas_analisis=self.rutas_analisis, rutas_r91=self.rutas_r91,
            ruta_usuarios=self.ruta_usuarios,
            rutas_call_center=self.rutas_call_center,
            calcular_nomina=self.calcular_nomina_var.get(),
            ruta_nomina=self.ruta_nomina,
        )


class BaseMensualTabView(ctk.CTkFrame):
    """Contenedor del módulo 'Base Mensual' con sus sub-páginas."""
    def __init__(self, parent, base_mensual_controller, novedades_analisis_controller,
                 main_window_controller):
        super().__init__(parent, fg_color="transparent")

        tabs = ctk.CTkTabview(self, fg_color="transparent")
        # MOTIVO (visual): estilizar el control de pestañas con la paleta de la
        # app en vez del azul por defecto de customtkinter.
        try:
            tabs.configure(
                segmented_button_selected_color=THEME.accent,
                segmented_button_selected_hover_color=THEME.accent_hover,
                segmented_button_unselected_color=THEME.surface_alt,
                segmented_button_unselected_hover_color=THEME.border,
            )
        except Exception:
            pass
        tabs.pack(fill="both", expand=True, padx=6, pady=6)

        tab_base = tabs.add("Reporte Base")
        tab_nov = tabs.add("Reporte Novedades")

        reporte_base_frame = BaseMensualView(tab_base, base_mensual_controller)
        reporte_base_frame.pack(fill="both", expand=True)
        reporte_novedades_frame = NovedadesView(tab_nov, novedades_analisis_controller)
        reporte_novedades_frame.pack(fill="both", expand=True)

        # Las páginas reenvían su avance a la barra única del pie de la ventana.
        reporte_base_frame.main_window = main_window_controller
        reporte_novedades_frame.main_window = main_window_controller
