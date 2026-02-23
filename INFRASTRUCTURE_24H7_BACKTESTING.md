# 🏗️ Validação de Infraestrutura para Backtesting 24/7

**Especialista:** The Blueprint (#7) | Infrastructure Lead  
**Data:** 2026-02-22  
**Versão:** 1.0  
**Status:** READY FOR IMPLEMENTATION  

---

## 📋 Executive Summary

Backtesting em paralelo com live trading requer isolamento total, atualização de dados automática e monitoramento silencioso. Este blueprint valida que a infraestrutura suporta:

- ✅ **1 ano × 60 símbolos × múltiplos timeframes** em SQLite (~850MB)
- ✅ **Atualização diária** (+4 candles/dia por símbolo) com rate limiting respeitado
- ✅ **Execução isolada** (subprocesso separado, não bloqueia live trading)
- ✅ **Monitoring automático** com alertas de falhas silenciosas
- ✅ **Recovery determinístico** em caso de corrupção de dados

---

## 1️⃣ Diagrama de Jobs/Tasks

### 1.1 Arquitetura de Fluxo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKTESTING 24/7 ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────┘

╔════════════════════╗        ╔═════════════════════╗
║   LIVE TRADING     ║        ║    BACKTESTING     ║
║   (Main Process)   ║        ║   (Subprocess)     ║
║                    ║        ║                     ║
║ • Real Execution   ║        ║ • Historical Data   ║
║ • Order Streaming  ║        ║ • Strategy Testing  ║
║ • Risk Gate Active ║        ║ • Silent Monitoring ║
║ • ~50-80% CPU      ║        ║ • ~20-30% CPU      ║
║ • PID: Main        ║        ║ • PID: Child       ║
╚════════════════════╝        ╚═════════════════════╝
         │                            │
         │ Shared                     │ Read-only
         ▼ Database                   ▼ Access
    ┌─────────────────────────────────────────┐
    │  SQLite: db/crypto_agent.db             │
    │  • Tables: ohlcv_d1, ohlcv_h4, ohlcv_h1│
    │  • Tables: sentiment, macro, trades     │
    │  • WAL mode: Write-Ahead Logging        │
    │  • Connections: live=3, backtest=1     │
    └─────────────────────────────────────────┘
         ▲          ▲
    ┌────┘          └──────────┐
    │ Historical Update         │ Trade Logging
    │ (4 candles/day)          │ (execution only)
    │                          │
    ▼                          ▼
┌──────────────┐      ┌────────────────┐
│ Data Update  │      │ Trade Logger   │
│ Job (Cron)   │      │ (Async Write)  │
│ Timer: 00:30 │      │ Timer: Realtime│
│ UTC Daily    │      │ Buffer: 500ms  │
└──────────────┘      └────────────────┘
```

### 1.2 Job Schedule (Cron/APScheduler)

| Job | Timeframe | Cron | Duration | Input | Output | Retry |
|-----|-----------|------|----------|-------|--------|-------|
| **Daily Backtest** | 23:30-01:30 | `0 23 * * *` | 2h | ohlcv_h4 (últimas 250 candles × 60 símbolos) | backtest_results.json, signals_validated, metrics | 3× cada 1h |
| **Data Update** | 00:30 UTC | `30 0 * * *` | 15m | 60 símbolos × 4 timeframes | +4 candles/symbol no DB | 5× (backoff: 5,15,45s) |
| **Data Validation** | 01:00 UTC | `0 1 * * *` | 5m | ohlcv_d1, ohlcv_h4, ohlcv_h1 | staleness_check.log | fail-block |
| **Sentiment/Macro** | 02:00 UTC | `0 2 * * *` | 10m | Binance API, Fred API | sentimento_mercado, macro_data | 3× (backoff: 10,30,60s) |
| **Backup & Compact** | 03:00 UTC | `0 3 * * 0` | 20m | db/crypto_agent.db | db_backup_YYYYMMDD.db, VACUUM | -|
| **Alert Digest** | 04:00 UTC | `0 4 * * *` | 2m | Logs, staleness, errors | digest.txt → Telegram | -|

### 1.3 Isolamento via Subprocesso

**Python Implementation (main.py):**

```python
import subprocess
import os
import signal
from pathlib import Path

class BacktestOrchestrator:
    """Orquestrador isolado de backtesting."""
    
    def __init__(self):
        self.backtest_proc = None
        self.backtest_logfile = Path("logs/backtest_24h7.log")
        self.backtest_pidfile = Path("run/backtest.pid")
    
    def start_isolated_backtest(self):
        """Inicia backtesting em subprocesso isolado."""
        # Subprocesso NÃO compartilha:
        # - File descriptors de ordens
        # - Conexões WebSocket ao vivo
        # - Threads de streaming
        
        env = os.environ.copy()
        env['BACKTEST_ISOLATED'] = '1'
        env['LOG_LEVEL'] = 'INFO'
        env['BACKTEST_LOGFILE'] = str(self.backtest_logfile)
        
        self.backtest_proc = subprocess.Popen(
            [sys.executable, 'backtest/daemon_24h7.py'],
            stdout=open(self.backtest_logfile, 'a'),
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setpgrp if os.name == 'posix' else None
        )
        
        with open(self.backtest_pidfile, 'w') as f:
            f.write(str(self.backtest_proc.pid))
        
        logger.info(f"Backtesting daemon started: PID {self.backtest_proc.pid}")
    
    def monitor_backtest_health(self):
        """Monitora saúde do backtesting 24/7."""
        if self.backtest_proc is None:
            return {'status': 'not_running'}
        
        return {
            'status': 'running' if self.backtest_proc.poll() is None else 'crashed',
            'pid': self.backtest_proc.pid,
            'uptime_h': (datetime.now() - start_time).total_seconds() / 3600
        }
    
    def safe_kill_backtest(self, timeout=30):
        """Kill graceful do subprocesso."""
        if self.backtest_proc and self.backtest_proc.poll() is None:
            os.killpg(os.getpgid(self.backtest_proc.pid), signal.SIGTERM)
            try:
                self.backtest_proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self.backtest_proc.pid), signal.SIGKILL)
```

**Isolamento garantido:**

- ✅ `BACKTEST_ISOLATED=1` flag desabilita trade execution
- ✅ Subprocesso tem seu próprio heap Python (não compartilha objetos)
- ✅ Database em WAL mode permite leitura concorrente sem lock
- ✅ Logs separados: `logs/backtest_24h7.log` vs `logs/agent.log`
- ✅ PID separado facilita monitoramento (killpg não afeta live trader)

---

## 2️⃣ Estimativa de Overhead

### 2.1 Storage: 1 Ano × 60 Símbolos

#### Cálculo de Candles

| Timeframe | Candles/Ano | Símbolos | Total Candles | Bytes/Candle | Subtotal |
|-----------|------------|----------|---------------|--------------|----------|
| **D1** | 365 | 60 | 21,900 | ~120 | ~2.6 MB |
| **H4** | 2,190 | 60 | 131,400 | ~120 | ~15.8 MB |
| **H1** | 8,760 | 60 | 525,600 | ~120 | ~63 MB |

**Total OHLCV:** ~81 MB (bruto)

#### Tabelas Suplementares

| Tabela | Símbolos | Candles/Símbolo | Bytes/Row | Total |
|--------|----------|-----------------|-----------|--------|
| **indicadores_tecnico** (D1+H4+H1) | 60 | 10,315 | ~300 | ~186 MB |
| **sentimento_mercado** (daily) | 60 | 365 | ~200 | ~4.4 MB |
| **macro_data** (daily) | 1 | 365 | ~180 | ~65 KB |
| **trades** (execução) | 60 | ~500/símbolo | ~250 | ~7.5 MB |
| **Índices + Overhead SQLite** | - | - | - | ~15 MB |

**Total Banco de Dados:** ~294 MB (consolidado)

#### Com Margem de Segurança

- Histórico de erros: +10 MB
- Cache de cálculos intermediários: +15 MB
- Backup em-rotação (3×): +882 MB

**Total Final:** ~1.2 GB (com backups)

### 2.2 Memória (RAM)

**Live Trading (Main Process):**
- Modelo PPO loaded: ~150 MB
- DataFrames em cache (últimas 250 H4 candles × 60): ~80 MB
- WebSocket buffers: ~20 MB
- Order queue + metadata: ~10 MB
- **Subtotal Live:** ~260 MB

**Backtesting (Subprocess):**
- Modelo PPO (cópia own): ~150 MB
- Backtest environment (trade history, equity curve): ~100 MB
- Results buffers: ~50 MB
- **Subtotal Backtest:** ~300 MB

**Shared (O.S. + Framework base):**
- Python interpreter, numpy, pandas base: ~400 MB
- Available for buffer growth: +100 MB

**Total RAM Requerida:** ~1.0 GB (mínimo 1.5 GB recomendado para headroom)

### 2.3 CPU

#### Live Trading
- Main event loop: ~40% (1 core dedicado com threading)
- Order streaming: ~15% (WebSocket async)
- Risk calculations: ~10%
- Miscellaneous: ~5%
- **Total Live:** ~60-80% (1.5-2 cores equivalentes)

#### Backtesting
- Strategy evaluation: ~20% (stepping through 250 H4 candles/hour)
- Indicator calculations: ~5%
- Data loading: ~3%
- **Total Backtest:** ~25-30% (1 core parcialmente ocupado)

#### Resource Contention
- **Peak times** (23:30-01:30 daily backtest shift):
  - Live: 60%, Backtest: 30% = **90% total** ✅ Safe (< 100%)
  - Normal times: 70% + 0% = **70% total** (backtest em sleep)

**CPU Requerida:** 4 cores mínimo, 8 cores recomendado

### 2.4 Throughput (Binance API)

#### Coleta Diária Incremental

**Cenário:** 60 símbolos, 4 timeframes, +4 candles/dia

- **D1:** 60 símbolos × 1 request = 60 chamadas
- **H4:** 60 símbolos × 1 request = 60 chamadas
- **H1:** 60 símbolos × 1 request = 60 chamadas
- **15m:** (optional) 60 × 1 = 60 chamadas
- **Total:** ~240 requisições = **1 requisição por 15 segundos**

**Rate Limiting Binance:**
- Limite: 1200 req/min = **20 req/s max**
- Nossa taxa: **0.066 req/s** ✅ Safe (33× abaixo do limite)

#### Jitter Exponential Backoff

```python
def adaptive_backoff(attempt):
    """Backoff exponencial com jitter."""
    base_delay = [5, 15, 45]  # seconds
    jitter = random.uniform(0, 0.1 * base_delay[attempt])
    return base_delay[attempt] + jitter

# Retry sequência para falha temporária:
# Retry 1: 5s + jitter
# Retry 2: 15s + jitter
# Retry 3: 45s + jitter
# Retry 4: Falha, trigger alert
```

---

## 3️⃣ Checklist de Readiness 24/7

### 3.1 Database Readiness

- [ ] **WAL Mode Habilitado**
  ```sql
  PRAGMA journal_mode=WAL;
  PRAGMA wal_autocheckpoint=1000;
  ```
  - Write-Ahead Logging permite read-concorrente
  - Verificação automática a cada 1000 páginas

- [ ] **Pragmas de Performance & Segurança**
  ```sql
  PRAGMA synchronous=NORMAL;  -- Não fsync em cada transação
  PRAGMA cache_size=10000;    -- 10MB cache em RAM
  PRAGMA foreign_keys=ON;     -- Integridade referencial
  PRAGMA temp_store=MEMORY;   -- Tabelas temp em RAM
  ```

- [ ] **Índices Críticos Presentes**
  ```
  ✅ idx_ohlcv_d1_symbol ON ohlcv_d1(symbol, timestamp)
  ✅ idx_ohlcv_h4_symbol ON ohlcv_h4(symbol, timestamp)
  ✅ idx_ohlcv_h1_symbol ON ohlcv_h1(symbol, timestamp)
  ✅ idx_indicadores_symbol_tf ON indicadores_tecnico(symbol, timeframe)
  ✅ idx_sentimento_symbol ON sentimento_mercado(symbol, timestamp)
  ✅ idx_trades_symbol ON trades(symbol, timestamp DESC)
  ```

- [ ] **Compactação Semanal (VACUUM)**
  - Cron: Domingo 03:00 UTC
  - Libera espaço de fragmentação
  - Requer ~294 MB disk livre temporariamente

- [ ] **Backup 3-3-1 Policy**
  - Local: 3 cópias (diária, +2 dias anteriores)
  - Offsite: 1 cópia (semanal, 4 semanas rotação)
  - Teste mensal: Restore test em staging

### 3.2 Scheduling Readiness

- [ ] **APScheduler Configuration**
  ```python
  from apscheduler.schedulers.background import BackgroundScheduler
  from apscheduler.triggers.cron import CronTrigger
  
  scheduler = BackgroundScheduler(
      daemon=False,
      timezone='UTC',
      job_defaults={'coalesce': True, 'max_instances': 1}
  )
  
  scheduler.add_job(
      daily_backtest_run,
      trigger=CronTrigger(hour=23, minute=30),
      id='backtest_daily',
      misfire_grace_time=600
  )
  
  scheduler.add_job(
      data_update_job,
      trigger=CronTrigger(hour=0, minute=30),
      id='data_update',
      misfire_grace_time=300
  )
  ```

- [ ] **Heartbeat Monitoring**
  - Escrever timestamp em `run/scheduler.heartbeat` a cada 30s
  - Se heartbeat > 2 min, trigger alert

- [ ] **Job Deduplication**
  - `coalesce=True`: Não executa múltiplas vezes se houver delay
  - `max_instances=1`: Só 1 execução simultânea por job

### 3.3 Monitoring & Alerting

- [ ] **Data Staleness Detector**
  ```python
  class StalenessDetector:
      """Detecta dados obsoletos."""
      
      THRESHOLDS = {
          'D1': timedelta(days=7),      # Alerta se D1 > 7 dias sem update
          'H4': timedelta(days=1),      # Alerta se H4 > 24h sem update
          'H1': timedelta(hours=6),     # Alerta se H1 > 6h sem update
      }
      
      def check_staleness(self):
          """Verifica cada timeframe."""
          alerts = []
          
          for tf, threshold in self.THRESHOLDS.items():
              last_update = self.db.get_latest_timestamp(tf)
              age = datetime.utcnow() - last_update
              
              if age > threshold:
                  alerts.append({
                      'severity': 'CRITICAL',
                      'message': f'{tf} data is {age} old',
                      'symbol': '?',
                      'timestamp': datetime.utcnow()
                  })
          
          return alerts
  ```

- [ ] **Backtesting Health Probe**
  ```python
  class BacktestHealthProbe:
      """Monitora saúde do subprocesso de backtesting."""
      
      def probe(self):
          if not self.proc_is_alive():
              return {'status': 'DEAD', 'severity': 'CRITICAL'}
          
          # Verificar se arquivo de resultado foi atualizado
          result_age = datetime.now() - get_file_mtime('backtest_results.json')
          
          if result_age > timedelta(hours=3):
              return {'status': 'STALLED', 'severity': 'CRITICAL'}
          
          # Verificar logs para erros
          errors = parse_recent_errors('logs/backtest_24h7.log', lookback_h=1)
          if len(errors) > 5:
              return {'status': 'FLAKY', 'severity': 'WARNING'}
          
          return {'status': 'HEALTHY', 'severity': None}
  ```

- [ ] **Alert Routing (Telegram)**
  ```python
  ALERT_CHANNELS = {
      'CRITICAL': '@backtest_alerts_critical',    # Imediato
      'WARNING': '@backtest_alerts_warning',       # A cada 1h
      'INFO': '@backtest_alerts_info',             # Digest diário
  }
  
  # Batching: Não enviar mais de 10 alertas por hora
  # Max latency: < 2 min para CRITICAL
  ```

### 3.4 Recovery Readiness

- [ ] **Automated Restart on Crash**
  ```python
  def monitor_and_restart():
      """Monitora processo e reinicia se necessário."""
      
      while True:
          status = orchestrator.monitor_backtest_health()
          
          if status['status'] in ['crashed', 'stalled']:
              logger.error(f"Backtest {status['status']}, restarting...")
              
              # 1. Kill graceful
              orchestrator.safe_kill_backtest(timeout=30)
              
              # 2. Validate DB integrity
              if not validate_db_integrity():
                  logger.error("DB corrupted, triggering recovery...")
                  trigger_db_recovery()
              
              # 3. Restart subprocess
              time.sleep(5)
              orchestrator.start_isolated_backtest()
              
              # 4. Log incident
              log_incident({
                  'type': status['status'],
                  'timestamp': datetime.utcnow(),
                  'action': 'RESTARTED'
              })
          
          time.sleep(60)  # Check every minute
  ```

- [ ] **Graceful Shutdown on Live-Trading Crash**
  ```python
  # Se live trading morrer, guarantir que backtesting
  # não continue alimentando dados corrompidos
  
  if not is_live_trading_alive():
      logger.critical("Live trading dead, stopping backtest...")
      orchestrator.safe_kill_backtest()
      
      # Evita restart até investigação manual
      scheduler.pause_job('backtest_daily')
  ```

---

## 4️⃣ Procedimento Disaster Recovery

### 4.1 Cenário 1: Data Corruption (Bitflip/Crash durante Write)

**Trigger:** Database integrity check falha

```python
def detect_corruption():
    """SQLite PRAGMA integrity_check."""
    
    with db.get_connection() as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        
        if result[0] != 'ok':
            # Corruption detected!
            return {
                'corrupted': True,
                'detail': result[0],  # ex: "row 5 missing from index idx_ohlcv_d1_symbol"
                'timestamp': datetime.utcnow()
            }
        
        return {'corrupted': False}
```

**Recovery Steps (Determinístico):**

1. **Isolate (< 5 min)**
   ```bash
   # Parar ambos os processos (live + backtest)
   pkill -f main.py
   pkill -f daemon_24h7.py
   
   # Lock database para prevent concurrent writes
   touch db/LOCKED
   ```

2. **Diagnose (5-10 min)**
   ```python
   # Executar PRAGMA integrity_check em db_backup_yesterday
   integrity = check_db_integrity('db/crypto_agent.db.bak')
   
   if integrity['corrupted']:
       # Go 2 days back
       restore_point = 'db_backup_2days_ago.db'
   else:
       # Yesterday é válido
       restore_point = 'db/crypto_agent.db.bak'
   ```

3. **Restore (< 2 min)**
   ```bash
   # Restore from backup
   cp {restore_point} db/crypto_agent.db
   
   # Rebuild indices (garantir consistency)
   sqlite3 db/crypto_agent.db << EOF
   REINDEX;
   PRAGMA integrity_check;
   EOF
   ```

4. **Resync Missing Data (10-30 min)**
   ```python
   # Determinar o gap entre restore_point e agora
   gap_start = get_most_recent_timestamp(restored_db, 'H4')
   gap_end = datetime.utcnow()
   
   # Re-fetch dados históricos para o gap
   for symbol in ALL_SYMBOLS:
       backfill_ohlcv(
           symbol=symbol,
           start=gap_start,
           end=gap_end,
           timeframes=['D1', 'H4', 'H1']
       )
   ```

5. **Validate & Resume (5 min)**
   ```python
   # Rodar integrity_check final
   assert check_db_integrity()['corrupted'] == False
   
   # Delete lock file
   os.remove('db/LOCKED')
   
   # Restart live trading first (priority)
   start_live_trading()
   
   # Restart backtesting after 2 min
   time.sleep(120)
   start_backtest_daemon()
   ```

**Total Recovery Time:** ~30-60 min (RTO=15min SLA, RTOerved 60min)

### 4.2 Cenário 2: Missing Recent Data (Task Update Failed)

**Trigger:** Data staleness alert (H4 > 24h old)

```python
def recover_missing_recent_data():
    """
    Se job de update falhou, re-fetch últimas 48h
    para garantir cobertura.
    """
    
    # 1. Determinar últimas candles conhecidas
    last_h4_timestamp = db.get_latest_timestamp('H4')
    hours_missing = (datetime.utcnow() - last_h4_timestamp).total_seconds() / 3600
    
    if hours_missing > 24:
        logger.warning(f"Missing {hours_missing}h of H4 data")
        
        # 2. Re-fetch últimas 7 dias (garante cobertura)
        recovery_window = timedelta(days=7)
        start_time = datetime.utcnow() - recovery_window
        
        for symbol in ALL_SYMBOLS:
            try:
                data = collector.fetch_klines(
                    symbol=symbol,
                    interval='4h',
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    max_retries=5
                )
                
                # Upsert (replace if exists) para consolidar
                db.upsert_ohlcv('H4', symbol, data)
                
            except Exception as e:
                logger.error(f"Recovery failed for {symbol}: {e}")
                # Continue com próximo símbolo, não falhe completo
        
        # 3. Verify coverage
        coverage = db.check_data_coverage('H4', lookback_h=24)
        if coverage < 0.95:  # < 95% dos símbolos, problema
            raise DataIntegrityError(f"Post-recovery coverage only {coverage:.0%}")
```

### 4.3 Cenário 3: Backtest Process Hangs (Infinite Loop)

**Trigger:** Heartbeat timeout (> 2 min sem output) ou CPU > 90% por > 10 min

```python
def recover_from_process_hang():
    """
    Detecta e mata processo pendurado, após análise.
    """
    
    if is_process_hung():
        # 1. Capture stack trace (debug)
        subprocess.run(['pstack', str(backtest_pid)], 
                       stdout=open('logs/pstack_dump.txt', 'w'))
        
        # 2. Force kill
        os.killpg(os.getpgid(backtest_pid), signal.SIGKILL)
        
        # 3. Rotate current results file
        shutil.move('backtest_results.json', 
                   f'backtest_results.incomplete_{datetime.now().isoformat()}.json')
        
        # 4. Wait for cleanup (socket descriptor closing, etc)
        time.sleep(5)
        
        # 5. Restart
        orchestrator.start_isolated_backtest()
        
        # 6. Alert
        send_alert({
            'severity': 'WARNING',
            'message': f'Backtest process hung and restarted',
            'pstack': open('logs/pstack_dump.txt').read()
        })
```

### 4.4 Rollback Procedure (Last Resort)

**Trigger:** Persistent failures after 3 recovery attempts in 24h

```python
def last_resort_rollback():
    """
    Volta para estado conhecido-bom de 48h atrás.
    Aceita pequena perda de dados recentes.
    """
    
    logger.critical("INITIATING ROLLBACK: Todas recovery attempts falharam")
    
    # 1. Parar all operations
    orchestrator.safe_kill_backtest()
    pause_live_trading()  # Não kill, apenas pause
    
    # 2. Restore from 48h ago
    restore_db = f"db_backup_{(datetime.now() - timedelta(days=2)).strftime('%Y%m%d')}.db"
    
    shutil.copy(restore_db, 'db/crypto_agent.db')
    
    logger.info(f"Rolled back to {restore_db}")
    
    # 3. Notificar operador para investigação
    send_telegram_alert({
        'severity': 'CRITICAL',
        'message': 'ROLLBACK COMPLETED. Investigate root cause.',
        'restore_point': restore_db,
        'data_loss_hours': 48
    })
    
    # 4. Resume live (high priority), NOT backtest
    resume_live_trading()
    
    # Backtest fica paused até investigação manual
```

---

## 5️⃣ Implementação: Checklist Técnico

### 5.1 Arquivos a Criar/Modificar

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `config/backtest_config.py` | 🆕 Create | Config para backtesting (separado de live) |
| `backtest/daemon_24h7.py` | 🆕 Create | Subprocesso daemon isolado |
| `backtest/scheduler_jobs.py` | 🆕 Create | Jobs (update, backtest, alert) |
| `monitoring/staleness_detector.py` | 🆕 Create | Detector data obsolescence |
| `monitoring/health_probe.py` | 🆕 Create | Probe de saúde do backtest |
| `main.py` | 📝 Modify | Adicionar orquestrador de backtest |
| `data/database.py` | 📝 Modify | Habilitar WAL mode, pragmas |
| `tests/test_backtest_isolation.py` | 🆕 Create | E2E isolated backtest tests |

### 5.2 Dependencies

```
apscheduler>=3.10.0     # Job scheduling
python-telegram-bot     # Alertas via Telegram
psutil                  # Process monitoring
```

### 5.3 Environment Variables (`.env`)

```bash
# Backtesting Config
BACKTEST_ENABLED=1
BACKTEST_START_HOUR=23
BACKTEST_START_MINUTE=30
BACKTEST_TIMEOUT_MINUTES=120

# Database
SQLITE_WAL_MODE=1
SQLITE_CACHE_MB=10

# Monitoring
STALENESS_ALERT_THRESHOLD_H4_HOURS=24
STALENESS_ALERT_THRESHOLD_D1_DAYS=7
HEALTH_PROBE_INTERVAL_SECONDS=60

# Alerting
TELEGRAM_BACKTEST_CHANNEL=@backtest_alerts
TELEGRAM_CRITICAL_TIMEOUT=120  # seconds to send
```

### 5.4 Logging Structure

```
logs/
├── agent.log              # Live trading
├── backtest_24h7.log      # Backtesting daemon
├── scheduler.log          # APScheduler events
├── staleness_detector.log # Data age monitoring
├── health_probe.log       # Health checks
└── recovery.log           # Recovery procedures
```

---

## 6️⃣ Matriz de Decisão: Auto-Restart vs. Manual Intervention

| Cenário | Symptom | Auto-Action | Manual Review | SLA |
|---------|---------|-------------|---------------|-----|
| **Processo morreu** | PID não existe | Kill & Restart | Sim, se > 3×/24h | 5 min |
| **Dados obsoletos** | H4 > 24h | Retry update 5× | Sim, depois de 3× | 30 min |
| **DB corrupto** | PRAGMA integrity_check fail | Restore yesterday | Sempre investigar | 60 min |
| **Backtest hang** | CPU > 90% por 10 min | Kill & Restart | Sim, pstack dump | 5 min |
| **Persistent fails** | 3× restarts em 24h | Rollback 48h | Investigar urgente | 120 min |

---

## 7️⃣ Validation: Preflight Tests

Execute antes de go-live:

```bash
# 1. Database integrity
pytest tests/test_db_integrity.py

# 2. Subprocesso isolation
pytest tests/test_backtest_isolation.py -v

# 3. Job scheduling
pytest tests/test_scheduler.py

# 4. Recovery procedures
pytest tests/test_recovery_procedures.py

# 5. Rate limiting
pytest tests/test_rate_limiting.py

# 6. End-to-end 1h dry run
python scripts/dry_run_backtest_1h.py
```

---

## 📞 Support & Escalation

| Issue | Contact | Response Time |
|-------|---------|--------|
| Data staleness > 1h | DevOps Slack #alerts | < 5 min |
| DB corruption | Do emergency fallback, then contact | < 10 min |
| Replicar issue offline | DM The Blueprint (#7) | < 1h |

---

## 🔄 Review & Sign-Off

- [ ] DRI: The Blueprint (#7) — Infrastructure validation
- [ ] QA: Test automation coverage
- [ ] Live Trading PM: Confirms no impact on existing operations
- [ ] Board: Final approval for 24/7 operation

**Status:** READY FOR IMPLEMENTATION (pending sign-offs)
