#!/bin/bash
# === DAILY CANDLE SYNC RUNNER ===
# Executor: cron @ 01:00 UTC (8 PM São Paulo time)
# SLA: 30 minutes maximum
# Purpose: Incremental refresh of last 4 candles for all symbols

set -euo pipefail

# Configuration
WORKSPACE="/var/app/crypto-futures-agent"
LOG_DIR="/var/log/crypto-futures-agent"
LOCK_FILE="/tmp/daily_candle_sync.lock"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/daily_sync_${TIMESTAMP}.log"

# Ensure directories exist
mkdir -p "${LOG_DIR}"

# ===== PREVENT CONCURRENT RUNS =====
if [ -f "${LOCK_FILE}" ]; then
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ❌ SYNC ALREADY RUNNING (lockfile exists)" | tee -a "${LOG_FILE}"
    exit 1
fi

trap "rm -f ${LOCK_FILE}; echo \"[$(date -u +'%Y-%m-%d %H:%M:%S')] 🔓 Lock released\" >> \"${LOG_FILE}\"" EXIT
touch "${LOCK_FILE}"
echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 🔒 Lock acquired" >> "${LOG_FILE}"

# ===== TIMEOUT WRAPPER =====
# Different behavior on macOS vs Linux
TIMEOUT_CMD="timeout"
if ! command -v timeout &> /dev/null; then
    TIMEOUT_CMD="gtimeout"  # macOS: brew install coreutils
fi

EXEC_TIMEOUT="30m"

# ===== MAIN EXECUTION =====
{
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 🚀 DAILY SYNC STARTING"
    echo "   Workspace: ${WORKSPACE}"
    echo "   SLA: 30 minutes"
    echo ""
    
    cd "${WORKSPACE}"
    
    # Activate virtual environment
    if [ ! -f "venv/bin/activate" ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ❌ Virtual env not found at venv/bin/activate"
        exit 1
    fi
    source venv/bin/activate
    
    # Execute python sync job with timeout
    ${TIMEOUT_CMD} ${EXEC_TIMEOUT} python3 -m scripts.daily_candle_sync \
        --workspace "${WORKSPACE}" \
        --symbols all \
        --lookback 4 \
        --mode incremental \
        2>&1
    
    SYNC_EXIT_CODE=$?
    
    echo ""
    if [ ${SYNC_EXIT_CODE} -eq 0 ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ✅ SYNC COMPLETED SUCCESSFULLY"
    elif [ ${SYNC_EXIT_CODE} -eq 124 ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ⏱️  TIMEOUT (exceeded 30 minutes)"
        echo "       This is a FAILURE - sync took too long"
        exit 124
    else
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ❌ SYNC FAILED (exit code: ${SYNC_EXIT_CODE})"
        exit ${SYNC_EXIT_CODE}
    fi
    
} | tee -a "${LOG_FILE}"

FINAL_EXIT=$?

# ===== LOG SUMMARY =====
echo "" | tee -a "${LOG_FILE}"
echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 📊 EXECUTION LOG: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 📈 Log size: $(stat -f%z "${LOG_FILE}" 2>/dev/null || stat -c%s "${LOG_FILE}") bytes" | tee -a "${LOG_FILE}"

exit ${FINAL_EXIT}
