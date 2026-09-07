# src/views/widgets.py
#
# Componentes visuales COMPARTIDOS por todos los módulos.
#
# MOTIVO DE ESTE MÓDULO:
#   Antes, cada vista copiaba el bloque de canvas+scroll con proporciones y
#   paddings distintos (5-90-5, 10-80-10, tarjetas con padding 15/18/20...),
#   lo que hacía que los módulos se vieran con ritmos diferentes. Aquí se
#   definen UNA VEZ las piezas que usan todas las páginas (área con scroll,
#   tarjeta, campo de archivo, botón de acción) para que la interfaz sea
#   visualmente consistente en toda la aplicación. No contiene lógica.
import tkinter as tk
from tkinter import ttk

from src.views.config_view.theme import THEME, FONT_FAMILY
from src.views.config_view.theme import (
    SPACE_PAGE_TOP,
    SPACE_PAGE_BOTTOM,
    SPACE_CARD_GAP,
    SPACE_CARD_PAD,
    SPACE_FIELD_TOP,
    SPACE_FIELD_BOTTOM,
    SPACE_ENTRY_BTN,
    SPACE_ACTION_TOP,
    DESC_WRAP,
)


def add_scroll_area(frame) -> ttk.Frame:
    """Crea el área con scroll estándar dentro de 'frame'.

    Retorna el contenedor central donde cada página coloca su contenido.
    MOTIVO: normaliza el patrón canvas+scrollbar+columna centrada que hoy cada
    vista repetía con proporciones distintas; todas las páginas usan el mismo
    encuadre (columna 5-90-5) y los mismos márgenes verticales.
    """
    canvas = tk.Canvas(frame, bg=THEME.bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)

    scrollable = ttk.Frame(canvas)
    content = ttk.Frame(scrollable)

    # Cada vez que cambie el tamaño del contenido, se recalcula la zona de scroll.
    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")

    # El frame interno adopta el ancho del canvas (contenido fluido al redimensionar).
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Columna central ancha (estilo de todas las páginas).
    scrollable.columnconfigure(0, weight=5)
    scrollable.columnconfigure(1, weight=90)
    scrollable.columnconfigure(2, weight=5)
    content.grid(row=0, column=1, sticky="nsew", pady=(SPACE_PAGE_TOP, SPACE_PAGE_BOTTOM))
    return content


def card(parent, title=None) -> ttk.LabelFrame:
    """Crea y ubica una tarjeta (LabelFrame) con el estilo y espaciado estándar."""
    text = f" {title} " if title else ""
    frame = ttk.LabelFrame(parent, text=text, padding=SPACE_CARD_PAD)
    frame.pack(fill="x", pady=(0, SPACE_CARD_GAP))
    return frame


def description(parent, text: str) -> ttk.Label:
    """Texto descriptivo dentro de una tarjeta (con estilo y ancho comunes)."""
    label = ttk.Label(
        parent,
        text=text,
        style="Card.TLabel",
        wraplength=DESC_WRAP,
        justify="left",
    )
    label.pack(anchor="w", pady=(0, 8))
    return label


def file_field(parent, label_text: str, var, command) -> None:
    """Campo de archivo canónico: etiqueta + Entry readonly + botón.

    MOTIVO: unifica los selectores de archivos de todos los módulos (antes Base
    usaba un chip, Centrales un botón "📂", etc.) en una sola presentación.
    """
    ttk.Label(parent, text=label_text, style="Card.TLabel").pack(
        anchor="w", pady=(SPACE_FIELD_TOP, SPACE_FIELD_BOTTOM))

    row = ttk.Frame(parent, style="Card.TFrame")
    row.pack(fill="x")
    row.columnconfigure(0, weight=1)

    entry = ttk.Entry(row, textvariable=var, state="readonly", style="Readonly.TEntry")
    entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_ENTRY_BTN))
    ttk.Button(row, text="Seleccionar...", command=command).grid(row=0, column=1)


def action_button(parent, text: str, command) -> ttk.Button:
    """Botón de acción principal (único estilo redondeado, centrado).

    MOTIVO: antes cada módulo usaba estilos/alineaciones distintos (algunos
    estiraban el botón a todo el ancho). Con este helper todos los botones
    'Generar/Iniciar/Procesar' se ven y se colocan igual.
    """
    button = ttk.Button(parent, text=text, command=command, style="Modern.TButton")
    button.pack(pady=(SPACE_ACTION_TOP, 4))
    return button


def status_area(parent, initial_text: str = ""):
    """Área de estado + progreso (estilo común donde un módulo la usa)."""
    label = ttk.Label(parent, text=initial_text, style="Muted.TLabel", anchor="center")
    label.pack(fill="x", pady=(14, 2))
    bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
    bar.pack(fill="x", pady=(4, 0))
    return label, bar


def note_label(parent, text: str) -> ttk.Label:
    """Etiqueta secundaria (título de sección) dentro de una tarjeta."""
    label = ttk.Label(parent, text=text, style="CardHeader.TLabel")
    label.pack(anchor="w")
    return label
