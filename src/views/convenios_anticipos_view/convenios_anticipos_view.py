import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

class ConveniosAnticiposView(ttk.Frame):
    def __init__(self, parent, convenios_controller, anticipos_controller, main_window_controller):
        super().__init__(parent)
        self.convenios_controller = convenios_controller
        self.anticipos_controller = anticipos_controller
        
        self.convenios_file_path = tk.StringVar()
        self.anticipos_file_path = tk.StringVar()

        self.configure(style='TFrame')

        canvas = tk.Canvas(self, bg="#F0F0F0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self.scrollable_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(self.scrollable_window, width=canvas_width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        scrollable_frame.grid_columnconfigure(0, weight=5)
        scrollable_frame.grid_columnconfigure(1, weight=90)
        scrollable_frame.grid_columnconfigure(2, weight=5)
        
        title_label = ttk.Label(scrollable_frame, text="Módulo de Convenios, Ecollect y Anticipos", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(20, 30))

        main_container = ttk.Frame(scrollable_frame)
        main_container.grid(row=1, column=1, sticky="nsew")

        # --- SECCIÓN ACTUALIZADA: Convenios + Ecollect ---
        convenios_frame = ttk.LabelFrame(main_container, text=" Cruce de Convenios & Ecollect ", padding=20)
        convenios_frame.pack(fill='x', expand=False, pady=(0, 20))

        convenios_desc = ttk.Label(
            convenios_frame, 
            text="Este proceso analiza y cruza la información de Bancolombia, Efecty y Ecollect para generar un reporte consolidado. Asegúrate de que el archivo contenga las hojas requeridas.",
            wraplength=600, 
            justify="left"
        )
        convenios_desc.pack(pady=(0, 20), anchor="w")

        convenios_form = ttk.Frame(convenios_frame)
        convenios_form.pack(fill='x', expand=True)
        convenios_form.grid_columnconfigure(0, weight=1)

        ttk.Label(convenios_form, text="1. Seleccione el archivo de convenios unificado (.xlsx):").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        ttk.Entry(convenios_form, textvariable=self.convenios_file_path, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(convenios_form, text="Seleccionar...", command=self._select_convenios_file).grid(row=1, column=1, sticky="ew")

        ttk.Button(
            convenios_form, 
            text="▶ Generar Reporte Consolidado",
            command=self._generate_convenios_report, 
            style='Modern.TButton'
        ).grid(row=2, column=0, columnspan=2, pady=(20, 10), ipady=5)

        # --- SECCIÓN: Anticipos ---
        anticipos_frame = ttk.LabelFrame(main_container, text=" Anticipos Online ", padding=20)
        anticipos_frame.pack(fill='x', expand=False, pady=10)

        anticipos_desc = ttk.Label(
            anticipos_frame,
            text="Este proceso procesa la información de anticipos online. Haz clic en el botón para seleccionar el archivo y comenzar.",
            wraplength=600,
            justify="left"
        )
        anticipos_desc.pack(pady=(0, 20), anchor="w")

        anticipos_form = ttk.Frame(anticipos_frame)
        anticipos_form.pack(fill='x', expand=True)
        anticipos_form.grid_columnconfigure(0, weight=1)

        ttk.Label(anticipos_form, text="1. Seleccione el archivo de anticipos (.xlsx):").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        ttk.Entry(anticipos_form, textvariable=self.anticipos_file_path, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(anticipos_form, text="Seleccionar...", command=self._select_anticipos_file).grid(row=1, column=1, sticky="ew")

        ttk.Button(
            anticipos_form, 
            text="▶ Generar Reporte de Anticipos",
            command=self._generate_anticipos_report, 
            style='Modern.TButton'
        ).grid(row=2, column=0, columnspan=2, pady=(20, 10), ipady=5)
        
    def _select_convenios_file(self):
        file_path = filedialog.askopenfilename(title="Seleccionar archivo de convenios", filetypes=[("Archivos de Excel", "*.xlsx *.xls")])
        if file_path:
            self.convenios_file_path.set(Path(file_path).name)
            self._full_convenios_path = file_path

    def _select_anticipos_file(self):
        file_path = filedialog.askopenfilename(title="Seleccionar archivo de anticipos", filetypes=[("Archivos de Excel", "*.xlsx *.xls")])
        if file_path:
            self.anticipos_file_path.set(Path(file_path).name)
            self._full_anticipos_path = file_path
            
    def _generate_convenios_report(self):
        if hasattr(self, '_full_convenios_path') and self._full_convenios_path:
            self.convenios_controller.start_report_generation(self._full_convenios_path)
        else:
            messagebox.showerror("Archivo no seleccionado", "Por favor, seleccione un archivo de convenios para procesar.")

    def _generate_anticipos_report(self):
        if hasattr(self, '_full_anticipos_path') and self._full_anticipos_path:
            self.anticipos_controller.start_report_generation(self._full_anticipos_path)
        else:
            messagebox.showerror("Archivo no seleccionado", "Por favor, seleccione un archivo de anticipos para procesar.")
    
    # Método auxiliar para actualizar mensajes desde el controlador
    def update_display(self, message, progress=None):
        print(f"Status: {message} ({progress}%)")
