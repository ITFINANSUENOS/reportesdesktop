import customtkinter as ctk
from tkinter import filedialog, messagebox

# MOTIVO: la capa visual usa customtkinter (look moderno) conservando la MISMA
# estructura y nombres de métodos que usan los controladores.
from src.views.widgets import add_scroll_area, card, file_field, action_button
from src.views.config_view.theme import THEME
from src.utils.task_runner import main_thread, register_action_button


# 1. CLASE BASE (DISEÑO Y FUNCIONES COMUNES)
class BaseCentralesView(ctk.CTkFrame):
    """
    Clase Padre: maneja la interfaz (scroll + tarjetas uniformes) y la
    selección de archivos. No sabe qué empresa es; eso lo dicen las hijas.
    """
    def __init__(self, parent, datacredito_controller, cifin_controller, empresa_name):
        super().__init__(parent, fg_color="transparent")
        self.datacredito_controller = datacredito_controller
        self.cifin_controller = cifin_controller
        self.empresa_name = empresa_name.lower()
        self.main_window = None  # lo asigna CentralesTabView (progreso global)

        # MOTIVO: los controladores reciben la vista POR PARÁMETRO en el clic
        # (igual que Datacrédito/CIFIN), así que NO se guarda aquí un self.view
        # compartido (evita que la pestaña FINANSUEÑOS sobrescriba a ARPESOD).
        # Los placeholders arrancan VACÍOS para que el guard 'if not ruta'
        # funcione de verdad (antes "No seleccionado" era truthy y el flujo
        # intentaba abrir un archivo llamado literalmente "No seleccionado").
        self.dc_plano_path = ctk.StringVar(value="")
        self.dc_correcciones_path = ctk.StringVar(value="")
        self.cifin_plano_path = ctk.StringVar(value="")
        self.cifin_correcciones_path = ctk.StringVar(value="")

        self._init_ui()

    def _init_ui(self):
        content = add_scroll_area(self)

        dc_card = card(content, "Proceso Datacrédito")
        file_field(dc_card, "1. Archivo plano (.txt)", self.dc_plano_path,
                   lambda: self._seleccionar_archivo(self.dc_plano_path, "*.txt"))
        file_field(dc_card, "2. Archivo de correcciones (.xlsx)", self.dc_correcciones_path,
                   lambda: self._seleccionar_archivo(self.dc_correcciones_path, "*.xlsx"))
        register_action_button("datacredito", action_button(
            dc_card, "Generar reporte Datacrédito", self._process_datacredito))

        cifin_card = card(content, "Proceso CIFIN")
        file_field(cifin_card, "1. Archivo plano CIFIN (.txt)", self.cifin_plano_path,
                   lambda: self._seleccionar_archivo(self.cifin_plano_path, "*.txt"))
        file_field(cifin_card, "2. Archivo de correcciones (.xlsx)", self.cifin_correcciones_path,
                   lambda: self._seleccionar_archivo(self.cifin_correcciones_path, "*.xlsx"))
        register_action_button("cifin", action_button(
            cifin_card, "Generar reporte CIFIN", self._process_cifin))

        self.status_label = ctk.CTkLabel(content, text="Listo para procesar.",
                                         text_color=THEME.muted)
        self.status_label.pack(pady=(6, 4))

    def _seleccionar_archivo(self, variable, extension):
        ftypes = [("Archivos", extension), ("Todos", "*.*")]
        path = filedialog.askopenfilename(filetypes=ftypes)
        if path:
            variable.set(path)

    # --- MÉTODO VITAL PARA EL CONTROLADOR ---
    @main_thread
    def update_status(self, message):
        """El controlador llama a esto para mostrar progreso."""
        print(f"[VISTA {self.empresa_name.upper()}]: {message}")
        self.status_label.configure(text=message)

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
        # La vista se pasa por parámetro (el controlador ya no usa self.view).
        self.cifin_controller.run_processing(self, plano, correcciones)


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
        # La vista se pasa por parámetro (el controlador ya no usa self.view).
        self.cifin_controller.run_processing(self, plano, correcciones)


# 4. VISTA DE PESTAÑAS (CONTENEDOR PRINCIPAL)
class CentralesTabView(ctk.CTkFrame):
    """Contenedor del módulo 'Centrales de Riesgo' con sus sub-pestañas."""
    def __init__(self, parent, datacredito_controller, cifin_controller, main_window_controller):
        super().__init__(parent, fg_color="transparent")

        tabs = ctk.CTkTabview(self, fg_color="transparent")
        # MOTIVO (visual): control de pestañas con la paleta de la app.
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

        tab_arp = tabs.add("ARPESOD")
        tab_fnz = tabs.add("FINANSUEÑOS")

        self.tab_arpesod = CentralesArpesodView(tab_arp, datacredito_controller, cifin_controller)
        self.tab_arpesod.pack(fill="both", expand=True)
        self.tab_finansuenos = CentralesFinansuenosView(tab_fnz, datacredito_controller, cifin_controller)
        self.tab_finansuenos.pack(fill="both", expand=True)

        # Las páginas reenvían su avance a la barra única del pie de la ventana.
        self.tab_arpesod.main_window = main_window_controller
        self.tab_finansuenos.main_window = main_window_controller
