# src/views/config_view/assets.py
#
# Generadores de imágenes (PIL, en memoria) para el estilo "Fluent" claro:
# botones y tarjetas con esquinas redondeadas reales mediante la técnica
# 9-patch de ttk (una sola imagen pequeña que ttk estira conservando las
# esquinas), más el ícono de la ventana y la marca del sidebar.
#
# MOTIVO: tkinter no dibuja esquinas redondeadas nativas. La única forma de
# lograr radios redondeados "de verdad" sin dependencias es pintarlos en
# imágenes RGBA y usarlas como elemento de fondo en los estilos de ttk.
from PIL import Image, ImageDraw, ImageTk

# Mantener referencias a los PhotoImage para que Tk no los elimine (GC).
_TK_KEEPALIVE = []


def _make_rounded_rgba(color: str, radius: int, size: int) -> Image.Image:
    """Imagen RGBA con un rectángulo redondeado relleno de 'color'.

    Las esquinas quedan transparentes: así, al estirarse como 9-patch, el fondo
    de la página se asoma por las esquinas y se ve la curva (radio redondeado).
    """
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=color)
    return img


def rounded_photo(color: str, radius: int = 10, size: int = 48) -> ImageTk.PhotoImage:
    """Convierte un rectángulo redondeado en PhotoImage usable por ttk."""
    photo = ImageTk.PhotoImage(_make_rounded_rgba(color, radius, size))
    _TK_KEEPALIVE.append(photo)
    return photo


def button_photos(color: str, hover: str, pressed: str, disabled: str,
                  radius: int = 10) -> dict:
    """Fotos de los 4 estados de un botón redondeado (mismo color de relleno)."""
    return {
        "normal": rounded_photo(color, radius),
        "hover": rounded_photo(hover, radius),
        "pressed": rounded_photo(pressed, radius),
        "disabled": rounded_photo(disabled, radius),
    }


def app_icon_photo(accent: str, on_accent: str, size: int = 64):
    """Ícono de la aplicación (ventana/taskbar): cuadrado redondeado acento
    con tres barras blancas (metáfora de 'reporte/gráfica').
    MOTIVO: tkinter muestra un ícono genérico por defecto; esto lo reemplaza
    por una marca simple y moderna sin guardar archivos en disco."""
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    pad = 6
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=accent)
    bar_w = max(int(size * 0.09), 2)
    gap = size * 0.16
    bars_x = size * 0.16
    base = size - pad - size * 0.16
    # Tres barras verticales de alturas distintas -> parecen un reporte/gráfica.
    for i, h_ratio in enumerate((0.45, 0.7, 0.95)):
        x0 = bars_x + i * gap
        h = base * h_ratio
        y0 = size - pad - h
        draw.rounded_rectangle((x0, y0, x0 + bar_w, size - pad), radius=bar_w // 2,
                               fill=on_accent)
    photo = ImageTk.PhotoImage(img)
    _TK_KEEPALIVE.append(photo)
    return photo


def brand_photo(accent: str, on_accent: str, size: int = 26):
    """Marca pequeña (esquina superior del sidebar): cuadrado redondeado acento
    con una 'R' blanca dibujada como trazo (sin depender de fuentes)."""
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.28), fill=accent)
    # Trazo de la letra "R" con líneas (estilizada).
    t = max(int(size * 0.12), 2)
    x = size * 0.28
    top = size * 0.22
    bot = size * 0.72
    # Pata vertical
    draw.line((x, top, x, bot), fill=on_accent, width=t)
    # Cabeza + curva (arco) mediante arco de rectángulo + línea horizontal
    draw.line((x, top, x + size * 0.34, top), fill=on_accent, width=t)
    draw.arc((x, top, x + size * 0.6, top + size * 0.4), start=270, end=90,
             fill=on_accent, width=t)
    # Diagonal final de la R
    draw.line((x + size * 0.26, size * 0.5, x + size * 0.5, bot), fill=on_accent, width=t)
    photo = ImageTk.PhotoImage(img)
    _TK_KEEPALIVE.append(photo)
    return photo
