import pandas as pd
from tkinter import messagebox
from pathlib import Path

class NominaService:
    """
    Servicio encargado de leer y procesar el archivo de configuración de nómina,
    extrayendo las tablas de comisiones, anticipos y recaudos para Gestores y Cobradores.
    """
    def _clean_columns(self, df):
        """
        Limpia y renombra las columnas de un DataFrame de nómina.
        - Renombra las dos primeras columnas si coinciden con un patrón.
        - Elimina columnas completamente vacías.
        """
        new_cols = list(df.columns)
        
        if new_cols and '% CMPLTO' in str(new_cols[0]):
            new_cols[0] = 'Rango_Inferior'
        if len(new_cols) > 1 and 'Unnamed: 1' in str(new_cols[1]):
            new_cols[1] = 'Rango_Superior'
        
        df.columns = new_cols
        return df.dropna(axis=1, how='all')

    def procesar_archivo_nomina(self, file_path):
        """
        Orquesta la lectura del archivo Excel de nómina.
        
        Args:
            file_path (str): La ruta al archivo de nómina .xlsx.

        Returns:
            dict: Un diccionario con los DataFrames de GESTORES y COBRADORES,
                  o None si ocurre un error.
        """
        print(f"⚙️  Iniciando procesamiento del archivo de nómina: {Path(file_path).name}")
        
        excel_data = {
            'GESTORES': {},
            'COBRADORES': {}
        }

        try:
            # --- Lectura de la hoja 'GESTORES' ---
            sheet_gestores = 'GESTORES'
            excel_data['GESTORES']['Comisiones'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=0, nrows=6, usecols="A:F")
            )
            excel_data['GESTORES']['Anticipo'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=9, nrows=3, usecols="A:C")
            )
            excel_data['GESTORES']['Recaudo'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=14, nrows=4, usecols="A:C")
            )
            print("✅ Tablas de GESTORES extraídas correctamente.")

            # --- Lectura de la hoja 'COBRADORES' ---
            sheet_cobradores = 'COBRADORES'
            excel_data['COBRADORES']['Comisiones'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=0, nrows=5, usecols="A:F")
            )
            excel_data['COBRADORES']['Anticipo'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=8, nrows=3, usecols="A:C")
            )
            excel_data['COBRADORES']['Recaudo'] = self._clean_columns(
                pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=13, nrows=3, usecols="A:C")
            )
            print("✅ Tablas de COBRADORES extraídas correctamente.")
            
            print("🆔 Leyendo hoja de Cédulas...")
            sheet_cc = 'CC COBRADORES' # Asegúrate que este sea el nombre exacto en el Excel
            
            # Leemos el excel. Asumimos que los encabezados están en la primera fila (header=0)
            df_cedulas = pd.read_excel(file_path, sheet_name=sheet_cc, header=0)
            
            # Limpiamos los nombres para asegurar el cruce (mayúsculas y sin espacios extra)
            if 'NOMBRE' in df_cedulas.columns and 'CC' in df_cedulas.columns:
                df_cedulas['NOMBRE'] = df_cedulas['NOMBRE'].astype(str).str.strip().str.upper()
                # Nos quedamos solo con las columnas que nos interesan
                excel_data['CEDULAS'] = df_cedulas[['NOMBRE', 'CC']]
                print("✅ Tabla de CÉDULAS extraída correctamente.")
            else:
                print("⚠️ La hoja 'CC COBRADORES' no tiene las columnas 'NOMBRE' o 'CC'.")
                excel_data['CEDULAS'] = pd.DataFrame(columns=['NOMBRE', 'CC'])
            
            # --- INICIO DE LA MODIFICACIÓN: IMPRIMIR RESULTADOS EN CONSOLA ---
            print("\n" + "="*50)
            print("📊 DATOS DE NÓMINA CARGADOS CORRECTAMENTE 📊")
            print("="*50)
            
            print("\n--- DATOS EXTRAÍDOS DE LA HOJA GESTORES ---")
            print("\n[+] Tabla de Comisiones:")
            print(excel_data['GESTORES']['Comisiones'])
            print("\n[+] Tabla de Anticipo:")
            print(excel_data['GESTORES']['Anticipo'])
            print("\n[+] Tabla de Recaudo:")
            print(excel_data['GESTORES']['Recaudo'])

            print("\n\n--- DATOS EXTRAÍDOS DE LA HOJA COBRADORES ---")
            print("\n[+] Tabla de Comisiones:")
            print(excel_data['COBRADORES']['Comisiones'])
            print("\n[+] Tabla de Anticipo:")
            print(excel_data['COBRADORES']['Anticipo'])
            print("\n[+] Tabla de Recaudo:")
            print(excel_data['COBRADORES']['Recaudo'])
            print("\n" + "="*50 + "\n")
            # --- FIN DE LA MODIFICACIÓN ---

            print("🎉 Procesamiento de nómina finalizado con éxito.")
            return excel_data

        except Exception as e:
            error_msg = f"No se pudo leer una de las hojas del archivo de nómina. Error: {e}"
            print(f"❌ {error_msg}")
            messagebox.showerror("Error en Archivo de Nómina", error_msg)
            return None
