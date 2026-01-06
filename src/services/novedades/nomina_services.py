import pandas as pd
from tkinter import messagebox
from pathlib import Path

class NominaService:
    def _clean_columns(self, df):
        """Limpieza respetando tus nombres de columnas originales."""
        new_cols = list(df.columns)
        
        if new_cols and '% CMPLTO' in str(new_cols[0]):
            new_cols[0] = 'Rango_Inferior'
        if len(new_cols) > 1 and 'Unnamed: 1' in str(new_cols[1]):
            new_cols[1] = 'Rango_Superior'
        
        df.columns = new_cols
        return df.dropna(axis=1, how='all')

    def _agregar_cedulas(self, df, df_cedulas):
        """Cruza la tabla con las cédulas usando la columna NOMBRE."""
        if df is None or df.empty: return df

        # Buscamos la columna que contenga "NOMBRE"
        col_nombre = next((col for col in df.columns if str(col).upper().strip() == 'NOMBRE'), None)
        
        if col_nombre:
            df[col_nombre] = df[col_nombre].astype(str).str.strip().str.upper()
            
            # Merge
            df_merged = pd.merge(df, df_cedulas, left_on=col_nombre, right_on='NOMBRE', how='left')
            
            # Limpieza post-merge
            if col_nombre != 'NOMBRE' and 'NOMBRE' in df_merged.columns:
                df_merged = df_merged.drop(columns=['NOMBRE'])

            # Reorganizar columna CC al lado del nombre
            cols = list(df_merged.columns)
            if 'CC' in cols:
                cols.remove('CC')
                idx_nombre = cols.index(col_nombre)
                cols.insert(idx_nombre + 1, 'CC')
                df_merged = df_merged[cols]
            return df_merged
        return df

    def procesar_archivo_nomina(self, file_path):
        print(f"⚙️  Iniciando procesamiento del archivo de nómina: {Path(file_path).name}")
        excel_data = {'GESTORES': {}, 'COBRADORES': {}, 'CEDULAS': None}

        try:
            # 1. LEER CÉDULAS PRIMERO
            print("🆔 Leyendo hoja de Cédulas...")
            df_cedulas = pd.read_excel(file_path, sheet_name='CC COBRADORES', header=0)
            
            # Normalizar tabla de cédulas
            col_nombre_cc = next((col for col in df_cedulas.columns if str(col).upper().strip() == 'NOMBRE'), None)
            
            if col_nombre_cc and 'CC' in df_cedulas.columns:
                df_cedulas.rename(columns={col_nombre_cc: 'NOMBRE'}, inplace=True)
                df_cedulas['NOMBRE'] = df_cedulas['NOMBRE'].astype(str).str.strip().str.upper()
                df_cedulas = df_cedulas[['NOMBRE', 'CC']].drop_duplicates()
                excel_data['CEDULAS'] = df_cedulas
                print("✅ Tabla de CÉDULAS cargada.")
            else:
                excel_data['CEDULAS'] = pd.DataFrame(columns=['NOMBRE', 'CC'])

            # 2. PROCESAR GESTORES
            sheet_gestores = 'GESTORES'
            df_com_gest = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=0, nrows=6, usecols="A:F"))
            df_ant_gest = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=9, nrows=3, usecols="A:C"))
            df_rec_gest = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_gestores, header=0, skiprows=14, nrows=4, usecols="A:C"))

            excel_data['GESTORES']['Comisiones'] = self._agregar_cedulas(df_com_gest, df_cedulas)
            excel_data['GESTORES']['Anticipo']   = self._agregar_cedulas(df_ant_gest, df_cedulas)
            excel_data['GESTORES']['Recaudo']    = self._agregar_cedulas(df_rec_gest, df_cedulas)

            # 3. PROCESAR COBRADORES
            sheet_cobradores = 'COBRADORES'
            df_com_cobr = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=0, nrows=5, usecols="A:F"))
            df_ant_cobr = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=8, nrows=3, usecols="A:C"))
            df_rec_cobr = self._clean_columns(pd.read_excel(file_path, sheet_name=sheet_cobradores, header=0, skiprows=13, nrows=3, usecols="A:C"))

            excel_data['COBRADORES']['Comisiones'] = self._agregar_cedulas(df_com_cobr, df_cedulas)
            excel_data['COBRADORES']['Anticipo']   = self._agregar_cedulas(df_ant_cobr, df_cedulas)
            excel_data['COBRADORES']['Recaudo']    = self._agregar_cedulas(df_rec_cobr, df_cedulas)

            print("🎉 Procesamiento de nómina finalizado con éxito.")
            return excel_data

        except Exception as e:
            messagebox.showerror("Error", f"Error en nómina: {e}")
            return None