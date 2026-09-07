# src/views/config_view/style_assets.py
#
# Genera las imágenes RGBA (en memoria, sin guardarlas en disco) que forman el
# botón principal redondeado "Modern.TButton" con sus estados visuales.
#
# MOTIVO DEL CAMBIO:
#   Antes las imágenes se creaban leyendo colores sueltos de AppConfig. Ahora
#   AppConfig expone esos mismos colores desde el tema central (theme.py), así
#   que si algún día se cambia la paleta, el botón principal se regenera solo.
from PIL import Image, ImageDraw, ImageTk


def create_rounded_button_images(config, width=170, height=44, radius=10):
    """
    Genera imágenes en memoria para los estados del botón con esquinas
    redondeadas (normal, hover, presionado).

    Retorna un diccionario con las imágenes listas para Tkinter.
    """
    # 'config' es AppConfig, que expone accent_color / secondary_color /
    # button_pressed_color como alias del tema central (theme.py).
    def create_image(color):
        """Crea una imagen redondeada en memoria con el color dado."""
        image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            ((0, 0), (width, height)),
            fill=color,
            radius=radius,
        )
        return image

    # Crear las imágenes (solo en memoria)
    normal_img = create_image(config.accent_color)
    hover_img = create_image(config.secondary_color)
    pressed_img = create_image(config.button_pressed_color)

    # Convertirlas a PhotoImage (para Tkinter)
    normal_photo = ImageTk.PhotoImage(normal_img)
    hover_photo = ImageTk.PhotoImage(hover_img)
    pressed_photo = ImageTk.PhotoImage(pressed_img)

    # Retornar un diccionario con todas
    return {
        "normal": normal_photo,
        "hover": hover_photo,
        "pressed": pressed_photo,
    }
