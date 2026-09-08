import sys
import traceback
import customtkinter as ctk
from pathlib import Path

# MOTIVO (empaquetado): en el .exe los módulos viajan dentro del PYZ y este
# ajuste de sys.path solo se necesita cuando se ejecuta desde el código fuente.
if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

# MOTIVO (estabilidad): logging a archivo y salida estándar a prueba de
# "--windowed" (donde sys.stdout puede ser None y cualquier print rompería).
from src.utils.logging_setup import init_logging, log_exception_to_file

# MOTIVO (concurrencia): infraestructura de hilos segura para tkinter.
from src.utils import task_runner
from src.utils.task_runner import TaskRunner, set_default_runner, patch_tk_dialogs

from src.controllers.convenios_controller import ConveniosController
from src.controllers.anticipos_controller import AnticiposController
from src.controllers.base_controller import BaseMensualController
from src.controllers.datacredito_controller import DataCreditoController
from src.controllers.cifin_contoller import CifinController
from src.views.main_window import MainWindow
from src.controllers.novedades_controller import NovedadesAnalisisController
from src.controllers.ecollect_controller import EcollectController


def _attach_runner(runner, *controllers):
    """Da acceso al runner a todos los controladores (para ejecutar en hilos)."""
    for controller in controllers:
        controller.runner = runner


def main():
    root = None
    try:
        # --- Logging antes de cualquier otra cosa (visible en campo) ---
        log_dir = init_logging()

        # Ventana moderna con customtkinter (solo tema claro).
        ctk.set_appearance_mode("light")
        root = ctk.CTk()

        # --- Infraestructura de hilos segura ---
        runner = TaskRunner(root)
        set_default_runner(runner)
        patch_tk_dialogs()

        controller_convenios = ConveniosController(None)
        controller_anticipos = AnticiposController(None)
        controller_base_mensual = BaseMensualController()
        controller_datacredito = DataCreditoController()
        controller_cifin = CifinController()
        controller_novedades_analisis = NovedadesAnalisisController()
        controller_ecollect = EcollectController()
        _attach_runner(
            runner,
            controller_convenios,
            controller_anticipos,
            controller_base_mensual,
            controller_datacredito,
            controller_cifin,
            controller_novedades_analisis,
            controller_ecollect,
        )

        main_view = MainWindow(
            root,
            controller_convenios,
            controller_anticipos,
            controller_base_mensual,
            controller_datacredito,
            controller_cifin,
            controller_novedades_analisis,
            controller_ecollect,
        )

        controller_anticipos.set_view(main_view)
        controller_convenios.set_view(main_view)

        # MOTIVO (bug/robustez): al cerrar con un proceso en marcha antes se
        # descartaba la cola de golpe (posible archivo truncado o TimeoutError
        # en el worker). Ahora se avisa y NO se cierra mientras haya procesos
        # activos; así el usuario termina la tarea y luego cierra normalmente.
        def _on_close():
            if runner.busy_keys():
                from tkinter import messagebox
                messagebox.showwarning(
                    "Procesos en curso",
                    "Hay procesos ejecutándose. Espera a que terminen y cierra de nuevo.")
                return
            runner.shutdown()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", _on_close)
        root.mainloop()

    except Exception as exc:  # noqa: BLE001 - último recurso visible
        message = (f"Error inesperado en la aplicación:\n{exc}\n\n"
                   f"Detalle guardado en: {log_exception_to_file(None, exc) if 'log_dir' in dir() else 'la carpeta de logs'}")
        try:
            if root is not None:
                from tkinter import messagebox
                messagebox.showerror("Error de aplicación", message)
            else:
                print(message)
        except Exception:
            traceback.print_exc()
    finally:
        print("Aplicación finalizada")


if __name__ == "__main__":
    main()
