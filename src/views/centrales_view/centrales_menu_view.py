import tkinter as tk
from tkinter import ttk

class CentralesMenuView(ttk.Frame):
    """
    Vista que sirve como menú para seleccionar entre ARPESOD y FINANSUEÑOS
    dentro del módulo de Centrales.
    """
    def __init__(self, parent, main_window_controller):
        super().__init__(parent)
        self.main_window_controller = main_window_controller
        
        # --- Estilos para esta vista ---
        style = ttk.Style()
        style.configure('Module.TFrame', background='#F0F0F0')
        style.configure('ModuleTitle.TLabel', background='#F0F0F0', font=("Helvetica", 16, "bold"))
        self.configure(style='Module.TFrame')

        # --- Botón para volver al menú principal de la aplicación ---
        ttk.Button(self, text="← Volver al Menú Principal", 
                   command=lambda: self.main_window_controller.mostrar_vista("menu")
        ).pack(anchor="nw", padx=10, pady=10)
        
        # --- Contenido de la vista ---
        content_frame = ttk.Frame(self, style='Module.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        ttk.Label(content_frame, text="Módulo de Centrales de Riesgo", 
                  style='ModuleTitle.TLabel'
        ).pack(pady=(20, 30))
        
        # --- Botones para seleccionar la empresa (CON ESTILO APLICADO) ---
        ttk.Button(
            content_frame, 
            text="ARPESOD", 
            command=lambda: self.main_window_controller.mostrar_vista("centrales_arpesod"),
            style='Accent.TButton'  # <-- ESTILO AÑADIDO
        ).pack(pady=10, ipadx=20, ipady=10)
        
        ttk.Button(
            content_frame, 
            text="FINANSUEÑOS", 
            command=lambda: self.main_window_controller.mostrar_vista("centrales_finansuenos"),
            style='Accent.TButton'  # <-- ESTILO AÑADIDO
        ).pack(pady=10, ipadx=20, ipady=10)
        
        