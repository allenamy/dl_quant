#!/usr/bin/env bash
# collector_monitor.sh — Monitor and restart the Binance depth collector.
#
# Designed for cron usage:
#   */5 * * * * /path/to/collector_monitor.sh >> /path/to/monitor.log 2>&1
#
# Configuration: edit the variables below or override via environment.
# ---------------------------------------------------------------------------

set -euo pipefail

# --- Configuration (override via environment) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COLLECTOR_SCRIPT="${COLLECTOR_SCRIPT:-${SCRIPT_DIR}/collect_binance_depth.py}"
PYTHON="${PYTHON:-python3}"
SYMBOL="${SYMBOL:-BTCUSDT}"
LEVELS="${LEVELS:-20}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_DIR}/data/collected}"
PID_FILE="${PID_FILE:-${PROJECT_DIR}/data/collected/.collector.pid}"
LOG_FILE="${LOG_FILE:-${PROJECT_DIR}/data/collected/collector.log}"

# --- Functions ---

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [monitor] $*"
}

is_running() {
    if [ -f "${PID_FILE}" ]; then
        local pid
        pid=$(cat "${PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

start_collector() {
    mkdir -p "$(dirname "${PID_FILE}")"
    mkdir -p "$(dirname "${LOG_FILE}")"
    mkdir -p "${OUTPUT_DIR}"

    log_msg "Starting collector: symbol=${SYMBOL} levels=${LEVELS}"

    nohup "${PYTHON}" "${COLLECTOR_SCRIPT}" \
        --symbol "${SYMBOL}" \
        --levels "${LEVELS}" \
        --output-dir "${OUTPUT_DIR}" \
        >> "${LOG_FILE}" 2>&1 &

    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    log_msg "Collector started with PID ${pid}"
}

stop_collector() {
    if is_running; then
        local pid
        pid=$(cat "${PID_FILE}")
        log_msg "Stopping collector (PID ${pid}) ..."
        kill -TERM "${pid}" 2>/dev/null || true
        # Wait up to 10 seconds for graceful shutdown
        for i in $(seq 1 10); do
            if ! kill -0 "${pid}" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        # Force kill if still running
        if kill -0 "${pid}" 2>/dev/null; then
            log_msg "Force killing PID ${pid}"
            kill -9 "${pid}" 2>/dev/null || true
        fi
        rm -f "${PID_FILE}"
        log_msg "Collector stopped"
    else
        log_msg "Collector is not running"
    fi
}

status_collector() {
    if is_running; then
        local pid
        pid=$(cat "${PID_FILE}")
        log_msg "Collector is running (PID ${pid})"
        return 0
    else
        log_msg "Collector is NOT running"
        if [ -f "${PID_FILE}" ]; then
            log_msg "Stale PID file found, removing"
            rm -f "${PID_FILE}"
        fi
        return 1
    fi
}

# --- Main ---

case "${1:-check}" in
    start)
        if is_running; then
            log_msg "Collector already running"
        else
            start_collector
        fi
        ;;
    stop)
        stop_collector
        ;;
    restart)
        stop_collector
        sleep 2
        start_collector
        ;;
    status)
        status_collector
        ;;
    check)
        # Default action for cron: restart if not running
        if ! is_running; then
            log_msg "Collector not running — restarting"
            start_collector
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        echo "  check  — restart if not running (default, for cron)"
        exit 1
        ;;
esac
