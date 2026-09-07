# =============================================================================
# src/views/config_view/theme.py
# -----------------------------------------------------------------------------
# Tema visual central de la aplicación (estilo "Fluent light corporativo").
#
# MOTIVO DE ESTE MÓDULO:
#   1) Antes del rediseño, los colores estaban repartidos por cada vista y varios
#      estilos de ttk se usaban SIN definirse ("Title.TLabel", "Status.TLabel",
#      "Accent.TButton"...), con lo que ttk los resolvía con el aspecto por
#      defecto del tema "clam".
#   2) tkinter no pinta esquinas redondeadas nativas. Para lograr un look
#      moderno (tarjetas y botones con radio real) usamos imágenes RGBA 9-patch
#      generadas por assets.py y aquí las registramos como ELEMENTOS de los
#      estilos de ttk.
#   Este módulo NO contiene lógica de negocio: solo apariencia.
# =============================================================================
from dataclasses import dataclass

# Fuente por defecto: "Segoe UI" es la tipografía moderna estándar de Windows.
FONT_FAMILY = "Segoe UI"


@dataclass(frozen=True)
class AppTheme:
    """Paleta clara pulida (único tema; sin modo oscuro)."""

    # --- Fondos / superficies -------------------------------------------------
    bg: str = "#E9EEF5"           # Fondo de las páginas (detrás de las tarjetas)
    surface: str = "#FFFFFF"      # Tarjetas / paneles
    surface_alt: str = "#F1F5FA"  # Gris muy suave (campos, hover)
    border: str = "#D5DCE8"       # Bordes de entradas y separadores

    # --- Texto ----------------------------------------------------------------
    text: str = "#1C2437"
    muted: str = "#5B6B84"
    on_accent: str = "#FFFFFF"

    # --- Acento (índigo corporativo) ------------------------------------------
    accent: str = "#2563EB"
    accent_hover: str = "#1D4ED8"
    accent_active: str = "#1E40AF"
    accent_soft: str = "#E1EBFD"

    # --- Sidebar (índigo profundo, para contraste sobre el tema claro) --------
    sidebar_bg: str = "#121A36"
    sidebar_hover: str = "#1E2A52"
    sidebar_active: str = "#2A3A78"
    sidebar_text: str = "#E7ECF9"
    sidebar_text_dim: str = "#7C89B3"

    # --- Botones secundarios (gris suave, estilo "ghost") ---------------------
    soft_bg: str = "#E7ECF4"
    soft_hover: str = "#DCE3EF"
    soft_pressed: str = "#CBD5E5"
    soft_disabled: str = "#F0F3F8"

    # --- Semánticos -----------------------------------------------------------
    success: str = "#16A34A"
    success_soft: str = "#E4F5EA"
    danger: str = "#DC2626"
    danger_soft: str = "#FCECEC"


# Instancia por defecto; las vistas toman colores de aquí (p. ej. canvas).
THEME = AppTheme()


# ---------------------------------------------------------------------------
# Escala de espaciado (tokens únicos usados por widgets.py).
# MOTIVO: antes cada vista usaba sus propios paddings (15, 18, 20...) y el
# resultado se veía distinto entre módulos. Centralizar aquí la medida hace que
# todas las páginas compartan el mismo ritmo vertical/horizontal.
# ---------------------------------------------------------------------------
SPACE_PAGE_TOP = 6       # aire superior del área con scroll de cada página
SPACE_PAGE_BOTTOM = 26   # aire inferior antes del final del scroll
SPACE_CARD_GAP = 14      # separación entre tarjetas
SPACE_CARD_PAD = 18      # padding interior de las tarjetas
SPACE_FIELD_TOP = 10     # espacio encima de la etiqueta de cada campo
SPACE_FIELD_BOTTOM = 6   # espacio entre etiqueta y su campo
SPACE_ENTRY_BTN = 8      # espacio entre el campo y su botón "Seleccionar"
SPACE_ACTION_TOP = 18    # espacio antes del botón de acción principal
DESC_WRAP = 860          # ancho de texto de las descripciones largas


def apply_theme(style) -> None:
    """Aplica la paleta a los estilos de ttk (sin tocar layouts).

    Se llama UNA sola vez desde la ventana principal, antes de crear widgets,
    para que todo el árbol de la app (incluidas sub-pestañas) herede el tema.
    """
    # Fuente base para todos los widgets que no definan la suya.
    style.configure(".", font=(FONT_FAMILY, 10))

    # --- Contenedores ---------------------------------------------------------
    style.configure("TFrame", background=THEME.bg)
    style.configure("Card.TFrame", background=THEME.surface)
    style.configure("Sidebar.TFrame", background=THEME.sidebar_bg)
    style.configure("AppHeader.TFrame", background=THEME.surface)

    # --- Etiquetas ------------------------------------------------------------
    style.configure("TLabel", background=THEME.bg, foreground=THEME.text)
    style.configure("Card.TLabel", background=THEME.surface, foreground=THEME.text)
    style.configure("CardHeader.TLabel", background=THEME.surface,
                    foreground=THEME.text, font=(FONT_FAMILY, 11, "bold"))
    style.configure("Title.TLabel", background=THEME.bg, foreground=THEME.text,
                    font=(FONT_FAMILY, 22, "bold"))
    style.configure("PageTitle.TLabel", background=THEME.surface, foreground=THEME.text,
                    font=(FONT_FAMILY, 19, "bold"))
    style.configure("PageSub.TLabel", background=THEME.surface, foreground=THEME.muted,
                    font=(FONT_FAMILY, 10))
    style.configure("Subtitle.TLabel", background=THEME.bg, foreground=THEME.muted,
                    font=(FONT_FAMILY, 10))
    style.configure("Section.TLabel", background=THEME.surface, foreground=THEME.text,
                    font=(FONT_FAMILY, 11, "bold"))
    style.configure("Muted.TLabel", background=THEME.bg, foreground=THEME.muted)
    style.configure("Status.TLabel", background=THEME.surface, foreground=THEME.muted,
                    font=(FONT_FAMILY, 9))
    # Éxito: se aplica sobre etiquetas de ruta dentro de tarjetas blancas.
    style.configure("Success.TLabel", background=THEME.surface, foreground=THEME.success,
                    font=(FONT_FAMILY, 9, "bold"))
    style.configure("Error.TLabel", background=THEME.surface, foreground=THEME.danger,
                    font=(FONT_FAMILY, 10, "bold"))

    # --- Etiqueta de las LabelFrames (título de tarjeta) ----------------------
    style.configure("TLabelframe.Label", background=THEME.surface,
                    foreground=THEME.accent, font=(FONT_FAMILY, 10, "bold"))

    # --- Entradas -------------------------------------------------------------
    style.configure("TEntry", fieldbackground=THEME.surface, foreground=THEME.text,
                    insertcolor=THEME.text, bordercolor=THEME.border,
                    lightcolor=THEME.border, darkcolor=THEME.border,
                    relief="solid", padding=6)
    style.map("TEntry",
              bordercolor=[("focus", THEME.accent)],
              lightcolor=[("focus", THEME.accent)],
              darkcolor=[("focus", THEME.accent)])
    style.configure("Readonly.TEntry", fieldbackground=THEME.surface_alt,
                    foreground=THEME.muted, readonlybackground=THEME.surface_alt)

    # --- Checkbuttons ---------------------------------------------------------
    style.configure("TCheckbutton", background=THEME.bg, foreground=THEME.text,
                    font=(FONT_FAMILY, 10))
    style.map("TCheckbutton", background=[("active", THEME.bg)])
    style.configure("Card.TCheckbutton", background=THEME.surface, foreground=THEME.text)
    style.map("Card.TCheckbutton", background=[("active", THEME.surface)])

    # --- Notebook (pestañas internas de Base Mensual y Centrales) -------------
    style.configure("TNotebook", background=THEME.bg, borderwidth=0, tabmargins=(4, 8, 4, 0))
    style.configure("TNotebook.Tab", background=THEME.surface_alt, foreground=THEME.muted,
                    padding=(18, 8), borderwidth=0, font=(FONT_FAMILY, 10))
    style.map("TNotebook.Tab",
              background=[("selected", THEME.surface), ("active", THEME.surface_alt)],
              foreground=[("selected", THEME.accent), ("active", THEME.text)],
              bordercolor=[("selected", THEME.accent)])

    # --- Progreso, scrollbar y separador --------------------------------------
    style.configure("TProgressbar", background=THEME.accent, troughcolor=THEME.surface_alt,
                    bordercolor=THEME.border, lightcolor=THEME.accent,
                    darkcolor=THEME.accent)
    style.configure("Vertical.TScrollbar", background=THEME.border, troughcolor=THEME.bg,
                    arrowcolor=THEME.muted, relief="flat", borderwidth=0)
    style.configure("Horizontal.TScrollbar", background=THEME.border, troughcolor=THEME.bg,
                    arrowcolor=THEME.muted, relief="flat", borderwidth=0)
    style.configure("TSeparator", background=THEME.border)


# ---------------------------------------------------------------------------
# Registro de estilos con imágenes redondeadas (9-patch).
# ---------------------------------------------------------------------------
# Las imágenes (generadas en assets.py) se registran como ELEMENTOS de ttk y
# luego se sustituye el LAYOUT del estilo para que dibuje la imagen estirada.
# El parámetro 'border' de element_create indica cuántos píxeles de cada borde
# NO se estiran: así las esquinas redondeadas se conservan a cualquier tamaño.
# NOTA: esto solo es seguro para BOTONES (sus elementos no dibujan texto por
# dentro). En las LabelFrames no se usa porque su etiqueta la dibuja el tema.

_BTN_RADIUS = 10


def register_card_style(style, card_photo=None) -> None:
    """Estiliza las LabelFrames como 'tarjetas' blancas limpias.

    MOTIVO: se probó sustituir el borde de la LabelFrame por una imagen
    redondeada (9-patch), pero ttk dibuja el título/etiqueta de la LabelFrame
    dentro del elemento de borde de su tema; reemplazarlo dejaba la tarjeta en
    blanco. Para NO romper nada, las tarjetas se mantienen con el widget nativo
    y un borde sutil y fondo blanco (look plano moderno). Los botones sí
    conservan esquinas redondeadas vía imágenes (funcionan correctamente).
    """
    style.configure(
        "TLabelframe",
        background=THEME.surface,
        bordercolor=THEME.border,
        relief="solid",
        borderwidth=1,
    )


def _register_filled_button(style, name: str, element: str, photos: dict) -> None:
    """Helper: botón de relleno uniforme redondeado con 4 estados."""
    style.element_create(
        element, "image",
        photos["normal"],
        ("active", photos["hover"]),
        ("pressed", photos["pressed"]),
        ("disabled", photos["disabled"]),
        border=_BTN_RADIUS, sticky="nsew",
    )
    style.layout(name, [
        (element, {
            "sticky": "nsew",
            "children": [
                ("Button.padding", {
                    "sticky": "nsew",
                    "children": [("Button.label", {"sticky": "nsew"})],
                }),
            ],
        }),
    ])


def register_secondary_button(style, photos: dict) -> None:
    """Botón secundario (gris suave): TODOS los 'TButton' por defecto."""
    _register_filled_button(style, "TButton", "Fluent.Secondary.button", photos)
    style.configure("TButton", foreground=THEME.text, anchor="center",
                    padding=(14, 7), font=(FONT_FAMILY, 10))
    style.map("TButton", foreground=[("disabled", THEME.muted)])


def register_accent_button(style, photos: dict) -> None:
    """Botón de acento sólido (usado en 'Centrales de Riesgo')."""
    _register_filled_button(style, "Accent.TButton", "Fluent.Accent.button", photos)
    style.configure("Accent.TButton", foreground=THEME.on_accent, anchor="center",
                    padding=(16, 8), font=(FONT_FAMILY, 10, "bold"))
    style.map("Accent.TButton", foreground=[("disabled", THEME.on_accent)])


def register_primary_button(style, images: dict) -> None:
    """Botón principal redondeado 'Modern.TButton' (CTAs grandes).

    MOTIVO: se conserva el mecanismo de imágenes que ya existía (y que las
    vistas usan con el nombre 'Modern.TButton'), pero ahora las imágenes toman
    los colores del tema central.
    """
    style.element_create(
        "Modern.Button.background", "image",
        images["normal"],
        ("active", images["hover"]),
        ("pressed", images["pressed"]),
        border=_BTN_RADIUS, sticky="nsew",
    )
    style.layout("Modern.TButton", [
        ("Modern.Button.background", {"sticky": "nsew"}),
        ("Button.padding", {
            "sticky": "nsew",
            "children": [("Button.label", {"sticky": "nsew"})],
        }),
    ])
    style.configure("Modern.TButton", font=(FONT_FAMILY, 11, "bold"),
                    foreground=THEME.on_accent, anchor="center", padding=10)
