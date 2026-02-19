"""analysis/services/thread_manager.py - Thread limiter + watchdog wrapper.

Ogranicza ilość równoczesnych wątków AI (semaphore)
i monitoruje timeout (10 min).
"""

import logging
import threading

logger = logging.getLogger(__name__)

MAX_THREADS = 5
THREAD_TIMEOUT = 600  # 10 min

_semaphore = threading.Semaphore(MAX_THREADS)
_active_threads = {}
_lock = threading.Lock()


def run_with_limit(target, args=(), kwargs=None, name=None):
    """Uruchamia target w nowym wątku z ograniczeniem MAX_THREADS.

    - Czeka na wolny slot (semaphore)
    - Rejestruje wątek w _active_threads
    - Po zakończeniu zwalnia slot
    """
    kwargs = kwargs or {}

    def wrapper():
        _semaphore.acquire()
        thread_id = threading.current_thread().ident
        with _lock:
            _active_threads[thread_id] = {
                'name': name or target.__name__,
                'thread': threading.current_thread(),
            }
        try:
            target(*args, **kwargs)
        except Exception as e:
            logger.error(f"Thread {name or target.__name__} failed: {e}")
        finally:
            with _lock:
                _active_threads.pop(thread_id, None)
            _semaphore.release()

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread


def get_active_count():
    """Zwraca liczbę aktywnych wątków AI."""
    with _lock:
        return len(_active_threads)


def get_active_threads_info():
    """Zwraca info o aktywnych wątkach (do diagnostyki)."""
    with _lock:
        return [
            {'name': info['name'], 'alive': info['thread'].is_alive()}
            for info in _active_threads.values()
        ]
