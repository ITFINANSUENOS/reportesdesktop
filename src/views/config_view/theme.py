# =============================================================================
# src/views/config_view/theme.py
# -----------------------------------------------------------------------------
# Paleta y tokens visuales centrales (customtkinter).
#
# MOTIVO DEL CAMBIO: la interfaz migró de tkinter/ttk a customtkinter, por lo
# que se eliminaron las funciones que registraban estilos ttk (apply_theme,
# register_card_style, register_secondary/accent/primary_button) y los helpers
# 9-patch asociados (código muerto). Este módulo queda como única fuente de la
# paleta, tipografía y escala de espaciado que usan las vistas.
# No contiene lógica de negocio: solo apariencia.
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

    # --- Semánticos -----------------------------------------------------------
    success: str = "#16A34A"
    success_soft: str = "#E4F5EA"
    danger: str = "#DC2626"
    danger_soft: str = "#FCECEC"


# Instancia por defecto; las vistas toman colores de aquí.
THEME = AppTheme()


# ---------------------------------------------------------------------------
# Escala de espaciado (tokens únicos usados por widgets.py).
# MOTIVO: todas las páginas comparten el mismo ritmo vertical/horizontal.
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
