# src/views/config_view/config_view.py

# Configuración general de la ventana + acceso al tema central.
#
# MOTIVO DEL CAMBIO:
#   Antes, la paleta de colores vivía aquí en forma de atributos sueltos que
#   además quedaban desactualizados respecto a lo que las vistas usaban
#   (colores fijos "#F0F0F0", "#ECECEC" repartidos por cada archivo).
#   Ahora la paleta real está en AppTheme (theme.py) y AppConfig conserva
#   SOLO la configuración de la ventana (título, tamaño, nombre de salida) y
#   expone propiedades de compatibilidad para que el código existente
#   (main_window, style_assets) no se rompa.
from src.views.config_view.theme import AppTheme


class AppConfig:
    title: str = "Procesador de Reportes Financieros"

    # Ventana grande y redimensionable. Parte del ancho lo ocupa el sidebar.
    geometry: str = "1280x800"
    min_width: int = 1080
    min_height: int = 700

    output_filename: str = "reporte_financiero.xlsx"

    def __init__(self):
        self.theme = AppTheme()

    # --- Accesos de compatibilidad (alias hacia el tema central) -------------
    # Se mantienen los MISMOS nombres de atributo que usaban main_window y
    # style_assets, de modo que ninguna otra parte del código necesite cambios.
    @property
    def bg_color(self) -> str:
        return self.theme.bg

    @property
    def accent_color(self) -> str:
        return self.theme.accent

    @property
    def secondary_color(self) -> str:
        return self.theme.accent_hover

    @property
    def text_color(self) -> str:
        return self.theme.text

    @property
    def button_text_color(self) -> str:
        return self.theme.on_accent

    @property
    def button_pressed_color(self) -> str:
        return self.theme.accent_active
