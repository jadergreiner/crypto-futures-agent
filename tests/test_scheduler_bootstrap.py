"""
Testes de bootstrap do Scheduler.
"""

from unittest.mock import Mock

from core.scheduler import Scheduler
import schedule as schedule_module


def test_scheduler_start_runs_initial_h4_scan(monkeypatch):
    """start() deve executar varredura inicial de Layer 4 antes do loop principal."""
    layer_manager = Mock()
    scheduler = Scheduler(layer_manager)

    # Evitar jobs reais de schedule durante o teste
    scheduler.setup_schedules = Mock()

    # Interromper loop principal imediatamente após primeira iteração
    def _stop_loop():
        raise KeyboardInterrupt()

    monkeypatch.setattr(schedule_module, 'run_pending', _stop_loop)

    scheduler.start()

    layer_manager.h4_main_decision.assert_called_once()


def test_layer3_m15_runs_main_decision():
    """Layer 3 M15 deve sempre executar análise principal."""
    layer_manager = Mock()
    scheduler = Scheduler(layer_manager)

    scheduler._run_layer3_m15()

    layer_manager.h4_main_decision.assert_called_once()


def test_setup_schedules_registers_four_m15_slots():
    """setup_schedules() deve registrar 4 slots por hora para M15 (:00/:15/:30/:45)."""
    schedule_module.clear()
    layer_manager = Mock()
    scheduler = Scheduler(layer_manager)

    scheduler.setup_schedules()

    m15_jobs = [
        job for job in schedule_module.jobs
        if getattr(job.job_func, '__name__', '') == '_run_layer3_m15'
    ]

    assert len(m15_jobs) == 4
    schedule_module.clear()
