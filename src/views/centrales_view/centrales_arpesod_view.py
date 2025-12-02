import tkinter as tk
from tkinter import ttk,filedialog, messagebox

class CentralesArpesodView(ttk.Frame):
    """
    Vista para los procesos de Datacredito y CIFIN de ARPESOD,
    con scroll y estilos consistentes.
    """

    def __init__(self, parent, datacredito_controller, cifin_controller, main_window_controller):
        super().__init__(parent)
        self.datacredito_controller = datacredito_controller
        self.cifin_controller = cifin_controller
        self.main_window_controller = main_window_controller
        
        # --- Variables para las rutas de los archivos ---
        self.dc_plano_path = tk.StringVar()
        self.dc_correcciones_path = tk.StringVar()
        self.cifin_plano_path = tk.StringVar()
        self.cifin_correcciones_path = tk.StringVar()

        # --- Estilos y configuración ---
        style = ttk.Style()
        style.configure('Base.TFrame', background='#F0F0F0')
        style.configure('Card.TFrame', background='#FFFFFF')
        style.configure('ModuleTitle.TLabel', background='#F0F0F0', font=("Helvetica", 16, "bold"))
        self.configure(style='Base.TFrame')
        
        # --- Botón para volver al menú de Centrales ---
        top_bar_frame = ttk.Frame(self, style='Base.TFrame')
        top_bar_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(top_bar_frame, text="← Volver a Centrales",
                   command=lambda: self.main_window_controller.mostrar_vista("centrales_menu")
        ).pack(anchor="nw")

        # --- Frame principal con scroll (igual que en BaseMensualView) ---
        main_frame = ttk.Frame(self, padding="10", style='Base.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame, bg="#F0F0F0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Título Principal de la Vista (dentro del frame con scroll) ---
        ttk.Label(scrollable_frame, text="Centrales ARPESOD",
                  style='Title.TLabel' # Usamos el estilo 'Title' para consistencia
        ).pack(pady=(20, 15))

        # --- SECCIÓN DATACREDITO ---
        dc_frame = ttk.LabelFrame(scrollable_frame, text=" Datacredito ", padding="15")
        dc_frame.pack(fill=tk.X, expand=True, padx=20, pady=10)
        
        ttk.Label(dc_frame, text="1. Cargar Archivo Plano (.txt):").grid(row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Entry(dc_frame, textvariable=self.dc_plano_path, width=60, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(dc_frame, text="Seleccionar...", command=self.seleccionar_dc_plano).grid(row=1, column=1, sticky="ew")
        
        ttk.Label(dc_frame, text="2. Cargar Correcciones (.xlsx):").grid(row=2, column=0, sticky="w", pady=(15, 5))
        ttk.Entry(dc_frame, textvariable=self.dc_correcciones_path, width=60, state="readonly").grid(row=3, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(dc_frame, text="Seleccionar...", command=self.seleccionar_dc_correcciones).grid(row=3, column=1, sticky="ew")
        
        ttk.Button(dc_frame, text="▶ Generar Reporte Datacredito", command=self.procesar_datacredito, style='Accent.TButton').grid(row=4, column=0, columnspan=2, pady=(20, 10))
        dc_frame.grid_columnconfigure(0, weight=1)

        # --- SECCIÓN CIFIN ---
        cifin_frame = ttk.LabelFrame(scrollable_frame, text=" CIFIN ", padding="15")
        cifin_frame.pack(fill=tk.X, expand=True, padx=20, pady=10)

        ttk.Label(cifin_frame, text="1. Cargar Archivo Plano CIFIN (.txt):").grid(row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Entry(cifin_frame, textvariable=self.cifin_plano_path, width=60, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(cifin_frame, text="Seleccionar...", command=self.seleccionar_cifin_plano).grid(row=1, column=1, sticky="ew")

        ttk.Label(cifin_frame, text="2. Cargar Correcciones (.xlsx):").grid(row=2, column=0, sticky="w", pady=(15, 5))
        ttk.Entry(cifin_frame, textvariable=self.cifin_correcciones_path, width=60, state="readonly").grid(row=3, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(cifin_frame, text="Seleccionar...", command=self.seleccionar_cifin_correcciones).grid(row=3, column=1, sticky="ew")
        
        ttk.Button(cifin_frame, text="▶ Generar Reporte CIFIN", command=self.procesar_cifin, style='Accent.TButton').grid(row=4, column=0, columnspan=2, pady=(20, 10))
        cifin_frame.grid_columnconfigure(0, weight=1)
        
    def update_status(self, mensaje):
        """
        Este método es llamado por el Controlador para reportar progreso.
        """
        print(f"[VISTA STATUS]: {mensaje}")    
        
    # --- Métodos de la clase (sin cambios) ---
    def seleccionar_dc_plano(self):
        filepath = filedialog.askopenfilename(title="Seleccionar plano Datacredito", filetypes=[("Archivos de Texto", "*.txt")])
        if filepath: self.dc_plano_path.set(filepath)

    def seleccionar_dc_correcciones(self):
        filepath = filedialog.askopenfilename(title="Seleccionar correcciones Datacredito", filetypes=[("Archivos de Excel", "*.xlsx")])
        if filepath: self.dc_correcciones_path.set(filepath)
        
    def procesar_datacredito(self):
        plano = self.dc_plano_path.get()
        correcciones = self.dc_correcciones_path.get()

        if not plano:
            messagebox.showwarning("Faltan datos", "Por favor selecciona el archivo Plano (.txt)")
            return
        if not correcciones:
            messagebox.showwarning("Faltan datos", "Por favor selecciona el archivo de Correcciones (.xlsx)")
            return
        # 2. Configurar la empresa en el controlador
        self.datacredito_controller.set_empresa_actual("arpesod")

        # 3. LLAMAR AL CONTROLADOR (Esto es lo que faltaba)
        # Pasamos 'self' porque el controlador espera la vista como primer argumento
        self.datacredito_controller.run_processing_datacredito(self, plano, correcciones)
        
    def seleccionar_cifin_plano(self):
        filepath = filedialog.askopenfilename(title="Seleccionar plano CIFIN", filetypes=[("Archivos de texto", "*.txt")])
        if filepath: self.cifin_plano_path.set(filepath)

    def seleccionar_cifin_correcciones(self):
        filepath = filedialog.askopenfilename(title="Seleccionar correcciones CIFIN", filetypes=[("Archivos Excel", "*.xlsx")])
        if filepath: self.cifin_correcciones_path.set(filepath)
        
    def procesar_cifin(self):
        if not self.cifin_plano_path.get():
            messagebox.showerror("Error", "Debe seleccionar un archivo plano de CIFIN")
            return
            
        if not self.cifin_correcciones_path.get():
            messagebox.showerror("Error", "Debe seleccionar un archivo de correcciones")
            return
            
        # Establecer que es ARPESOD antes de procesar
        self.cifin_controller.set_empresa_actual("arpesod")
        self.cifin_controller.run_processing(
            self.cifin_plano_path.get(), 
            self.cifin_correcciones_path.get()
        )