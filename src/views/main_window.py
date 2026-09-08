# src/views/main_window.py
#
# Ventana principal (customtkinter).
#
# MOTIVO DEL CAMBIO: se migró de tkinter/ttk a customtkinter para lograr un look
# realmente moderno (tarjetas/botones redondeados, colores limpios y sidebar).
# La estructura y los métodos que usan los controladores NO cambian:
# select_page(), update_status(), update_progress(), update_display().
import datetime
import functools

import customtkinter as ctk

# MOTIVO (hilos): estos métodos de UI corren siempre en el hilo principal.
from src.utils.task_runner import main_thread
from src.views.config_view.theme import THEME, FONT_FAMILY
from src.views.config_view.config_view import AppConfig
from src.views.config_view.assets import app_icon_photo
from src.views.convenios_anticipos_view.convenios_anticipos_view import ConveniosAnticiposView
from src.views.base_view.base_mensual_tab_view import BaseMensualTabView
from src.views.centrales_view.centrales_tab_view import CentralesTabView
from src.views.ecollect.ecollect_view import EcollectView


class MainWindow:
    """Ventana principal con navegación lateral (sidebar) estilo moderno."""

    SIDEBAR_W = 250

    NAV = [
        ("convenios", "Convenios y Anticipos"),
        ("base_mensual", "Base Mensual"),
        ("centrales", "Centrales de Riesgo"),
        ("ecollect", "Ecollect"),
    ]

    def __init__(self, root, controller_convenios, controller_anticipos, controller_base_mensual,
                 controller_datacredito, controller_cifin, controller_novedades_analisis,
                 controller_ecollect):

        self.root = root
        self.config = AppConfig()

        self.controllers = {
            "convenios": controller_convenios,
            "anticipos": controller_anticipos,
            "base_mensual": controller_base_mensual,
            "datacredito": controller_datacredito,
            "cifin": controller_cifin,
            "novedades_analisis": controller_novedades_analisis,
            "ecollect": controller_ecollect,
        }

        self._pages = {}
        self._nav_buttons = {}
        self._current = None

        # --- Ventana ---
        self.root.title(self.config.title)
        self.root.minsize(self.config.min_width, self.config.min_height)
        self.root.geometry(self.config.geometry)
        self.root.resizable(True, True)
        try:
            self.root.iconphoto(True, app_icon_photo(THEME.accent, THEME.on_accent))
        except Exception:
            pass

        self._build_shell()
        self._center_window()
        self.select_page("convenios")

        controller_anticipos.set_view(self)
        controller_convenios.set_view(self)

    # ---------------------------------------------------------------- layout
    def _build_shell(self):
        """Sidebar izquierdo + área de contenido (cabecera, páginas, estado)."""
        # --- SIDEBAR ---
        sidebar = ctk.CTkFrame(self.root, width=self.SIDEBAR_W, corner_radius=0,
                               fg_color=THEME.sidebar_bg)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="Reportes Financieros",
                     text_color=THEME.sidebar_text,
                     font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", padx=18, pady=(22, 2))
        ctk.CTkLabel(sidebar, text="Departamento Financiero",
                     text_color=THEME.sidebar_text_dim,
                     font=(FONT_FAMILY, 9)).pack(anchor="w", padx=18, pady=(0, 20))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=10)
        for key, label in self.NAV:
            button = ctk.CTkButton(
                nav, text=label, anchor="w", height=42, corner_radius=10,
                fg_color="transparent", hover_color=THEME.sidebar_hover,
                text_color=THEME.sidebar_text,
                font=(FONT_FAMILY, 12),
                command=functools.partial(self.select_page, key),
            )
            button.pack(fill="x", pady=3)
            self._nav_buttons[key] = button

        ctk.CTkLabel(sidebar, text=f"© {datetime.date.today().year}",
                     text_color=THEME.sidebar_text_dim,
                     font=(FONT_FAMILY, 8)).pack(side="bottom", anchor="w", padx=18, pady=16)

        # --- ÁREA DE CONTENIDO ---
        content = ctk.CTkFrame(self.root, corner_radius=0, fg_color=THEME.surface)
        content.pack(side="left", fill="both", expand=True)

        # Cabecera
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(20, 6))
        self.header_title = ctk.CTkLabel(header, text="", text_color=THEME.text,
                                         font=(FONT_FAMILY, 21, "bold"), anchor="w")
        self.header_title.pack(anchor="w")
        self.header_sub = ctk.CTkLabel(header, text="", text_color=THEME.muted,
                                       font=(FONT_FAMILY, 10), anchor="w")
        self.header_sub.pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(content, height=1, fg_color=THEME.border).pack(fill="x", padx=28)

        # Zona de páginas
        body = ctk.CTkFrame(content, fg_color=THEME.bg, corner_radius=0)
        body.pack(fill="both", expand=True, padx=0, pady=(0, 0))
        self.body = body

        pages = {
            "convenios": ConveniosAnticiposView(
                body, self.controllers["convenios"], self.controllers["anticipos"], self),
            "base_mensual": BaseMensualTabView(
                body, self.controllers["base_mensual"],
                self.controllers["novedades_analisis"], self),
            "centrales": CentralesTabView(
                body, self.controllers["datacredito"], self.controllers["cifin"], self),
            "ecollect": EcollectView(body, self.controllers["ecollect"], self),
        }
        for key, page in pages.items():
            self._pages[key] = page

        # Barra de estado inferior
        status_bar = ctk.CTkFrame(content, fg_color=THEME.surface, corner_radius=0)
        status_bar.pack(fill="x", side="bottom")
        ctk.CTkFrame(status_bar, height=1, fg_color=THEME.border).pack(fill="x")
        row = ctk.CTkFrame(status_bar, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(8, 10))

        self.status_label = ctk.CTkLabel(row, text="Estado: Listo",
                                         text_color=THEME.muted, font=(FONT_FAMILY, 10))
        self.status_label.pack(side="left")
        self.footer_progress = ctk.CTkProgressBar(row, width=220, height=10,
                                                  corner_radius=5,
                                                  fg_color=THEME.surface_alt,
                                                  progress_color=THEME.accent)
        self.footer_progress.pack(side="left", padx=18)
        self.footer_progress.set(0)
        footer = ctk.CTkLabel(row, text=f"© {datetime.date.today().year} Departamento Financiero",
                              text_color=THEME.muted, font=(FONT_FAMILY, 9))
        footer.pack(side="right")

    def _center_window(self):
        """Centra la ventana en pantalla."""
        self.root.update_idletasks()
        try:
            w, h = (int(x) for x in self.config.geometry.lower().split("x"))
        except (ValueError, AttributeError):
            return
        x = max((self.root.winfo_screenwidth() - w) // 2, 0)
        y = max((self.root.winfo_screenheight() - h) // 2, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ---------------------------------------------------------- navegación
    def select_page(self, key):
        """Muestra la página de 'key' y actualiza cabecera/sidebar."""
        if key not in self._pages:
            return
        self._current = key

        meta = {k: v for k, v in self.NAV}
        self.header_title.configure(text=meta[key])
        subs = {
            "convenios": "Cruce Bancolombia, Efecty, Ecollect y anticipos online",
            "base_mensual": "Reporte base y novedades / análisis mensual",
            "centrales": "Reportes Datacrédito y CIFIN - ARPESOD / FINANSUEÑOS",
            "ecollect": "Generación de planos de clientes y colaboradores",
        }
        self.header_sub.configure(text=subs.get(key, ""))

        for k, page in self._pages.items():
            if k == key:
                page.pack(fill="both", expand=True, padx=22, pady=14)
            else:
                page.pack_forget()

        for k, button in self._nav_buttons.items():
            active = (k == key)
            button.configure(fg_color=THEME.sidebar_active if active else "transparent")

    # ------------------------------------------------------------ estado
    @main_thread
    def update_status(self, message: str):
        """Actualiza el texto de estado de la barra inferior."""
        self.status_label.configure(text=f"Estado: {message}")

    @main_thread
    def update_progress(self, progress: int):
        """Actualiza la barra de progreso del pie (0-100)."""
        if progress is not None:
            value = max(0.0, min(float(progress) / 100.0, 1.0))
            self.footer_progress.set(value)

    @main_thread
    def update_display(self, message: str, progress: int):
        """Método unificado que actualiza estado y progreso."""
        self.update_status(message)
        self.update_progress(progress)
