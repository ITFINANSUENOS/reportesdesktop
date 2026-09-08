# src/views/widgets.py
#
# Componentes visuales COMPARTIDOS (customtkinter).
#
# MOTIVO DEL CAMBIO: tkinter/ttk no permite un look realmente moderno
# (esquinas finas, sombras, widgets pulidos). Se migró la capa visual a
# customtkinter manteniendo los MISMOS helpers y firmas para que los
# controladores/servicios no cambien (solo se reescribe la presentación).
import customtkinter as ctk

from src.views.config_view.theme import THEME, FONT_FAMILY
from src.views.config_view.theme import SPACE_CARD_GAP, SPACE_ENTRY_BTN, DESC_WRAP

# Fuentes base (escala consistente).
_FONT_LABEL = (FONT_FAMILY, 11)
_FONT_LABEL_BOLD = (FONT_FAMILY, 12, "bold")
_FONT_SMALL = (FONT_FAMILY, 10)
_FONT_ACTION = (FONT_FAMILY, 12, "bold")


def add_scroll_area(frame) -> ctk.CTkScrollableFrame:
    """Crea el área con scroll de las páginas (customtkinter ya trae scrollbar).

    Retorna el contenedor donde la página coloca sus tarjetas.
    """
    scroll = ctk.CTkScrollableFrame(frame, fg_color=THEME.bg, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)
    return scroll


def card(parent, title=None) -> ctk.CTkFrame:
    """Tarjeta blanca redondeada con título (si se indica).

    Devuelve el contenedor interior transparente donde se ponen los campos.
    """
    frame = ctk.CTkFrame(parent, fg_color=THEME.surface, corner_radius=14,
                         border_width=1, border_color=THEME.border)
    frame.pack(fill="x", padx=4, pady=(0, SPACE_CARD_GAP))
    if title:
        label = ctk.CTkLabel(frame, text=f" {title} ", text_color=THEME.accent,
                             font=_FONT_LABEL_BOLD, anchor="w")
        label.pack(anchor="w", padx=18, pady=(12, 0))
    inner = ctk.CTkFrame(frame, fg_color="transparent")
    inner.pack(fill="x", padx=18, pady=(6, 16))
    return inner


def description(parent, text: str) -> None:
    """Texto descriptivo dentro de una tarjeta (ancho de texto controlado)."""
    ctk.CTkLabel(parent, text=text, text_color=THEME.muted,
                 font=_FONT_SMALL, wraplength=DESC_WRAP, justify="left",
                 anchor="w").pack(anchor="w", pady=(0, 6))


def file_field(parent, label_text: str, var, command) -> None:
    """Campo de archivo canónico: etiqueta + entrada readonly + botón."""
    ctk.CTkLabel(parent, text=label_text, text_color=THEME.text,
                 font=_FONT_LABEL, anchor="w").pack(anchor="w", pady=(12, 6))

    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x")
    row.grid_columnconfigure(0, weight=1)

    entry = ctk.CTkEntry(row, textvariable=var, state="readonly",
                         fg_color=THEME.surface_alt, text_color=THEME.muted,
                         height=36, corner_radius=8, border_width=1,
                         border_color=THEME.border, font=_FONT_SMALL)
    entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_ENTRY_BTN))

    button = ctk.CTkButton(row, text="Seleccionar...", command=command,
                           width=140, height=36, corner_radius=8,
                           fg_color=THEME.accent, hover_color=THEME.accent_hover,
                           text_color="#FFFFFF", font=(FONT_FAMILY, 11))
    button.grid(row=0, column=1)


def action_button(parent, text: str, command) -> ctk.CTkButton:
    """Botón de acción principal (acento, redondeado y centrado)."""
    button = ctk.CTkButton(parent, text=text, command=command, height=44,
                           corner_radius=10, fg_color=THEME.accent,
                           hover_color=THEME.accent_hover, text_color="#FFFFFF",
                           font=_FONT_ACTION)
    button.pack(pady=(18, 4))
    return button


def status_area(parent, initial_text: str = ""):
    """Área de estado + progreso (estilo común donde un módulo la usa)."""
    label = ctk.CTkLabel(parent, text=initial_text, text_color=THEME.muted,
                         font=_FONT_SMALL)
    label.pack(pady=(12, 6))
    bar = ctk.CTkProgressBar(parent, height=12, corner_radius=6,
                             fg_color=THEME.surface_alt,
                             progress_color=THEME.accent)
    bar.set(0)
    bar.pack(fill="x")
    return label, bar


def note_label(parent, text: str) -> None:
    """Título de sección pequeño dentro de una tarjeta."""
    ctk.CTkLabel(parent, text=text, text_color=THEME.text,
                 font=_FONT_LABEL_BOLD, anchor="w").pack(anchor="w")
