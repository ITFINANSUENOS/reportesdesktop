import pandas as pd

class DataCreditoModel:
    """Gestiona los datos y la lógica de negocio para el reporte de Datacredito."""

    # CONFIGURACIÓN ESPECÍFICA PARA ARPESOD
    COLUMNAS_ARPESOD = [
        'TIPO DE IDENTIFICACION', 'NUMERO DE IDENTIFICACION', 'NUMERO DE LA CUENTA U OBLIGACION', 
        'NOMBRE COMPLETO', 'SITUACION DEL TITULAR', 'FECHA APERTURA', 'FECHA VENCIMIENTO', 
        'RESPONSABLE', 'FORMA DE PAGO', 'NOVEDAD', 'ESTADO ORIGEN DE LA CUENTA', 
        'FECHA ESTADO ORIGEN', 'ESTADO DE LA CUENTA', 'FECHA ESTADO DE LA CUENTA', 
        'ADJETIVO', 'FECHA DE ADJETIVO', 'CALIFICACION', 'EDAD DE MORA', 'VALOR INICIAL', 
        'VALOR SALDO DEUDA', 'VALOR DISPONIBLE', 'V CUOTA MENSUAL', 'VALOR SALDO MORA', 
        'TOTAL CUOTAS', 'CUOTAS CANCELADAS', 'CUOTAS EN MORA', 'CLAUSULA DE PERMANENCIA', 
        'FECHA CLAUSULA DE PERMANENCIA', 'FECHA LIMITE DE PAGO', 'FECHA DE PAGO', 
        'CIUDAD CORRESPONDENCIA', 'CODIGO DANE CIUDAD CORRESPONDENCIA', 
        'DEPARTAMENTO DE CORRESPONDENCIA', 'DIRECCION DE CORRESPONDENCIA', 
        'CORREO ELECTRONICO', 'CELULAR'
    ]

    COLSPECS_ARPESOD = [
        (0, 1),      
        (1, 12),     
        (12, 30),    
        (30, 75),    
        (75, 76),     
        (76, 84),     
        (84, 92),     
        (92, 94),     
        (105, 106),   
        (107, 109),   
        (109, 110),   
        (110, 118),   
        (118, 120),   
        (120, 128),   
        (137, 138),   
        (138, 146),   
        (180, 182),   
        (185, 188),   
        (188, 199),   
        (199, 210),   
        (210, 221),   
        (221, 232),   
        (232, 243),   
        (243, 246),   
        (246, 249),   
        (249, 252),   
        (252, 255),   
        (255, 263),   
        (263, 271),   
        (271, 279),   
        (577, 597),   
        (597, 605),   
        (605, 625),   
        (625, 685),   
        (685, 745),   
        (445, 457)   
        
        
    ]
    
    # Nombres de columnas para lectura (coinciden con el orden de COLSPECS_ARPESOD)
    NAMES_ARPESOD = COLUMNAS_ARPESOD 

    def __init__(self):
        self.df = None
        # --- CONFIGURACIÓN POR DEFECTO (FINANSUEÑOS) ---
        self.colspecs_default = [
            (0, 1), (1, 12), (30, 75), (12, 30), (76, 84), (84, 92),
            (92, 94), (107, 109), (109, 110), (188, 199), (199, 210),
            (210, 221), (221, 232), (232, 243), (243, 246), (246, 249),
            (249, 252), (263, 271), (271, 279), (577, 597), (625, 685),
            (685, 745), (445, 457), (75, 76), (185, 188), (105, 106),
            (110, 118), (118, 120), (120, 128), (137, 138), (138, 146),
            (252, 255), (255, 263)
        ]
        self.names_default = [
            "TIPO DE IDENTIFICACION", "NUMERO DE IDENTIFICACION", "NOMBRE COMPLETO",
            "NUMERO DE LA CUENTA U OBLIGACION", "FECHA APERTURA", "FECHA VENCIMIENTO",
            "RESPONSABLE", "NOVEDAD", "ESTADO ORIGEN DE LA CUENTA", "VALOR INICIAL",
            "VALOR SALDO DEUDA", "VALOR DISPONIBLE", "V CUOTA MENSUAL",
            "VALOR SALDO MORA", "TOTAL CUOTAS", "CUOTAS CANCELADAS", "CUOTAS EN MORA",
            "FECHA LIMITE DE PAGO", "FECHA DE PAGO", "CIUDAD CORRESPONDENCIA",
            "DIRECCION DE CORRESPONDENCIA", "CORREO ELECTRONICO", "CELULAR",
            "SITUACION DEL TITULAR", "EDAD DE MORA", "FORMA DE PAGO",
            "FECHA ESTADO ORIGEN", "ESTADO DE LA CUENTA", "FECHA ESTADO DE LA CUENTA",
            "ADJETIVO", "FECHA DE ADJETIVO", "CLAUSULA DE PERMANENCIA", "FECHA CLAUSULA DE PERMANENCIA"
        ]

    def load_plano_file(self, file_path, empresa_actual=None):
        """
        Carga el archivo plano seleccionando la estructura correcta según la empresa.
        """
        print(f"Modelo: Cargando archivo plano para {empresa_actual}...")
        
        # 1. Selección de Estructura
        if empresa_actual and empresa_actual.lower() == "arpesod":
            specs = self.COLSPECS_ARPESOD
            names = self.NAMES_ARPESOD
            print("Modelo: Usando estructura de columnas ARPESOD.")
        else:
            specs = self.colspecs_default
            names = self.names_default
            print("Modelo: Usando estructura de columnas POR DEFECTO (Finansueños).")

        try:
            self.df = pd.read_fwf(
                file_path, colspecs=specs, names=names, encoding='cp1252',
                skiprows=1, skipfooter=1, engine='python'
            )
            # Limpieza básica
            self.df['NUMERO DE IDENTIFICACION'] = self.df['NUMERO DE IDENTIFICACION'].astype(str).str.strip()
            print("Modelo: Archivo plano cargado exitosamente.")
        except Exception as e:
            print(f"Error al leer el archivo plano: {e}")
            raise e

    def save_processed_file(self, output_path, empresa_actual=None):
        """Guarda el archivo Excel con el orden específico para Arpesod."""
        if self.df is None:
            raise ValueError("No hay datos procesados para guardar.")
        
        print(f"Modelo: Guardando archivo procesado en {output_path}")
        df_export = self.df.copy()

        try:
            # Lógica Arpesod
            if empresa_actual and empresa_actual.lower() == "arpesod":
                print("Modelo: Aplicando orden de columnas específico para ARPESOD...")
                for col in self.COLUMNAS_ARPESOD:
                    # Normalización V. CUOTA MENSUAL
                    if col == "V. CUOTA MENSUAL" and "V CUOTA MENSUAL" in df_export.columns:
                         df_export.rename(columns={"V CUOTA MENSUAL": "V. CUOTA MENSUAL"}, inplace=True)
                    elif col not in df_export.columns:
                        df_export[col] = "" 
                
                # Reordenamiento final
                df_export = df_export[self.COLUMNAS_ARPESOD]

            df_export.to_excel(output_path, index=False)
            print("Modelo: Archivo guardado con éxito.")
        except Exception as e:
            print(f"Error al guardar Excel: {e}")
            raise e