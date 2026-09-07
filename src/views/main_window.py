import tkinter as tk
from tkinter import ttk
import datetime

# MOTIVO (hilos): estas utilidades permiten que los métodos de UI se ejecuten
# siempre en el hilo principal aunque un hilo de trabajo los invoque.
from src.utils.task_runner import main_thread
from src.views.config_view.config_view import AppConfig
from src.views.config_view.style_assets import create_rounded_button_images
from src.views.config_view.assets import (
    app_icon_photo,
    brand_photo,
    button_photos,
    rounded_photo,
)
from src.views.config_view.theme import (
    THEME,
    apply_theme,
    register_card_style,
    register_secondary_button,
    register_accent_button,
    register_primary_button,
)
from src.views.convenios_anticipos_view.convenios_anticipos_view import ConveniosAnticiposView
from src.views.base_view.base_mensual_tab_view import BaseMensualTabView
from src.views.centrales_view.centrales_tab_view import CentralesTabView
from src.views.ecollect.ecollect_view import EcollectView


class MainWindow:
    """Ventana principal con navegación lateral (sidebar) estilo Fluent.

    MOTIVO DEL REDISEÑO: antes la app era un único Notebook con pestañas
    superiores sobre un tema ttk sin estilizar. Para una apariencia moderna se
    sustituye el notebook exterior por un SIDEBAR índigo con navegación y una
    cabecera de módulo. Cada página (Convenios, Base Mensual, Centrales,
    Ecollect) es la MISMA vista de siempre (ttk.Frame), solo que ahora se
    muestra/oculta dentro del área de contenido; la lógica no cambia.
    """

    SIDEBAR_W = 236

    # Metadatos de navegación: clave -> (etiqueta, subtítulo, chip, fabrica).
    NAV = [
        ("convenios", "Convenios y Anticipos",
         "Cruce Bancolombia, Efecty, Ecollect y anticipos online", "CA"),
        ("base_mensual", "Base Mensual",
         "Reporte base y novedades / análisis mensual", "BM"),
        ("centrales", "Centrales de Riesgo",
         "Reportes Datacrédito y CIFIN - ARPESOD / FINANSUEÑOS", "CR"),
        ("ecollect", "Ecollect",
         "Generación de planos de clientes y colaboradores", "EC"),
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

        self._pages = {}          # key -> vista (ttk.Frame)
        self._nav_rows = {}       # key -> dict de widgets del item del sidebar
        self._nav_photos = {}     # chips dibujados (mantener referencias)
        self._current = None

        # --- Configuración de la ventana ---
        self.root.title(self.config.title)
        self.root.minsize(self.config.min_width, self.config.min_height)
        self.root.geometry(self.config.geometry)
        self.root.resizable(True, True)
        self.root.configure(background=THEME.sidebar_bg)
        # Ícono propio de la app (antes tkinter mostraba un ícono genérico).
        self.root.iconphoto(True, app_icon_photo(THEME.accent, THEME.on_accent))

        self._setup_styles()
        self._build_shell()
        self._center_window()
        self.select_page("convenios")

        controller_anticipos.set_view(self)
        controller_convenios.set_view(self)

    # ---------------------------------------------------------------- estilos
    def _setup_styles(self):
        """Configura el tema (paleta + botones/tarjetas redondeados).

        MOTIVO: todo el estilo se centraliza en theme.py; aquí solo se generan
        las imágenes 9-patch (con PIL) y se registran en los estilos de ttk.
        """
        style = ttk.Style()
        style.theme_use("clam")
        apply_theme(style)

        # Tarjetas: LabelFrames con fondo blanco y borde sutil (look plano).
        register_card_style(style)

        # Botones: secundario (gris suave) + acento (índigo) + primario.
        th = THEME
        register_secondary_button(
            style,
            button_photos(th.soft_bg, th.soft_hover, th.soft_pressed, th.soft_disabled),
        )
        register_accent_button(
            style,
            button_photos(th.accent, th.accent_hover, th.accent_active, th.soft_disabled),
        )
        self.button_images = create_rounded_button_images(self.config)
        register_primary_button(style, self.button_images)

    # ---------------------------------------------------------------- layout
    def _build_shell(self):
        """Construye el esqueleto: sidebar izquierdo + área de contenido."""
        # --- SIDEBAR (fondo índigo profundo) ---
        sidebar = tk.Frame(self.root, bg=THEME.sidebar_bg, width=self.SIDEBAR_W)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # --- ÁREA DE CONTENIDO (derecha) ---
        content_shell = ttk.Frame(self.root)
        content_shell.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_header(content_shell)
        self._build_body(content_shell)
        self._build_statusbar(content_shell)

    def _build_sidebar(self, sidebar):
        """Contenido del sidebar: marca + navegación + pie."""
        pad_x = 18
        # --- Marca superior ---
        # La imagen queda referenciada por assets (keepalive) mientras la app vive.
        brand_img = brand_photo(THEME.accent, THEME.on_accent)
        tk.Label(sidebar, image=brand_img, bg=THEME.sidebar_bg).pack(
            anchor="w", padx=pad_x, pady=(22, 4))

        tk.Label(sidebar, text="Reportes Financieros",
                 bg=THEME.sidebar_bg, fg=THEME.sidebar_text,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=pad_x)
        tk.Label(sidebar, text="Departamento Financiero",
                 bg=THEME.sidebar_bg, fg=THEME.sidebar_text_dim,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=pad_x, pady=(0, 18))

        # --- Navegación ---
        nav_list = tk.Frame(sidebar, bg=THEME.sidebar_bg)
        nav_list.pack(fill=tk.X, pady=(6, 0))
        for key, label, _sub, chip in self.NAV:
            self._create_nav_row(nav_list, key, label, chip)

        # --- Pie del sidebar ---
        tk.Label(sidebar, text=f"© {datetime.date.today().year}",
                 bg=THEME.sidebar_bg, fg=THEME.sidebar_text_dim,
                 font=("Segoe UI", 8)).pack(side=tk.BOTTOM, anchor="w", padx=pad_x, pady=14)

    def _create_nav_row(self, parent, key, label, chip):
        """Fila de navegación: chip + texto + indicador activo.

        MOTIVO: un item clicable de aspecto moderno (hover suave y estado
        activo resaltado) sin depender de fuentes de iconos externas.
        """
        row_bg = THEME.sidebar_bg
        row = tk.Frame(parent, bg=row_bg, height=42, cursor="hand2")
        row.pack(fill=tk.X, pady=2)
        row.pack_propagate(False)

        # Indicador activo (barra vertical de acento).
        indicator = tk.Frame(row, bg=THEME.sidebar_bg, width=3)
        indicator.pack(side=tk.LEFT, fill=tk.Y)
        indicator.pack_propagate(False)

        content = tk.Frame(row, bg=row_bg)
        content.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))

        # Chip redondeado con las iniciales del módulo (ícono seguro).
        chip_canvas = tk.Canvas(content, width=24, height=24, bg=row_bg,
                                highlightthickness=0)
        chip_canvas.pack(side=tk.LEFT, padx=(0, 10))
        chip_photo = rounded_photo(THEME.sidebar_hover, radius=7, size=24)
        self._nav_photos[(key, "normal")] = chip_photo
        chip_active = rounded_photo(THEME.accent, radius=7, size=24)
        self._nav_photos[(key, "active")] = chip_active
        chip_img = chip_canvas.create_image(12, 12, image=chip_photo)
        chip_txt = chip_canvas.create_text(
            12, 12, text=chip, fill=THEME.sidebar_text,
            font=("Segoe UI", 8, "bold"))

        label_w = tk.Label(content, text=label, bg=row_bg, fg=THEME.sidebar_text,
                           font=("Segoe UI", 10))
        label_w.pack(side=tk.LEFT)

        def _set_colors(bg, txt, chip_photo_img, show_indicator):
            row.configure(bg=bg)
            content.configure(bg=bg)
            chip_canvas.configure(bg=bg)
            label_w.configure(bg=bg, fg=txt)
            indicator.configure(bg=THEME.accent if show_indicator else bg)
            chip_canvas.itemconfigure(chip_img, image=chip_photo_img)

        def on_enter(_e):
            if self._current != key:
                _set_colors(THEME.sidebar_hover, THEME.sidebar_text,
                            self._nav_photos[(key, "normal")], False)

        def on_leave(_e):
            is_active = self._current == key
            _set_colors(THEME.sidebar_active if is_active else THEME.sidebar_bg,
                        THEME.sidebar_text,
                        self._nav_photos[(key, "active") if is_active else (key, "normal")],
                        is_active)

        def on_click(_e):
            self.select_page(key)

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        row.bind("<Button-1>", on_click)
        for w in (content, chip_canvas, label_w):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        self._nav_rows[key] = {
            "row": row, "content": content, "chip": chip_canvas, "label": label_w,
            "indicator": indicator, "chip_img": chip_img,
        }

    def _build_header(self, content_shell):
        """Cabecera superior (blanca) con el título del módulo activo."""
        header = ttk.Frame(content_shell, style="AppHeader.TFrame", padding=(26, 16))
        header.pack(fill=tk.X)

        self.header_title = ttk.Label(header, text="", style="PageTitle.TLabel")
        self.header_title.pack(anchor="w")
        self.header_sub = ttk.Label(header, text="", style="PageSub.TLabel")
        self.header_sub.pack(anchor="w", pady=(2, 0))

        ttk.Separator(content_shell).pack(fill=tk.X)

    def _build_body(self, content_shell):
        """Zona central donde se muestran/ocultan las páginas de los módulos."""
        body = ttk.Frame(content_shell, padding=(18, 14, 18, 0))
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.body = body

        # Se crean las 4 vistas (misma lógica de siempre). Se ubican en la misma
        # celda del grid y se muestran una a la vez según el item del sidebar.
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
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()  # oculto hasta seleccionar

    def _build_statusbar(self, content_shell):
        """Barra de estado persistente al pie del área de contenido."""
        status = ttk.Frame(content_shell, style="AppHeader.TFrame", padding=(26, 10, 26, 12))
        status.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Separator(content_shell, orient="horizontal").pack(fill=tk.X, side=tk.BOTTOM)

        # Barra de estado en la parte baja del contenido.
        self.status_label = ttk.Label(status, text="Estado: Listo", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT)

        self.footer_progress = ttk.Progressbar(status, length=180, mode="determinate", maximum=100)
        self.footer_progress.pack(side=tk.LEFT, padx=16)

        footer_text = f"© {datetime.date.today().year} Departamento Financiero"
        tk.Label(status, text=footer_text, bg=THEME.surface, fg=THEME.muted,
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT)

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

        # Cabecera del módulo activo.
        meta = next((m for m in self.NAV if m[0] == key), None)
        if meta:
            self.header_title.config(text=meta[1])
            self.header_sub.config(text=meta[2])

        # Mostrar/ocultar páginas.
        for k, page in self._pages.items():
            if k == key:
                page.grid()
            else:
                page.grid_remove()

        # Reflejar el item activo en el sidebar.
        for k, data in self._nav_rows.items():
            is_active = (k == key)
            bg = THEME.sidebar_active if is_active else THEME.sidebar_bg
            row = data["row"]
            row.configure(bg=bg)
            data["content"].configure(bg=bg)
            data["chip"].configure(bg=bg)
            data["label"].configure(bg=bg, fg=THEME.sidebar_text)
            data["indicator"].configure(bg=THEME.accent if is_active else bg)
            data["chip"].itemconfigure(
                data["chip_img"],
                image=self._nav_photos[(k, "active") if is_active else (k, "normal")])

    # ------------------------------------------------------------ estado
    @main_thread
    def update_status(self, message: str):
        """Actualiza el texto de estado de la barra inferior."""
        self.status_label.config(text=f"Estado: {message}")
        self.root.update_idletasks()

    @main_thread
    def update_progress(self, progress: int):
        """Actualiza la barra de progreso de la barra de estado.

        MOTIVO: antes este método solo imprimía en consola; ahora refleja el
        avance en la interfaz sin cambiar su firma (compatibilidad total).
        """
        if progress is not None:
            self.footer_progress.config(value=progress)
        self.root.update_idletasks()

    @main_thread
    def update_display(self, message: str, progress: int):
        """Método unificado que actualiza estado y progreso."""
        self.update_status(message)
        self.update_progress(progress)
