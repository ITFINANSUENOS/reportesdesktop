# src/views/config_view/assets.py
#
# Genera en memoria el ícono de la aplicación (ventana/taskbar).
#
# MOTIVO DEL CAMBIO: se migró a customtkinter y se eliminaron los helpers
# 9-patch de botones/tarjetas de la etapa ttk (código muerto). Solo se conserva
# el ícono, que customtkinter reutiliza desde la ventana principal.
from PIL import Image, ImageDraw, ImageTk

# Mantener referencias a los PhotoImage para que Tk no los elimine (GC).
_TK_KEEPALIVE = []


def app_icon_photo(accent: str, on_accent: str, size: int = 64):
    """Ícono de la aplicación: cuadrado redondeado acento con tres barras
    blancas (metáfora de 'reporte/gráfica'). Se genera sin guardar archivos."""
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    pad = 6
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=accent)
    bar_w = max(int(size * 0.09), 2)
    gap = size * 0.16
    bars_x = size * 0.16
    base = size - pad - size * 0.16
    for i, h_ratio in enumerate((0.45, 0.7, 0.95)):
        x0 = bars_x + i * gap
        h = base * h_ratio
        y0 = size - pad - h
        draw.rounded_rectangle((x0, y0, x0 + bar_w, size - pad), radius=bar_w // 2,
                               fill=on_accent)
    photo = ImageTk.PhotoImage(img)
    _TK_KEEPALIVE.append(photo)
    return photo
