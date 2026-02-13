import pandas as pd
import numpy as np

# Es buena práctica importar los servicios que se usan
from src.services.base.dataloader_service import DataLoaderService
from src.models.base_model import configuracion  # Asumiendo que config se importa así


class MetricsCalculationService:
    """
    Servicio especializado en realizar cálculos de métricas de negocio,
    como saldos financieros y metas de cumplimiento.
    """

    def __init__(self):
        # Instanciamos el dataloader aquí si es una dependencia específica
        # de este servicio, como lo era en el original.
        self.data_loader = DataLoaderService(configuracion)

    def calculate_balances(self, reporte_df, fnz003_df):
        """
        Calcula saldos de forma robusta, asegurando que las columnas sean numéricas.
        También identifica y reporta créditos con saldos negativos.
        """
        print("📊 Calculando saldos...")
        creditos_negativos_fnz003 = pd.DataFrame()

        for col in ["Saldo_Capital", "Saldo_Avales", "Saldo_Interes_Corriente"]:
            if col not in reporte_df.columns:
                reporte_df[col] = 0

        reporte_df["Saldo_Capital"] = np.where(
            reporte_df["Empresa"] == "ARPESOD", reporte_df.get("Saldo_Factura"), np.nan
        )

        if not fnz003_df.empty:
            fnz003_df["Saldo"] = pd.to_numeric(
                fnz003_df["Saldo"], errors="coerce"
            ).fillna(0)

            negativos_df = fnz003_df[fnz003_df["Saldo"] < 0].copy()
            if not negativos_df.empty:
                print(
                    f"   - ⚠️ Se encontraron {len(negativos_df)} saldos negativos en FNZ003."
                )
                negativos_df = self.data_loader.create_credit_key(negativos_df)
                negativos_df["Observacion"] = "Saldo negativo en: " + negativos_df[
                    "Concepto"
                ].astype(str)
                creditos_negativos_fnz003 = negativos_df[
                    ["Credito", "Observacion"]
                ].drop_duplicates()

            mapa_capital = (
                fnz003_df[fnz003_df["Concepto"].isin(["CAPITAL", "ABONO DIF TASA"])]
                .groupby("Credito")["Saldo"]
                .sum()
            )
            mapa_avales = (
                fnz003_df[fnz003_df["Concepto"] == "AVAL"]
                .groupby("Credito")["Saldo"]
                .sum()
            )
            mapa_interes = (
                fnz003_df[fnz003_df["Concepto"] == "INTERES CORRIENTE"]
                .groupby("Credito")["Saldo"]
                .sum()
            )

            mask_fns = reporte_df["Empresa"] == "FINANSUEÑOS"
            # --- CORRECCIÓN pandas 3.0: castear a object antes de asignar numéricos ---
            # Si las columnas vienen de un Excel anterior con dtype 'str', el .loc
            # con .map() numérico explota con "Invalid value for dtype 'str'".
            for col in ["Saldo_Capital", "Saldo_Avales", "Saldo_Interes_Corriente"]:
                if col in reporte_df.columns:
                    reporte_df[col] = reporte_df[col].astype(object)
            reporte_df.loc[mask_fns, "Saldo_Capital"] = reporte_df.loc[
                mask_fns, "Credito"
            ].map(mapa_capital)
            reporte_df.loc[mask_fns, "Saldo_Avales"] = reporte_df.loc[
                mask_fns, "Credito"
            ].map(mapa_avales)
            reporte_df.loc[mask_fns, "Saldo_Interes_Corriente"] = reporte_df.loc[
                mask_fns, "Credito"
            ].map(mapa_interes)

        for col in ["Saldo_Capital", "Saldo_Avales", "Saldo_Interes_Corriente"]:
            if col in reporte_df.columns:
                reporte_df[col] = (
                    pd.to_numeric(reporte_df[col], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

        return reporte_df, creditos_negativos_fnz003

    def calculate_goal_metrics(self, reporte_df, metas_franjas_df=None):
        """
        Calcula las diferentes métricas de metas basadas en franjas y saldos.
        """
        print("🎯 Calculando métricas de metas...")

        for col in ["Meta_DC_Al_Dia", "Meta_DC_Atraso", "Meta_Atraso"]:
            if col in reporte_df.columns:
                reporte_df[col] = pd.to_numeric(
                    reporte_df[col], errors="coerce"
                ).fillna(0)
        reporte_df["Meta_General"] = (
            reporte_df["Meta_DC_Al_Dia"]
            + reporte_df["Meta_DC_Atraso"]
            + reporte_df["Meta_Atraso"]
        )

        columnas_metas_a_borrar = []
        if "Meta_1_A_30" not in reporte_df.columns:
            print(
                "   - Columnas de metas no encontradas. Uniendo desde el archivo de metas por franjas..."
            )
            if metas_franjas_df is not None and not metas_franjas_df.empty:
                reporte_df = pd.merge(
                    reporte_df, metas_franjas_df, on="Zona", how="left"
                )
                columnas_metas_a_borrar = [
                    col for col in metas_franjas_df.columns if col != "Zona"
                ]
            else:
                print(
                    "   - ⚠️ ADVERTENCIA: No se pudo realizar la unión. Los cálculos de metas por franja serán 0."
                )
                for col in [
                    "Meta_1_A_30",
                    "Meta_31_A_90",
                    "Meta_91_A_180",
                    "Meta_181_A_360",
                    "Total_Recaudo",
                ]:
                    reporte_df[col] = 0

        columnas_porcentaje = [
            "Meta_1_A_30",
            "Meta_31_A_90",
            "Meta_91_A_180",
            "Meta_181_A_360",
            "Total_Recaudo",
        ]
        for col in columnas_porcentaje:
            if col in reporte_df.columns:
                reporte_df[col] = (
                    reporte_df[col].astype(str).str.replace("%", "").str.strip()
                )
                numeric_col = pd.to_numeric(reporte_df[col], errors="coerce")
                reporte_df[col] = np.where(
                    numeric_col > 1, numeric_col / 100, numeric_col
                )
                reporte_df[col] = reporte_df[col].fillna(0)

        dias_atraso = pd.to_numeric(reporte_df["Dias_Atraso"], errors="coerce").fillna(
            -1
        )
        condiciones = [
            dias_atraso.between(1, 30),
            dias_atraso.between(31, 90),
            dias_atraso.between(91, 180),
            dias_atraso.between(181, 360),
        ]
        valores = [
            reporte_df["Meta_1_A_30"],
            reporte_df["Meta_31_A_90"],
            reporte_df["Meta_91_A_180"],
            reporte_df["Meta_181_A_360"],
        ]
        reporte_df["Meta_%"] = np.select(condiciones, valores, default=0)
        reporte_df["Meta_$"] = reporte_df["Meta_General"] * reporte_df["Meta_%"]

        reporte_df["Meta_T.R_%"] = reporte_df.get("Total_Recaudo", 0)

        meta_general_fs = pd.to_numeric(
            reporte_df.get("Meta_Saldo", 0), errors="coerce"
        ).fillna(0)
        reporte_df["Meta_T.R_$"] = meta_general_fs * reporte_df["Meta_T.R_%"]

        reporte_df.drop(columns=columnas_metas_a_borrar, inplace=True, errors="ignore")
        return reporte_df
