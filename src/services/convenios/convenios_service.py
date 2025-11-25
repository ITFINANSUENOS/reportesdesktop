from src.models.convenios_model import ConveniosConfig
from src.services.convenios.dataloader_service import DataLoader
from src.services.convenios.dataprocessor_service import DataProcessor
from src.services.convenios.report_service import ReportWriter

class ConveniosService:
    """
    Orquesta el proceso de generación de reportes coordinando
    la carga, procesamiento y escritura de datos.
    """
    def __init__(self, config: ConveniosConfig = None):
        self.config = config if config else ConveniosConfig()
        self.loader = DataLoader(self.config)
        self.processor = DataProcessor(self.config)
        self.writer = ReportWriter()

    def generate_report(self, file_path: str, status_callback):
        """
        Orquesta todo el proceso de generación del reporte Financiero.
        """
        status_callback("Cargando y filtrando datos...", 10)
        dfs = self.loader.load_and_filter_data(file_path)

        status_callback("Preparando datos...", 30)
        dfs = self.loader.prepare_data(dfs)

        status_callback("Procesando pagos de Bancolombia...", 50)
        df_bancolombia = self.processor.process_payment_type(dfs, 'bancolombia')
        
        status_callback("Procesando pagos de Efecty...", 65)
        df_efecty = self.processor.process_payment_type(dfs, 'efecty')

        status_callback("Procesando pagos de Ecollect...", 80)
        df_ecollect = self.processor.process_payment_type(dfs, 'ecollect')
        
        return df_bancolombia, df_efecty, df_ecollect
    
    def save_report(self, output_path: str, df_bancolombia, df_efecty, df_ecollect):
        """Delega la tarea de guardar el reporte al ReportWriter."""
        self.writer.save_report(output_path, df_bancolombia, df_efecty, df_ecollect)

    def validate_input_file(self, file_path: str) -> bool:
        """Delega la validación del archivo al DataLoader."""
        return self.loader.validate_input_file(file_path)