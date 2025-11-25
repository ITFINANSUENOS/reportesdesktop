from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ConveniosConfig:
    required_sheets: List[str] = field(default_factory=lambda:[
                'AC FS', 'AC ARP', 'CODEUDORES', 
                'CASA DE COBRANZA', 'EMPLEADOS ACTUALES', 
                'PAGOS BANCOLOMBIA', 'PAGOS EFECTY','PAGOS ECOLLECT'])
    sheet_columns: Dict[str, Dict[str, List[str]]] = field(default_factory=lambda:{
                'AC FS': ['CEDULA', 'FACTURA', 'saldofac', 'ccosto'],
                'AC ARP': ['CEDULA', 'FACTURA', 'saldofac', 'ccosto'],
                'CODEUDORES': ['CODEUDOR', 'FACTURA'],
                'CASA DE COBRANZA': ['FACTURA', 'cobra'],
                'EMPLEADOS ACTUALES': ['vincedula', 'ACTIVO'],
                'PAGOS BANCOLOMBIA': ['No.', 'Fecha', 'Detalle 1', 'Detalle 2', 'Referencia 1', 'Referencia 2', 'Valor'],
                'PAGOS EFECTY': ['No', 'Identificación', 'Valor', 'N° de Autorización', 'Fecha'],
                'PAGOS ECOLLECT': ['#TRANS', 'REFERENCIA 1', 'VALOR', 'FECHA INICIO', 'CANAL DE PAGO']
            })
    rename_columns: Dict[str, Dict[str, str]] = field(default_factory=lambda:{
                'AC FS': {'CEDULA': 'CEDULA_FS', 'FACTURA': 'FACTURA_FS', 'saldofac': 'SALDO_FS', 'ccosto': 'CENTRO_COSTO_FS'},
                'AC ARP': {'CEDULA': 'CEDULA_ARP', 'FACTURA': 'FACTURA_ARP', 'saldofac': 'SALDO_ARP', 'ccosto': 'CENTRO_COSTO_ARP'},
                'CODEUDORES': {'FACTURA': 'CODEUDOR', 'CODEUDOR': 'DOCUMENTO_CODEUDOR'},
                'CASA DE COBRANZA': {'cobra': 'CASA COBRANZA'},
                'EMPLEADOS ACTUALES': {'ACTIVO': 'ESTADO_EMPLEADO'}
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
    

    