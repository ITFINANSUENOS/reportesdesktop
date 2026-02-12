import pandas as pd
import numpy as np
from src.models.base_model import (
    ORDEN_COLUMNAS_FINAL,
    configuracion,
    DeteccionCreditos,
    COLUMNAS_VOLATILES,
    COLUMNAS_ESTATICAS,
    COLUMNAS_MAESTROS,
    COLUMNAS_ORGANIZACION,
    COLUMNAS_DETECCION_CAMBIOS,
)


class UpdateBaseService:
    """
    Servicio que actualiza un reporte base usando el enfoque híbrido:
    1. Usa el R91 nuevo como la "fuente de la verdad" para el esqueleto del reporte.
    2. Enriquece el esqueleto consolidando los datos nuevos del mes con los del reporte anterior.
    3. Reutiliza las funciones de transformación y cálculo del servicio principal.
    """

    def __init__(self, report_service):
        self.report_service = report_service
        self.data_loader = report_service.data_loader

    def sincronizar_reporte(self, df_base_anterior, dataframes_nuevos):
        print("🚀 Iniciando modo de actualización con enfoque híbrido...")

        # --- PASO 1: Usar R91 como el esqueleto INTOCABLE ---
        df_r91_nuevo = self.data_loader.safe_concat(dataframes_nuevos.get("R91", []))
        if df_r91_nuevo.empty:
            raise ValueError("El archivo R91 es obligatorio para la actualización.")

        esqueleto_df = self.data_loader.create_credit_key(df_r91_nuevo)
        print(
            f"\n[LOG] Esqueleto creado a partir de R91 con {len(esqueleto_df)} registros."
        )

        # --- PASO 2: Consolidar y unir cada fuente de datos ---
        for tipo, config in configuracion.items():
            if tipo == "R91":
                continue

            # --- INICIO DE LA CORRECCIÓN ---
            # 1. Establecemos la llave por defecto al inicio de CADA vuelta del bucle.
            join_keys = ["Credito", "Cedula_Cliente"]

            # 2. El 'if' ahora solo SOBREESCRIBE el valor por defecto en casos especiales.
            if tipo in ["MATRIZ_CARTERA", "METAS_FRANJAS"]:
                join_keys = ["Zona"]
            elif tipo in ["ASESORES", "SC04"]:
                # Simplificamos la omisión de casos especiales
                print(
                    f"   - Omitiendo '{tipo}' en la consolidación inicial (se procesará después)."
                )
                continue
            # --- FIN DE LA CORRECCIÓN ---

            columnas_del_tipo = list(config.get("rename_map", {}).values())
            if not columnas_del_tipo:
                continue

            # Ahora 'join_keys' siempre existirá en este punto.
            keys_to_add = join_keys if isinstance(join_keys, list) else [join_keys]
            for key in keys_to_add:
                if key not in columnas_del_tipo:
                    columnas_del_tipo.append(key)

            df_nuevos_datos = self.data_loader.safe_concat(
                dataframes_nuevos.get(tipo, [])
            )

            columnas_existentes_en_anterior = [
                col for col in columnas_del_tipo if col in df_base_anterior.columns
            ]
            df_datos_viejos = df_base_anterior[columnas_existentes_en_anterior].copy()

            df_consolidado = pd.DataFrame()

            if not df_nuevos_datos.empty:
                if "Credito" not in df_nuevos_datos.columns and "Credito" in join_keys:
                    df_nuevos_datos = self.data_loader.create_credit_key(
                        df_nuevos_datos
                    )

                df_combinado = pd.concat(
                    [df_nuevos_datos, df_datos_viejos], ignore_index=True
                )
                df_consolidado = df_combinado.drop_duplicates(
                    subset=join_keys, keep="first"
                )
            elif not df_datos_viejos.empty:
                df_consolidado = df_datos_viejos.drop_duplicates(
                    subset=join_keys, keep="first"
                )

            if df_consolidado.empty:
                continue

            print(
                f"   - Consolidando y uniendo datos de '{tipo}' usando la llave: {join_keys}..."
            )

            esqueleto_df = pd.merge(
                esqueleto_df,
                df_consolidado,
                on=join_keys,
                how="left",
                suffixes=("", f"_{tipo}_dup"),
            )

        print("\n[LOG] Todas las fuentes de datos han sido unidas al esqueleto.")
        reporte_df = esqueleto_df.copy()

        # --- PASO 3: (Sin cambios) Reutilizar las funciones de transformación ---
        print("\n[LOG] Aplicando transformaciones y cálculos finales...")
        reporte_df, negativos_finales, _ = self._aplicar_transformaciones(
            reporte_df, dataframes_nuevos
        )
        reporte_final, reporte_correcciones = (
            self.report_service.report_processor.finalize_report(
                reporte_df, ORDEN_COLUMNAS_FINAL
            )
        )

        print(
            f"\n✅ Proceso de sincronización completado. Registros finales: {len(reporte_final)}"
        )
        return reporte_final, negativos_finales, reporte_correcciones

    def _aplicar_transformaciones(self, reporte_df, dataframes_nuevos):
        # Esta función es un contenedor para las llamadas de servicio que ya tienes.
        # Es casi idéntica a la que tenías antes, pero ahora actúa sobre la base consolidada.

        # Cargar DataFrames necesarios para las funciones
        crtmp_df = self.data_loader.create_credit_key(
            self.data_loader.safe_concat(dataframes_nuevos.get("CRTMPCONSULTA1", []))
        )
        sc04_df = self.data_loader.safe_concat(dataframes_nuevos.get("SC04", []))
        fnz001_df = self.data_loader.create_credit_key(
            self.data_loader.safe_concat(dataframes_nuevos.get("FNZ001", []))
        )
        fnz003_df = self.data_loader.create_credit_key(
            self.data_loader.safe_concat(dataframes_nuevos.get("FNZ003", []))
        )
        vencimientos_df = self.data_loader.create_credit_key(
            self.data_loader.safe_concat(dataframes_nuevos.get("VENCIMIENTOS", []))
        )

        _, negativos_vencimientos = (
            self.report_service.credit_details.process_vencimientos_data(
                vencimientos_df
            )
        )

        # Llamadas a los servicios que reutilizamos
        reporte_df["Empresa"] = np.where(
            reporte_df["Tipo_Credito"] == "DF", "FINANSUEÑOS", "ARPESOD"
        )
        reporte_df = self.report_service.products_sales.assign_sales_invoice(
            reporte_df, crtmp_df
        )
        reporte_df = self.report_service.products_sales.add_product_details(
            reporte_df, crtmp_df
        )
        reporte_df = self.report_service.credit_details.enrich_credit_details(
            reporte_df, sc04_df, fnz001_df
        )
        reporte_df = self.report_service.credit_details.clean_installment_data(
            reporte_df
        )
        reporte_df = self.report_service.report_processor.map_call_center_data(
            reporte_df
        )
        reporte_df, negativos_fnz003 = (
            self.report_service.report_processor.calculate_balances(
                reporte_df, fnz003_df
            )
        )
        reporte_df = self.report_service.report_processor.calculate_goal_metrics(
            reporte_df
        )
        reporte_df = self.report_service.credit_details.adjust_arrears_status(
            reporte_df
        )

        negativos_finales = pd.concat(
            [negativos_vencimientos, negativos_fnz003], ignore_index=True
        )
        return reporte_df, negativos_finales, pd.DataFrame()

    def _detectar_creditos_modificados(
        self, df_r91_nuevo: pd.DataFrame, df_base_anterior: pd.DataFrame
    ) -> DeteccionCreditos:
        """Classifies every credit into exactly one of 4 categories.

        Compares the new R91 (current month truth) against the previous base
        report using set operations for O(1) membership tests.

        Credits present in both sources are further checked against
        COLUMNAS_DETECCION_CAMBIOS (Zona, Codigo_Vendedor, Zona_Cobro).
        If any of those structural columns changed, the credit is marked
        as 'modificado' so it gets fully re-processed downstream.

        Args:
            df_r91_nuevo: New R91 data with 'Credito' column already created.
            df_base_anterior: Previous month's complete report.

        Returns:
            DeteccionCreditos with sets: nuevos, eliminados, modificados, intactos.
        """
        # --- Step 1: Build ID sets ---
        ids_nuevos = set(df_r91_nuevo["Credito"].dropna().unique())
        ids_anteriores = set(df_base_anterior["Credito"].dropna().unique())

        # --- Step 2: Set operations for new / eliminated / common ---
        nuevos = ids_nuevos - ids_anteriores
        eliminados = ids_anteriores - ids_nuevos
        comunes = ids_nuevos & ids_anteriores

        # --- Step 3: Among common credits, detect structural changes ---
        modificados: set[str] = set()
        intactos: set[str] = set()

        if comunes:
            cols_deteccion = list(COLUMNAS_DETECCION_CAMBIOS)

            # Filter to common credits only and select detection columns + key
            cols_needed = ["Credito"] + cols_deteccion

            # From R91: only keep columns that actually exist
            comunes_list = list(comunes)
            cols_r91 = [c for c in cols_needed if c in df_r91_nuevo.columns]
            mask_nuevo = df_r91_nuevo["Credito"].isin(comunes_list)
            df_nuevo_filtered = df_r91_nuevo.loc[mask_nuevo, cols_r91]
            df_nuevo_subset = df_nuevo_filtered.drop_duplicates(
                subset=["Credito"], keep="first"
            ).set_index("Credito")

            # From base anterior: only keep columns that actually exist
            cols_anterior = [c for c in cols_needed if c in df_base_anterior.columns]
            mask_anterior = df_base_anterior["Credito"].isin(comunes_list)
            df_anterior_filtered = df_base_anterior.loc[mask_anterior, cols_anterior]
            df_anterior_subset = df_anterior_filtered.drop_duplicates(
                subset=["Credito"], keep="first"
            ).set_index("Credito")

            # Align both DataFrames to the same set of detection columns
            # (in case a column is missing from one side)
            cols_comunes = [
                c
                for c in cols_deteccion
                if c in df_nuevo_subset.columns and c in df_anterior_subset.columns
            ]

            if cols_comunes:
                # Fill NaN with empty string so NaN == NaN evaluates as True
                df_nuevo_aligned = df_nuevo_subset[cols_comunes].fillna("").astype(str)
                df_anterior_aligned = (
                    df_anterior_subset[cols_comunes].fillna("").astype(str)
                )

                # Reindex to ensure both have the exact same rows (common credits)
                common_index = df_nuevo_aligned.index.intersection(
                    df_anterior_aligned.index
                )
                df_nuevo_aligned = df_nuevo_aligned.loc[common_index]
                df_anterior_aligned = df_anterior_aligned.loc[common_index]

                # Compare: True where values differ
                cambios = (df_nuevo_aligned != df_anterior_aligned).any(axis=1)

                modificados = set(cambios[cambios].index)
                intactos = set(cambios[~cambios].index)
            else:
                # No detection columns available: treat all common as intact
                intactos = comunes

            # Credits in 'comunes' that weren't in either aligned DataFrame
            # (edge case: duplicates or missing from one side after dedup)
            no_clasificados = comunes - modificados - intactos
            if no_clasificados:
                # Conservative: treat unclassified as modified (re-process them)
                modificados |= no_clasificados

        print(f"\n📊 Detección de créditos completada:")
        print(f"   ✅ Intactos:     {len(intactos):>6,}")
        print(f"   🆕 Nuevos:       {len(nuevos):>6,}")
        print(f"   🔄 Modificados:  {len(modificados):>6,}")
        print(f"   ❌ Eliminados:   {len(eliminados):>6,}")
        print(f"   📋 Total R91:    {len(ids_nuevos):>6,}")

        return DeteccionCreditos(
            nuevos=nuevos,
            eliminados=eliminados,
            modificados=modificados,
            intactos=intactos,
        )

    def _procesar_creditos_nuevos_y_modificados(
        self,
        df_r91_nuevo: pd.DataFrame,
        ids_a_procesar: set[str],
        dataframes_nuevos: dict,
        df_base_anterior: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Runs the full processing pipeline for new and modified credits only.

        Filters the R91 to only include credits in ids_a_procesar, then
        executes the same consolidation + transformation pipeline that
        sincronizar_reporte uses today. This is the EXACT same logic,
        just applied to a subset of credits.

        Both NEW and MODIFIED credits get identical treatment because:
        - New credits have no prior data → need full processing.
        - Modified credits had structural changes (Zona/Vendedor) →
          cascading effects on MATRIZ_CARTERA, ASESORES, etc. make it
          safer to re-process from scratch than to patch.

        Args:
            df_r91_nuevo: Full R91 DataFrame with 'Credito' column created.
            ids_a_procesar: Set of credit IDs (nuevos ∪ modificados).
            dataframes_nuevos: Dict of all new source DataFrames by type.
            df_base_anterior: Previous month's complete report.

        Returns:
            Tuple of (processed DataFrame, negativos DataFrame).
        """
        if not ids_a_procesar:
            print("\n[LOG] No hay créditos nuevos ni modificados para procesar.")
            return pd.DataFrame(), pd.DataFrame()

        # --- Step 1: Filter R91 to only credits that need full processing ---
        ids_list = list(ids_a_procesar)
        mask = df_r91_nuevo["Credito"].isin(ids_list)
        esqueleto_df = df_r91_nuevo.loc[mask].copy()

        print(
            f"\n[LOG] Procesando {len(esqueleto_df)} créditos (nuevos + modificados)..."
        )

        # --- Step 2: Consolidate each data source (same logic as sincronizar_reporte) ---
        for tipo, config in configuracion.items():
            if tipo == "R91":
                continue

            join_keys = ["Credito", "Cedula_Cliente"]

            if tipo in ["MATRIZ_CARTERA", "METAS_FRANJAS"]:
                join_keys = ["Zona"]
            elif tipo in ["ASESORES", "SC04"]:
                continue

            columnas_del_tipo = list(config.get("rename_map", {}).values())
            if not columnas_del_tipo:
                continue

            keys_to_add = join_keys if isinstance(join_keys, list) else [join_keys]
            for key in keys_to_add:
                if key not in columnas_del_tipo:
                    columnas_del_tipo.append(key)

            df_nuevos_datos = self.data_loader.safe_concat(
                dataframes_nuevos.get(tipo, [])
            )

            columnas_existentes_en_anterior = [
                col for col in columnas_del_tipo if col in df_base_anterior.columns
            ]
            df_datos_viejos = df_base_anterior[columnas_existentes_en_anterior].copy()

            df_consolidado = pd.DataFrame()

            if not df_nuevos_datos.empty:
                if "Credito" not in df_nuevos_datos.columns and "Credito" in join_keys:
                    df_nuevos_datos = self.data_loader.create_credit_key(
                        df_nuevos_datos
                    )

                df_combinado = pd.concat(
                    [df_nuevos_datos, df_datos_viejos], ignore_index=True
                )
                df_consolidado = df_combinado.drop_duplicates(
                    subset=join_keys, keep="first"
                )
            elif not df_datos_viejos.empty:
                df_consolidado = df_datos_viejos.drop_duplicates(
                    subset=join_keys, keep="first"
                )

            if df_consolidado.empty:
                continue

            esqueleto_df = pd.merge(
                esqueleto_df,
                df_consolidado,
                on=join_keys,
                how="left",
                suffixes=("", f"_{tipo}_dup"),
            )

        # --- Step 3: Apply transformations (same pipeline as full processing) ---
        reporte_df = esqueleto_df.copy()
        reporte_df, negativos, _ = self._aplicar_transformaciones(
            reporte_df, dataframes_nuevos
        )

        print(f"   ✅ Pipeline completo aplicado a {len(reporte_df)} créditos.")

        return reporte_df, negativos

    def _preservar_datos_estaticos(
        self,
        df_base_anterior: pd.DataFrame,
        ids_intactos: set[str],
    ) -> pd.DataFrame:
        """Extracts intact credits from the previous base, preserving non-volatile data.

        For credits that haven't changed structurally (same Zona, Vendedor,
        Zona_Cobro), we skip the full processing pipeline and instead copy
        their rows directly from the previous report. This preserves:

        - COLUMNAS_ESTATICAS: loan details that never change (desembolso, factura, etc.)
        - COLUMNAS_MAESTROS: client data that rarely changes (nombre, cédula, etc.)
        - COLUMNAS_ORGANIZACION: zone/seller data (unchanged since we already
          classified structural changes as 'modificados')

        Volatile columns (saldos, mora, metas) are NOT included here — they'll
        be updated separately in Paso 4 (_actualizar_columnas_volatiles).

        Args:
            df_base_anterior: Previous month's complete report.
            ids_intactos: Set of credit IDs classified as unchanged.

        Returns:
            DataFrame with intact credits and all non-volatile columns preserved.
            Returns empty DataFrame if ids_intactos is empty.
        """
        if not ids_intactos:
            print("\n[LOG] No hay créditos intactos para preservar.")
            return pd.DataFrame()

        # --- Step 1: Filter base anterior to only intact credits ---
        ids_list = list(ids_intactos)
        mask = df_base_anterior["Credito"].isin(ids_list)
        df_intactos = df_base_anterior.loc[mask].copy()

        if df_intactos.empty:
            print(
                "⚠️ ids_intactos no vacío pero no se encontraron coincidencias en base anterior."
            )
            return pd.DataFrame()

        # --- Step 2: Determine which columns to preserve ---
        # Everything EXCEPT volatile columns — those will be updated in Paso 4
        columnas_a_preservar = [
            col for col in df_intactos.columns if col not in COLUMNAS_VOLATILES
        ]

        df_resultado = df_intactos[columnas_a_preservar].copy()

        print(
            f"\n[LOG] Preservados {len(df_resultado)} créditos intactos "
            f"({len(columnas_a_preservar)} columnas no-volátiles copiadas)."
        )

        return df_resultado
