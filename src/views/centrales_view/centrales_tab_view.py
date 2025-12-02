import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 1. CLASE BASE (DISEÑO Y FUNCIONES COMUNES)
class BaseCentralesView(ttk.Frame):
    """
    Clase Padre: Maneja toda la interfaz gráfica, el scroll y la selección de archivos.
    No sabe qué empresa es, eso se lo dicen las clases hijas.
    """
    def __init__(self, parent, datacredito_controller, cifin_controller, empresa_name):
        super().__init__(parent)
        self.datacredito_controller = datacredito_controller
        self.cifin_controller = cifin_controller
        self.empresa_name = empresa_name.lower() # Guardamos en minúscula para lógica interna
        
        # Variables de rutas
        self.dc_plano_path = tk.StringVar()
        self.dc_correcciones_path = tk.StringVar()
        self.cifin_plano_path = tk.StringVar()
        self.cifin_correcciones_path = tk.StringVar()

        self._init_ui(empresa_name)

    def _init_ui(self, title_text):
        """Configura toda la interfaz con Scroll."""
        # Configuración del Canvas y Scrollbar
        canvas = tk.Canvas(self, bg="#F0F0F0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.scrollable_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Ajustar ancho del frame interno al cambiar tamaño de ventana
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.scrollable_window, width=e.width))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Grid Layout para centrar contenido (5% - 90% - 5%) ---
        scrollable_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.grid_columnconfigure(1, weight=10)
        scrollable_frame.grid_columnconfigure(2, weight=1)

        content = ttk.Frame(scrollable_frame)
        content.grid(row=0, column=1, sticky="nsew", pady=20)

        # --- Título ---
        ttk.Label(content, text=f"Centrales {title_text}", font=("Helvetica", 16, "bold")).pack(pady=(0, 20))

        # --- SECCIÓN DATACRÉDITO ---
        dc_frame = ttk.LabelFrame(content, text=" Proceso Datacrédito ", padding="15")
        dc_frame.pack(fill=tk.X, expand=True, pady=10)
        
        self._crear_selector_archivo(dc_frame, "1. Archivo Plano (.txt):", self.dc_plano_path, "*.txt", 0)
        self._crear_selector_archivo(dc_frame, "2. Correcciones (.xlsx):", self.dc_correcciones_path, "*.xlsx", 2)
        
        ttk.Button(dc_frame, text="▶ Generar Reporte Datacrédito", command=self._process_datacredito, style='Accent.TButton').grid(row=4, column=0, columnspan=3, pady=15, sticky="ew")
        dc_frame.grid_columnconfigure(1, weight=1)

        # --- SECCIÓN CIFIN ---
        cifin_frame = ttk.LabelFrame(content, text=" Proceso CIFIN ", padding="15")
        cifin_frame.pack(fill=tk.X, expand=True, pady=20)

        self._crear_selector_archivo(cifin_frame, "1. Archivo Plano CIFIN (.txt):", self.cifin_plano_path, "*.txt", 0)
        self._crear_selector_archivo(cifin_frame, "2. Correcciones (.xlsx):", self.cifin_correcciones_path, "*.xlsx", 2)
        
        ttk.Button(cifin_frame, text="▶ Generar Reporte CIFIN", command=self._process_cifin, style='Accent.TButton').grid(row=4, column=0, columnspan=3, pady=15, sticky="ew")
        cifin_frame.grid_columnconfigure(1, weight=1)

        # --- Barra de Estado ---
        self.status_label = ttk.Label(content, text="Listo para procesar.", foreground="gray")
        self.status_label.pack(pady=10)

    def _crear_selector_archivo(self, parent, label_text, variable, file_ext, row):
        """Helper para no repetir código de selectores."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=(5, 0))
        ttk.Entry(parent, textvariable=variable, state="readonly").grid(row=row+1, column=0, columnspan=2, sticky="ew", padx=(0, 5))
        ttk.Button(parent, text="📂", width=4, 
                   command=lambda: self._seleccionar_archivo(variable, file_ext)
        ).grid(row=row+1, column=2, sticky="w")

    def _seleccionar_archivo(self, variable, extension):
        ftypes = [("Archivos", extension), ("Todos", "*.*")]
        path = filedialog.askopenfilename(filetypes=ftypes)
        if path: variable.set(path)

    # --- MÉTODO VITAL PARA EL CONTROLADOR ---
    def update_status(self, message):
        """El controlador llama a esto para mostrar progreso."""
        print(f"[VISTA {self.empresa_name.upper()}]: {message}") # Log consola
        self.status_label.config(text=message)
        self.update_idletasks() # Fuerza actualización visual inmediata

    # --- MÉTODOS ABSTRACTOS (Las hijas deben implementar la lógica de validación) ---
    def _process_datacredito(self):
        pass # Se sobreescribe en las hijas
    
    def _process_cifin(self):
        pass # Se sobreescribe en las hijas


# 2. CLASE ARPESOD (IMPLEMENTACIÓN ESPECÍFICA)
class CentralesArpesodView(BaseCentralesView):
    def __init__(self, parent, datacredito_controller, cifin_controller):
        super().__init__(parent, datacredito_controller, cifin_controller, "ARPESOD")

    def _process_datacredito(self):
        # 1. Validar
        plano = self.dc_plano_path.get()
        correcciones = self.dc_correcciones_path.get()
        
        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para Datacrédito.")
            return

        # 2. Configurar Controlador
        self.datacredito_controller.set_empresa_actual("arpesod")
        
        # 3. EJECUTAR (Esto es lo que faltaba antes)
        # Pasamos 'self' para que el controlador pueda llamar a nuestro update_status
        self.datacredito_controller.run_processing_datacredito(self, plano, correcciones)

    def _process_cifin(self):
        plano = self.cifin_plano_path.get()
        correcciones = self.cifin_correcciones_path.get()
        
        if not plano or not correcciones:
            messagebox.showwarning("Faltan Datos", "Selecciona ambos archivos para CIFIN.")
            return

        self.cifin_controller.set_empresa_actual("arpesod")
        self.cifin_controller.run_processing(plano, correcciones) # Asumiendo que cifin tiene logica similar

# 3. CLASE FINANSUEÑOS (IMPLEMENTACIÓN ESPECÍFICA)
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
    """
    Vista principal que contiene las pestañas. Esta es la que instancia
    el MainController.
    """
    def __init__(self, parent, datacredito_controller, cifin_controller, main_window_controller):
        super().__init__(parent)

        # Sistema de Pestañas
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Instanciar las vistas hijas
        self.tab_arpesod = CentralesArpesodView(notebook, datacredito_controller, cifin_controller)
        self.tab_finansuenos = CentralesFinansuenosView(notebook, datacredito_controller, cifin_controller)

        # Agregar al notebook
        notebook.add(self.tab_arpesod, text="   ARPESOD   ")
        notebook.add(self.tab_finansuenos, text="   FINANSUEÑOS   ")