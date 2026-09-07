# src/utils/task_runner.py
#
# Hilos seguros para una app tkinter.
#
# MOTIVO: tkinter NO es thread-safe. Antes la app lanzaba hilos que tocaban
# widgets, abrían messagebox/filedialog y llamaban update_idletasks() desde el
# hilo worker, lo que puede congelar o tumbar la app (y dejar procesos zombis
# al cerrar la ventana). Este módulo centraliza:
#   1. Un "TaskRunner" que ejecuta trabajo pesado en hilos daemon y devuelve el
#      control al hilo principal mediante una cola + root.after.
#   2. Un marshaling automático: messagebox/filedialog y métodos de UI marcados
#      con @main_thread se ejecutan SIEMPRE en el hilo principal, aunque los
#      llame un worker.
#   3. Un guard anti doble-ejecución (decorator @threaded) por proceso.
import functools
import queue
import threading

# Referencia al runner por defecto (la asigna la app al arrancar).
_DEFAULT_RUNNER = None


def on_main_thread() -> bool:
    """¿Estamos ejecutando en el hilo principal de tkinter?"""
    return threading.current_thread() is threading.main_thread()


def set_default_runner(runner) -> None:
    global _DEFAULT_RUNNER
    _DEFAULT_RUNNER = runner


def get_default_runner():
    return _DEFAULT_RUNNER


def run_on_main(fn, *args, **kwargs):
    """Ejecuta 'fn' en el hilo principal (bloquea al caller si viene de un worker)."""
    if on_main_thread():
        return fn(*args, **kwargs)
    runner = get_default_runner()
    if runner is None:
        # Sin runner (p. ej. tests/preview): se ejecuta aquí mismo.
        return fn(*args, **kwargs)
    return runner.call_ui_sync(lambda: fn(*args, **kwargs))


def main_thread(method):
    """Decorador para métodos de UI: se re-despachan al hilo principal.

    MOTIVO: los métodos que tocan widgets (label.config, progressbar, etc.)
    deben correr en el hilo principal aunque un worker los invoque.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if on_main_thread():
            return method(self, *args, **kwargs)
        return run_on_main(lambda: method(self, *args, **kwargs))
    return wrapper


def threaded(key):
    """Decorador para métodos largos: los ejecuta en un worker con guard.

    MOTIVO: los procesos pesados (pandas/Excel) NO deben congelar la UI. Al
    decorar el método público, la primera llamada corre el cuerpo en un hilo
    daemon; mientras esté activo, nuevas llamadas con la misma 'key' se ignoran
    (evita doble ejecución). Si no hay runner (tests/preview) corre igual que
    antes (síncrono).
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Si ya estamos dentro del worker ejecutando el cuerpo real...
            if getattr(self, "_tb_thread_enter", False):
                return method(self, *args, **kwargs)

            busy = getattr(self, "_tb_busy", set())
            if key in busy:
                from tkinter import messagebox
                run_on_main(lambda: messagebox.showwarning(
                    "Proceso en curso",
                    "Ya hay un proceso de este tipo ejecutándose. Espera a que termine."))
                return None

            runner = getattr(self, "runner", None) or get_default_runner()
            if runner is None:
                return method(self, *args, **kwargs)  # Sin runner: modo síncrono

            busy.add(key)
            self._tb_busy = busy

            def _worker_body():
                self._tb_thread_enter = True
                try:
                    return method(self, *args, **kwargs)
                finally:
                    self._tb_thread_enter = False

            def _finish(_payload=None):
                getattr(self, "_tb_busy", set()).discard(key)

            runner.submit(key, _worker_body, on_done=_finish, on_error=_finish)
            return None
        return wrapper
    return decorator


def patch_tk_dialogs() -> None:
    """Redirige messagebox.* y filedialog.* al hilo principal.

    MOTIVO: código existente (controladores y algunos servicios) abre diálogos
    con messagebox/filedialog. Si se ejecuta desde un worker hay que canalizar
    el diálogo al hilo principal; parcheando los dos módulos una sola vez,
    TODOS esos diálogos quedan seguros sin reescribir cada llamada.
    """
    if getattr(patch_tk_dialogs, "_patched", False):
        return
    patch_tk_dialogs._patched = True

    from tkinter import messagebox as _messagebox
    from tkinter import filedialog as _filedialog

    for _module in (_messagebox, _filedialog):
        for _name, _func in list(vars(_module).items()):
            if not callable(_func) or _name.startswith("_"):
                continue

            @functools.wraps(_func)
            def _wrapped(*args, _name=_name, _func=_func, **kwargs):
                if on_main_thread():
                    return _func(*args, **kwargs)
                return run_on_main(lambda: _func(*args, **kwargs))

            setattr(_module, _name, _wrapped)


class TaskRunner:
    """
    Lanza trabajo en hilos daemon y entrega resultados/progreso al hilo
    principal de Tk usando una cola y un pump periódico (root.after).
    """

    def __init__(self, root, poll_ms=60):
        self.root = root
        self._poll_ms = poll_ms
        self._queue = queue.Queue()
        self._threads = set()
        self._busy = set()
        self._callbacks = {}
        self._alive = True
        self.root.after(self._poll_ms, self._pump)

    # --------------------------------------------------------------- pública
    def is_busy(self, key) -> bool:
        return key in self._busy

    def busy_keys(self):
        return set(self._busy)

    def submit(self, key, fn, on_done=None, on_error=None) -> bool:
        """
        Ejecuta 'fn' en un hilo daemon identificado por 'key'.
        Devuelve False si ya hay un trabajo con esa clave en curso.
        'on_done(resultado)' / 'on_error(excepcion)' corren en el hilo principal.
        """
        if key in self._busy:
            return False
        self._busy.add(key)
        self._callbacks[key] = (on_done, on_error)

        def _run():
            try:
                result = fn()
                self._queue.put(("_done", key, result))
            except BaseException as exc:  # noqa: BLE001 - se entrega al main
                self._queue.put(("_error", key, exc))
            finally:
                self._threads.discard(threading.current_thread())

        thread = threading.Thread(target=_run, name=f"worker-{key}", daemon=True)
        self._threads.add(thread)
        thread.start()
        return True

    def call_ui_sync(self, fn):
        """
        Ejecuta 'fn' en el hilo principal esperando su resultado.
        Solo debe llamarse desde un hilo worker (el pump atiende la cola).
        """
        if on_main_thread():
            return fn()

        box = {}
        event = threading.Event()

        def _execute():
            try:
                box["result"] = fn()
            except BaseException as exc:  # noqa: BLE001
                box["error"] = exc
            finally:
                event.set()

        self._queue.put(("_ui", _execute))
        # Espera finita: nunca dejar un worker colgado si la app cierra.
        event.wait(60)
        if "error" in box:
            raise box["error"]
        if "result" in box:
            return box["result"]
        raise TimeoutError("La interfaz no respondió a una operación desde el hilo de trabajo.")

    def shutdown(self):
        """Detiene el pump. Los hilos son daemon: no bloquean el cierre del proceso."""
        self._alive = False
        self._queue = queue.Queue()

    # ------------------------------------------------------------ internas
    def _pump(self):
        if not self._alive:
            return
        try:
            for _ in range(500):
                try:
                    item = self._queue.get_nowait()
                except queue.Empty:
                    break
                self._dispatch(item)
        finally:
            self.root.after(self._poll_ms, self._pump)

    def _dispatch(self, item):
        try:
            kind = item[0]
            if kind == "_ui":
                # item[1] = función a ejecutar en el hilo principal
                item[1]()
                return

            # Mensajes de hilos: ("_done"/"_error", key, valor)
            key, value = item[1], item[2]
            if kind == "_done":
                self._busy.discard(key)
                on_done, _ = self._callbacks.pop(key, (None, None))
                if on_done:
                    on_done(value)
            elif kind == "_error":
                self._busy.discard(key)
                _, on_error = self._callbacks.pop(key, (None, None))
                if on_error:
                    on_error(value)
        except Exception:  # noqa: BLE001 - nunca romper el pump
            import traceback
            traceback.print_exc()
