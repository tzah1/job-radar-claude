#!/bin/bash
# setup_launchd.sh - Create a macOS launchd plist for daily Job Radar scan
#
# ┌─────────────────────────────────────────────────────────────────┐
# │  IMPORTANT: This script does NOT activate the scheduler.        │
# │                                                                 │
# │  It only creates the plist file and prints instructions.        │
# │  YOU must review the file and run the load command manually     │
# │  when you decide on a daily run time.                           │
# └─────────────────────────────────────────────────────────────────┘
#
# Usage:
#   bash scripts/setup_launchd.sh
#
# Then edit ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
# and run:
#   launchctl load ~/Library/LaunchAgents/com.jobradar.dailyscan.plist

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
PLIST_LABEL="com.jobradar.dailyscan"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
PROJECT_DIR="$HOME/Projects/job-radar-claude"
PYTHON_BIN="$(which python3)"
SCRIPT_PATH="${PROJECT_DIR}/scripts/run_daily_scan.py"
LOG_STDOUT="${PROJECT_DIR}/logs/launchd_stdout.log"
LOG_STDERR="${PROJECT_DIR}/logs/launchd_stderr.log"

# Default run time: 08:30 — edit this or change in the plist after generation
RUN_HOUR=8
RUN_MINUTE=30

# ── Check project directory ───────────────────────────────────────────────────
if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Project directory not found: $PROJECT_DIR"
    echo "Adjust PROJECT_DIR in this script."
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: run_daily_scan.py not found at $SCRIPT_PATH"
    exit 1
fi

# ── Detect Python venv if present ────────────────────────────────────────────
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    PYTHON_BIN="$VENV_PYTHON"
    echo "Found venv — using: $PYTHON_BIN"
else
    echo "No venv found — using system Python: $PYTHON_BIN"
    echo "(Recommended: create a venv first — see docs/operating_manual.md)"
fi

# ── Create LaunchAgents dir if needed ─────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "${PROJECT_DIR}/logs"

# ── Write plist ───────────────────────────────────────────────────────────────
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_BIN}</string>
        <string>${SCRIPT_PATH}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <!-- Daily run time — edit Hour and Minute to your preference -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${RUN_HOUR}</integer>
        <key>Minute</key>
        <integer>${RUN_MINUTE}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_STDOUT}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_STDERR}</string>

    <!-- Run immediately if a scheduled run was missed (e.g. Mac was asleep) -->
    <key>RunAtLoad</key>
    <false/>

</dict>
</plist>
EOF

# ── Print instructions ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  plist written to:"
echo "    $PLIST_PATH"
echo ""
echo "  Configured run time: ${RUN_HOUR}:$(printf '%02d' $RUN_MINUTE) daily"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "BEFORE ACTIVATING:"
echo "  1. Review the plist file above"
echo "  2. Edit Hour/Minute to your preferred daily run time"
echo "  3. Confirm PYTHON_BIN path is correct:"
echo "     $PYTHON_BIN"
echo ""
echo "TO ACTIVATE (run manually when ready):"
echo "  launchctl load $PLIST_PATH"
echo ""
echo "TO CHECK STATUS:"
echo "  launchctl list | grep jobradar"
echo ""
echo "TO DEACTIVATE:"
echo "  launchctl unload $PLIST_PATH"
echo ""
echo "TO TEST MANUALLY NOW:"
echo "  python scripts/run_daily_scan.py --dry-run"
echo ""
