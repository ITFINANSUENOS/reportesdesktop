import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

# MOTIVO: componentes visuales compartidos (consistencia entre módulos).
from src.views.widgets import add_scroll_area, card, file_field, action_button, status_area
# MOTIVO (hilos): estos métodos de UI se re-despachan al hilo principal aunque
# un hilo de trabajo los invoque (tkinter no es thread-safe).
from src.utils.task_runner import main_thread


class BaseMensualView(ttk.Frame):
    """Sub-página 'Reporte Base': carga de archivos para generar la base mensual."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.controller.set_view(self)
        self.configure(style='TFrame')
        self.main_window = None  # lo asigna BaseMensualTabView (progreso global)

        # Valores de texto de los campos (un StringVar por archivo requerido).
        # MOTIVO: antes eran etiquetas; usar StringVar + Entry readonly hace que
        # esta página se vea idéntica a las demás (misma fila de archivo).
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
                self.file_vars[key] = tk.StringVar(value="No seleccionado")

        content = add_scroll_area(self)

        # --- Tarjeta: Modo de generación ---
        mode_card = card(content, "Modo de generación")
        self.update_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            mode_card,
            text="Activar modo de actualización rápida (usar el reporte base del mes anterior)",
            variable=self.update_mode_var,
            command=self._toggle_base_report_visibility,
            style='Card.TCheckbutton',
        ).pack(anchor="w")

        # Campo que se muestra/oculta según el modo seleccionado.
        self.base_report_path_var = tk.StringVar(value="No se ha seleccionado ningún reporte base.")
        self.base_report_row = ttk.Frame(mode_card, style='Card.TFrame')
        file_field(
            self.base_report_row,
            "Reporte base del mes anterior (.xlsx)",
            self.base_report_path_var,
            self.controller.seleccionar_reporte_base,
        )

        # --- Tarjetas de archivos ---
        for title, files in self.rutas_grupos.items():
            self._create_file_group(content, title, files)

        # --- Tarjeta: Rango de fechas ---
        dates_card = card(content, "Rango de fechas del reporte")
        dates_row = ttk.Frame(dates_card, style='Card.TFrame')
        dates_row.pack(fill="x")
        dates_row.columnconfigure(0, weight=1)
        dates_row.columnconfigure(1, weight=1)

        for col, label, attr in (
            (0, "Fecha de inicio (DD/MM/AAAA)", "start_date_entry"),
            (1, "Fecha de fin (DD/MM/AAAA)", "end_date_entry"),
        ):
            sub = ttk.Frame(dates_row, style='Card.TFrame')
            sub.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0))
            ttk.Label(sub, text=label, style='Card.TLabel').pack(anchor="w", pady=(0, 6))
            entry = ttk.Entry(sub)
            entry.pack(fill="x")
            setattr(self, attr, entry)

        # --- Botón principal y estado/progreso ---
        self.procesar_button = action_button(
            content, "Procesar base mensual", self.controller.procesar_archivos)
        self.status_label, self.progress_bar = status_area(content, "Esperando archivos...")

        # Estado inicial: si no está activo el modo actualización, el campo se oculta.
        self._toggle_base_report_visibility()

    def _create_file_group(self, parent, title, files):
        """Tarjeta con los campos de un grupo de archivos."""
        group_card = card(parent, title)
        for key, desc in files.items():
            file_field(
                group_card,
                desc,
                self.file_vars[key],
                lambda k=key: self.controller.seleccionar_archivo(k),
            )

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
            self.update_idletasks()

    @main_thread
    def actualizar_estado(self, mensaje, progreso=None):
        """Actualiza la etiqueta de estado y la barra de progreso de la página."""
        self.status_label.config(text=mensaje)
        if progreso is not None:
            self.progress_bar.config(value=progreso)
        # MOTIVO (progreso global): además de la barra local, se alimenta la
        # barra única del pie de la ventana para que el avance sea visible
        # siempre (aunque el usuario cambie de módulo mientras corre).
        if getattr(self, "main_window", None) is not None and progreso is not None:
            self.main_window.update_progress(progreso)
        self.update_idletasks()


class NovedadesView(ttk.Frame):
    """Sub-página 'Reporte Novedades': novedades, análisis y módulo opcional de nómina."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.controller.set_view(self)
        self.main_window = None  # lo asigna BaseMensualTabView (progreso global)

        # Rutas (listas) y variables de texto de los campos.
        self.rutas_novedades, self.rutas_analisis, self.rutas_r91 = [], [], []
        self.ruta_usuarios, self.ruta_reporte_base, self.ruta_nomina = "", "", ""
        self.rutas_call_center = []
        self.label_novedades_path = tk.StringVar(value="No seleccionado")
        self.label_analisis_path = tk.StringVar(value="No seleccionado")
        self.label_r91_path = tk.StringVar(value="No seleccionado")
        self.label_usuarios_path = tk.StringVar(value="No seleccionado")
        self.label_base_path = tk.StringVar(value="No seleccionado")
        self.label_call_center_path = tk.StringVar(value="No seleccionado")
        self.label_nomina_path = tk.StringVar(value="No seleccionado")

        self.configure(style='TFrame')
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
        self.calcular_nomina_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_card,
            text="Calcular nómina",
            variable=self.calcular_nomina_var,
            command=self._toggle_nomina_visibility,
            style='Card.TCheckbutton',
        ).pack(anchor="w")

        # Campo de nómina que se muestra/oculta según el checkbox.
        self.nomina_row = ttk.Frame(options_card, style='Card.TFrame')
        file_field(
            self.nomina_row,
            "Archivo de nómina (.xlsx)",
            self.label_nomina_path,
            self.seleccionar_nomina,
        )

        # --- Botón principal ---
        action_button(content, "Procesar y generar reporte", self.procesar)

        self._toggle_nomina_visibility()

    def _toggle_nomina_visibility(self):
        """Muestra/oculta el campo de nómina según el checkbox 'Calcular nómina'."""
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
        filepath = filedialog.askopenfilename(
            title="Seleccionar Archivo de Nómina", filetypes=self._get_excel_file_types())
        if filepath:
            self.ruta_nomina = filepath
            self.label_nomina_path.set(Path(filepath).name)

    def seleccionar_r91(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivo(s) R91", filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_r91 = list(filepaths)
            self.label_r91_path.set(f"{len(self.rutas_r91)} archivo(s) seleccionado(s)")

    def seleccionar_reporte_base(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar Reporte Base Mensual", filetypes=self._get_excel_file_types())
        if filepath:
            self.ruta_reporte_base = filepath
            self.label_base_path.set(Path(filepath).name)

    def seleccionar_novedades(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivo(s) de Novedades", filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_novedades = list(filepaths)
            self.label_novedades_path.set(f"{len(self.rutas_novedades)} archivo(s) seleccionado(s)")

    def seleccionar_usuarios(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivo(s) de Usuarios", filetypes=self._get_excel_file_types())
        if filepaths:
            self.ruta_usuarios = list(filepaths)
            self.label_usuarios_path.set(f"{len(self.ruta_usuarios)} archivo(s) seleccionado(s)")

    def seleccionar_analisis(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivo(s) de Análisis", filetypes=self._get_excel_file_types())
        if filepaths:
            self.rutas_analisis = list(filepaths)
            self.label_analisis_path.set(f"{len(self.rutas_analisis)} archivo(s) seleccionado(s)")

    def seleccionar_call_center(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivo(s) de Call Center", filetypes=self._get_excel_file_types())
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


class BaseMensualTabView(ttk.Frame):
    """Contenedor del módulo 'Base Mensual' con sus sub-páginas."""

    def __init__(self, parent, base_mensual_controller, novedades_analisis_controller, main_window_controller):
        super().__init__(parent)
        self.configure(style='TFrame')

        # Sub-pestañas (mismo margen que en Centrales para que todo se vea alineado).
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        reporte_base_frame = BaseMensualView(notebook, base_mensual_controller)
        notebook.add(reporte_base_frame, text="  Reporte Base  ")

        reporte_novedades_frame = NovedadesView(notebook, novedades_analisis_controller)
        notebook.add(reporte_novedades_frame, text="  Reporte Novedades  ")

        # MOTIVO (progreso global): se guarda la ventana principal para que las
        # páginas puedan mover la barra única del pie de la ventana.
        reporte_base_frame.main_window = main_window_controller
        reporte_novedades_frame.main_window = main_window_controller
