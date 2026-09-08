from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class AnticiposConfig:
    """
    Define las REGLAS y PARÁMETROS para generar el reporte de Anticipos.
    Esta clase ahora vive en su propio archivo de modelo.

    MOTIVO DEL CAMBIO: las hojas 'AC FS'/'AC ARP' se reemplazaron por UNA hoja
    única llamada 'CARTERA' (Identificacion/Documentos/Proyectado Total Con
    Mora). La empresa se deduce por el prefijo del documento: 'DF' =
    Finansueños (equivale a AC FS); el resto = Arpesod (equivale a AC ARP).
    Las columnas CENTRO_COSTO_* y ZONA_COBRADOR_* se conservan en el orden de
    columnas pero quedan VACÍAS (la hoja nueva no las trae).
    """
    required_sheets: List[str] = field(default_factory=lambda: ['ONLINE', 'CARTERA'])
    sheet_columns: Dict[str, List[str]] = field(default_factory=lambda: {
        'ONLINE': ['MCNTIPCRU1', 'MCNNUMCRU1', 'MCNVINCULA', 'VINNOMBRE', 'SALDODOC']
    })
    rename_columns: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        'ONLINE': {
            'MCNTIPCRU1': 'TIPO_RECIBO', 'MCNNUMCRU1': 'No', 'MCNVINCULA': 'CEDULA',
            'VINNOMBRE': 'NOMBRE', 'SALDODOC': 'VALOR'
        }
    })

    # --- Hoja única de cartera (CARTERA) ---
    ac_sheet_name: str = 'CARTERA'
    ac_columns: Dict[str, str] = field(default_factory=lambda:{
        'Identificacion': 'CEDULA',
        'Documentos': 'FACTURA',
        'Proyectado Total Con Mora': 'saldofac',
    })
    ac_fs_prefix: str = 'DF'
    ac_fs_suffix_map: Dict[str, str] = field(default_factory=lambda:{
        'CEDULA': 'CEDULA', 'FACTURA': 'FACTURA_FS', 'saldofac': 'ULTIMO_SALDO_FS',
    })
    ac_arp_suffix_map: Dict[str, str] = field(default_factory=lambda:{
        'CEDULA': 'CEDULA', 'FACTURA': 'FACTURA_ARP', 'saldofac': 'ULTIMO_SALDO_ARP',
    })

    output_filename: str = "reporte_anticipos.xlsx"
    column_order_fs: List[str] = field(default_factory=lambda: [
        'ITEM', 'TIPO_RECIBO', 'No', 'CEDULA', 'NOMBRE', 'CENTRO_COSTO_FS',
        'VALOR', 'FACTURA_FS', 'ZONA_COBRADOR_FS', 'OBSERVACIONES', 'CUENTAS_FS',
        'ULTIMO_SALDO_FS', 'VALOR_POSITIVO', 'RESTA_SALDO'
    ])
    column_order_arp: List[str] = field(default_factory=lambda: [
        'ITEM', 'TIPO_RECIBO', 'No', 'CEDULA', 'NOMBRE', 'CENTRO_COSTO_ARP',
        'VALOR', 'FACTURA_ARP', 'ZONA_COBRADOR_ARP', 'OBSERVACIONES', 'CUENTAS_ARP',
        'ULTIMO_SALDO_ARP', 'VALOR_POSITIVO', 'RESTA_SALDO'
    ])
