"""
Testes de bootstrap do Scheduler.
"""

from unittest.mock import Mock

from core.scheduler import Scheduler


def test_scheduler_start_runs_initial_h4_scan(monkeypatch):
    """start() deve executar varredura inicial de Layer 4 antes do loop principal."""
    layer_manager = Mock()
    scheduler = Scheduler(layer_manager)

    # Evitar jobs reais de schedule durante o teste
    scheduler.setup_schedules = Mock()

    # Interromper loop principal imediatamente após primeira iteração
    import schedule as schedule_module

    def _stop_loop():
        raise KeyboardInterrupt()

    monkeypatch.setattr(schedule_module, 'run_pending', _stop_loop)

    scheduler.start()

    layer_manager.h4_main_decision.assert_called_once()
