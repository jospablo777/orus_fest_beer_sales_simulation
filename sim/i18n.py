"""Text shown in figures and videos, in English and Spanish.

The organizer pages exist in both languages, so their figures take a `lang` argument.
Identifiers and comments stay in English; only the displayed strings are translated.
"""

LABELS = {
    "en": {
        "stage": "STAGE", "bar_zone": "BAR", "tables": "tables", "vendors": "vendors",
        "entrance": "entrance",
        "dot_note": "Each dot is one attendee. Stage at the top, bar at the bottom.",
        "watching": "watching / moving", "to_line": "walking to a line",
        "ticket_line": "ticket line", "tap_line": "exchange / bar line",
        "wait_seller": "waiting for a seller", "seller": "roaming seller",
        "people_inside": "People inside", "people_in_lines": "People in lines",
        "wait_last15": "Typical time in line, last 15 min (min)",
        "in_lines": "in lines", "wait": "typical wait of", "beers_sold": "beers sold",
        "setup_2026": "2026 (ticket window, then exchange)",
        "setup_plan": "Plan (pay and get the beer at the bar)",
        "minutes": "min",
        "density_label": "people per m², mean",
    },
    "es": {
        "stage": "ESCENARIO", "bar_zone": "BARRA", "tables": "mesas", "vendors": "puestos",
        "entrance": "entrada",
        "dot_note": "Cada punto es una persona. Escenario arriba, barra abajo.",
        "watching": "viendo el show / caminando", "to_line": "caminando a una fila",
        "ticket_line": "fila de fichas", "tap_line": "fila de canje / barra",
        "wait_seller": "esperando a un vendedor", "seller": "vendedor en pista",
        "people_inside": "Personas dentro", "people_in_lines": "Personas en filas",
        "wait_last15": "Tiempo típico en fila, últimos 15 min (min)",
        "in_lines": "en filas", "wait": "espera típica de", "beers_sold": "cervezas vendidas",
        "setup_2026": "2026 (caja de fichas y luego canje)",
        "setup_plan": "Plan (se paga y se recibe la cerveza en la barra)",
        "minutes": "min",
        "density_label": "personas por m², promedio",
    },
}


def labels(lang: str) -> dict:
    return LABELS[lang]
