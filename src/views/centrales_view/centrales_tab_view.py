import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# MOTIVO: componentes visuales compartidos (consistencia entre módulos).
from src.views.widgets import add_scroll_area, card, file_field, action_button
# MOTIVO (hilos): el controlador de Datacrédito corre en un hilo; este método
# de UI se re-despacha al hilo principal para no violar la seguridad de tkinter.
from src.utils.task_runner import main_thread


# 1. CLASE BASE (DISEÑO Y FUNCIONES COMUNES)
class BaseCentralesView(ttk.Frame):
    """
    Clase Padre: maneja la interfaz (scroll + tarjetas uniformes) y la
    selección de archivos. No sabe qué empresa es; eso lo dicen las hijas.
    """
    def __init__(self, parent, datacredito_controller, cifin_controller, empresa_name):
        super().__init__(parent)
        self.datacredito_controller = datacredito_controller
        self.cifin_controller = cifin_controller
        self.empresa_name = empresa_name.lower()
        self.main_window = None  # lo asigna CentralesTabView (progreso global)

        # MOTIVO (progreso global): los controladores necesitan la vista para
        # poder reenviar su avance a la barra única del pie.
        datacredito_controller.set_view(self)
        cifin_controller.set_view(self)

        # Variables de rutas (se guarda la ruta completa para procesar).
        self.dc_plano_path = tk.StringVar(value="No seleccionado")
        self.dc_correcciones_path = tk.StringVar(value="No seleccionado")
        self.cifin_plano_path = tk.StringVar(value="No seleccionado")
        self.cifin_correcciones_path = tk.StringVar(value="No seleccionado")

        self._init_ui()

    def _init_ui(self):
        """Construye la página con el mismo encuadre que el resto de módulos."""
        self.configure(style='TFrame')
        content = add_scroll_area(self)

        # --- Tarjeta: Datacrédito ---
        dc_card = card(content, "Proceso Datacrédito")
        file_field(dc_card, "1. Archivo plano (.txt)", self.dc_plano_path,
                   lambda: self._seleccionar_archivo(self.dc_plano_path, "*.txt"))
        file_field(dc_card, "2. Archivo de correcciones (.xlsx)", self.dc_correcciones_path,
                   lambda: self._seleccionar_archivo(self.dc_correcciones_path, "*.xlsx"))
        action_button(dc_card, "Generar reporte Datacrédito", self._process_datacredito)

        # --- Tarjeta: CIFIN ---
        cifin_card = card(content, "Proceso CIFIN")
        file_field(cifin_card, "1. Archivo plano CIFIN (.txt)", self.cifin_plano_path,
                   lambda: self._seleccionar_archivo(self.cifin_plano_path, "*.txt"))
        file_field(cifin_card, "2. Archivo de correcciones (.xlsx)", self.cifin_correcciones_path,
                   lambda: self._seleccionar_archivo(self.cifin_correcciones_path, "*.xlsx"))
        action_button(cifin_card, "Generar reporte CIFIN", self._process_cifin)

        # --- Estado (estilo común) ---
        self.status_label = ttk.Label(content, text="Listo para procesar.", style='Muted.TLabel')
        self.status_label.pack(pady=(6, 0))

    def _seleccionar_archivo(self, variable, extension):
        ftypes = [("Archivos", extension), ("Todos", "*.*")]
        path = filedialog.askopenfilename(filetypes=ftypes)
        if path:
            variable.set(path)

    # --- MÉTODO VITAL PARA EL CONTROLADOR ---
    @main_thread
    def update_status(self, message):
        """El controlador llama a esto para mostrar progreso."""
        print(f"[VISTA {self.empresa_name.upper()}]: {message}")  # Log consola
        self.status_label.config(text=message)
        self.update_idletasks()

    def report_progress(self, percent):
        """Reenvía el avance a la barra única del pie de la ventana."""
        if getattr(self, "main_window", None) is not None:
            self.main_window.update_progress(percent)

    # --- MÉTODOS ABSTRACTOS (los implementan las clases hijas) ---
    def _process_datacredito(self):
        pass

    def _process_cifin(self):
        pass


# 2. CLASE ARPESOD
class CentralesArpesodView(BaseCentralesView):
    def __init__(self, parent, datacredito_controller, cifin_controller):
        super().__init__(parent, datacredito_controller, cifin_controller, "ARPESOD")

    def _process_datacredito(self):
        plano = self.dc_plano_path.get()
        correcciones = self.dc_correcciones_path.get()

        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para Datacrédito.")
            return

        self.datacredito_controller.set_empresa_actual("arpesod")
        self.datacredito_controller.run_processing_datacredito(self, plano, correcciones)

    def _process_cifin(self):
        plano = self.cifin_plano_path.get()
        correcciones = self.cifin_correcciones_path.get()

        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para CIFIN.")
            return

        self.cifin_controller.set_empresa_actual("arpesod")
        self.cifin_controller.run_processing(plano, correcciones)


# 3. CLASE FINANSUEÑOS
class CentralesFinansuenosView(BaseCentralesView):
    def __init__(self, parent, datacredito_controller, cifin_controller):
        super().__init__(parent, datacredito_controller, cifin_controller, "FINANSUEÑOS")

    def _process_datacredito(self):
        plano = self.dc_plano_path.get()
        correcciones = self.dc_correcciones_path.get()

        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para Datacrédito.")
            return

        self.datacredito_controller.set_empresa_actual("finansueños")
        self.datacredito_controller.run_processing_datacredito(self, plano, correcciones)

    def _process_cifin(self):
        plano = self.cifin_plano_path.get()
        correcciones = self.cifin_correcciones_path.get()

        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para CIFIN.")
            return

        self.cifin_controller.set_empresa_actual("finansueños")
        self.cifin_controller.run_processing(plano, correcciones)


# 4. VISTA DE PESTAÑAS (CONTENEDOR PRINCIPAL)
class CentralesTabView(ttk.Frame):
    """Contenedor del módulo 'Centrales de Riesgo' con sus sub-pestañas."""

    def __init__(self, parent, datacredito_controller, cifin_controller, main_window_controller):
        super().__init__(parent)

        # Sub-pestañas (mismo margen que en Base Mensual para el alineado).
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_arpesod = CentralesArpesodView(notebook, datacredito_controller, cifin_controller)
        self.tab_finansuenos = CentralesFinansuenosView(notebook, datacredito_controller, cifin_controller)

        # MOTIVO (progreso global): las páginas reenvían su avance a la barra
        # única del pie de la ventana.
        self.tab_arpesod.main_window = main_window_controller
        self.tab_finansuenos.main_window = main_window_controller

        notebook.add(self.tab_arpesod, text="  ARPESOD  ")
        notebook.add(self.tab_finansuenos, text="  FINANSUEÑOS  ")
