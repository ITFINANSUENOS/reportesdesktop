from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ConveniosConfig:
    # MOTIVO DEL CAMBIO: las hojas 'AC FS' y 'AC ARP' se reemplazaron por UNA
    # hoja única llamada 'CARTERA' con estructura distinta (mismos valores):
    #   Identificacion -> CEDULA
    #   Documentos     -> FACTURA
    #   Proyectado Total Con Mora -> saldofac (saldo)
    # La empresa se deduce por el prefijo del documento: si 'Documentos'
    # empieza con 'DF' es Finansueños (equivale a la antigua AC FS); el resto
    # es Arpesod (equivale a la antigua AC ARP).
    required_sheets: List[str] = field(default_factory=lambda:[
                'CARTERA', 'CODEUDORES', 
                'CASA DE COBRANZA', 'EMPLEADOS ACTUALES', 
                'PAGOS BANCOLOMBIA', 'PAGOS EFECTY','PAGOS ECOLLECT'])

    # Columnas usadas de las hojas "auxiliares" (AC FS/ARP ya no son hojas).
    sheet_columns: Dict[str, List[str]] = field(default_factory=lambda:{
                'CODEUDORES': ['CODEUDOR', 'FACTURA'],
                'CASA DE COBRANZA': ['FACTURA', 'cobra'],
                'EMPLEADOS ACTUALES': ['vincedula', 'ACTIVO'],
                'PAGOS BANCOLOMBIA': ['No.', 'Fecha', 'Detalle 1', 'Detalle 2', 'Referencia 1', 'Referencia 2', 'Valor'],
                'PAGOS EFECTY': ['No', 'Identificación', 'Valor', 'N° de Autorización', 'Fecha'],
                'PAGOS ECOLLECT': ['#TRANS', 'REFERENCIA 1', 'VALOR', 'FECHA INICIO', 'CANAL DE PAGO']
            })
    rename_columns: Dict[str, Dict[str, str]] = field(default_factory=lambda:{
                'CODEUDORES': {'FACTURA': 'CODEUDOR', 'CODEUDOR': 'DOCUMENTO_CODEUDOR'},
                'CASA DE COBRANZA': {'cobra': 'CASA COBRANZA'},
                'EMPLEADOS ACTUALES': {'ACTIVO': 'ESTADO_EMPLEADO'}
            })

    # --- Hoja única de cartera (CARTERA) ---
    ac_sheet_name: str = 'CARTERA'
    # Mapeo de columnas físicas de CARTERA -> nombres internos genéricos.
    ac_columns: Dict[str, str] = field(default_factory=lambda:{
        'Identificacion': 'CEDULA',
        'Documentos': 'FACTURA',
        'Proyectado Total Con Mora': 'saldofac',
    })
    # Prefijo que identifica a Finansueños (equivale a la antigua hoja AC FS).
    ac_fs_prefix: str = 'DF'
    # Nombres internos que la lógica espera por empresa (igual que antes).
    ac_fs_suffix_map: Dict[str, str] = field(default_factory=lambda:{
        'CEDULA': 'CEDULA_FS', 'FACTURA': 'FACTURA_FS', 'saldofac': 'SALDO_FS',
    })
    ac_arp_suffix_map: Dict[str, str] = field(default_factory=lambda:{
        'CEDULA': 'CEDULA_ARP', 'FACTURA': 'FACTURA_ARP', 'saldofac': 'SALDO_ARP',
    })

    merge_config: Dict[str, Dict] = field(default_factory=lambda:{
                'efecty': {
                    'empleados': ('Identificación', 'vincedula'),
                    'ac_fs': ('Identificación', 'CEDULA_FS'),
                    'ac_arp': ('Identificación', 'CEDULA_ARP'),
                    'casa_cobranza': ('FACTURA FINAL', 'FACTURA'),
                    'codeudores': ('Identificación', 'DOCUMENTO_CODEUDOR')
                },
                'bancolombia': {
                    'empleados': ('Referencia 1', 'vincedula'),
                    'ac_fs': ('Referencia 1', 'CEDULA_FS'),
                    'ac_arp': ('Referencia 1', 'CEDULA_ARP'),
                    'casa_cobranza': ('FACTURA FINAL', 'FACTURA'),
                    'codeudores': ('Referencia 1', 'DOCUMENTO_CODEUDOR')
                },
                'ecollect': {
                    'empleados':('REFERENCIA 1','vincedula'),
                    'ac_fs': ('REFERENCIA 1', 'CEDULA_FS'),
                    'ac_arp': ('REFERENCIA 1', 'CEDULA_ARP'),
                    'casa_cobranza': ('FACTURA FINAL', 'FACTURA'),
                    'codeudores': ('REFERENCIA 1', 'DOCUMENTO_CODEUDOR')
                    }
            })
    output_filename: str = "reporte_cruce_convenios.xlsx"
