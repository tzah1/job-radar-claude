#!/bin/bash
# setup_launchd.sh - Create a macOS launchd plist for daily Job Radar scan
#
# ┌──────────────────────────────────────────────────────────────────────┐
# │  IMPORTANT: This script does NOT activate the scheduler.             │
# │                                                                      │
# │  It only writes the plist file and prints step-by-step instructions. │
# │  YOU must review the plist, set your preferred run time, and         │
# │  activate it manually with the launchctl load command below.         │
# └──────────────────────────────────────────────────────────────────────┘
#
# Usage:
#   bash scripts/setup_launchd.sh
#
# After running this script:
#   1. Test the scan manually first (see STEP 1 output below)
#   2. Edit Hour/Minute in the plist if you want a different time
#   3. Load the plist with: launchctl load <path>

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PLIST_LABEL="com.jobradar.dailyscan"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
PROJECT_DIR="$HOME/AI-Work/projects/job-radar-claude"
SCRIPT_PATH="${PROJECT_DIR}/scripts/run_daily_scan.py"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python3"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_STDOUT="${LOG_DIR}/launchd_stdout.log"
LOG_STDERR="${LOG_DIR}/launchd_stderr.log"

# Default run time: 08:30 daily.
# Edit Hour/Minute in the plist before activating if you want a different time.
RUN_HOUR=8
RUN_MINUTE=30

# ── Validate prerequisites ────────────────────────────────────────────────────
if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Project directory not found: $PROJECT_DIR"
    echo "       Adjust PROJECT_DIR in this script if the path changed."
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: run_daily_scan.py not found at: $SCRIPT_PATH"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: venv Python not found at: $VENV_PYTHON"
    echo "       Set up the venv first:"
    echo "         uv venv --python python3.12 venv"
    echo "         uv pip install --python venv/bin/python3 -r requirements.txt"
    exit 1
fi

# ── Locate uv (required for the run command) ──────────────────────────────────
# uv is typically installed via: brew install uv
UV_BIN=""
for candidate in \
    "$(which uv 2>/dev/null || true)" \
    "/opt/homebrew/bin/uv" \
    "$HOME/.local/bin/uv" \
    "$HOME/.cargo/bin/uv"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        UV_BIN="$candidate"
        break
    fi
done

if [ -z "$UV_BIN" ]; then
    echo "WARNING: uv not found in common locations — falling back to venv Python directly."
    echo "         (Recommended: brew install uv)"
    # Fallback: invoke venv Python directly (no uv)
    PROGRAM_ARGS="        <string>${VENV_PYTHON}</string>
        <string>${SCRIPT_PATH}</string>"
    MANUAL_CMD="$VENV_PYTHON $SCRIPT_PATH"
else
    echo "Found uv: $UV_BIN"
    # Preferred: use uv run so that the correct Python and dependencies are guaranteed
    PROGRAM_ARGS="        <string>${UV_BIN}</string>
        <string>run</string>
        <string>--python</string>
        <string>${VENV_PYTHON}</string>
        <string>python</string>
        <string>${SCRIPT_PATH}</string>"
    MANUAL_CMD="uv run --python ${VENV_PYTHON} python ${SCRIPT_PATH}"
fi

# ── Create required directories ───────────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR"

# ── Write the plist ───────────────────────────────────────────────────────────
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <!-- The command to run each day.
         Uses uv run with the project venv so packages are always correct.
         WorkingDirectory is set to the project root below. -->
    <key>ProgramArguments</key>
    <array>
${PROGRAM_ARGS}
    </array>

    <!-- Run from the project root so relative paths in scripts resolve correctly -->
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <!-- Provide a minimal PATH so uv and Python are found at scheduled time.
         launchd does not inherit your shell PATH. -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>

    <!-- *** EDIT THESE before activating ***
         Set Hour (0–23) and Minute (0–59) to your preferred daily run time.
         Currently: ${RUN_HOUR}:$(printf '%02d' $RUN_MINUTE) -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${RUN_HOUR}</integer>
        <key>Minute</key>
        <integer>${RUN_MINUTE}</integer>
    </dict>

    <!-- Scan output is written to these log files.
         The main scan log is also written to logs/daily_scan.log by the script itself. -->
    <key>StandardOutPath</key>
    <string>${LOG_STDOUT}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_STDERR}</string>

    <!-- Do NOT run immediately when loaded — only at the scheduled time. -->
    <key>RunAtLoad</key>
    <false/>

</dict>
</plist>
EOF

# ── Print instructions ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  plist written to:"
echo "    $PLIST_PATH"
echo ""
echo "  Scheduled run time: ${RUN_HOUR}:$(printf '%02d' $RUN_MINUTE) daily"
echo "  Run command:        $MANUAL_CMD"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "STEP 1 — Test the scan manually first (strongly recommended):"
echo ""
echo "  Dry run (no files written):"
echo "    uv run --python venv/bin/python3 python scripts/run_daily_scan.py --dry-run"
echo ""
echo "  Real run:"
echo "    uv run --python venv/bin/python3 python scripts/run_daily_scan.py"
echo ""
echo "  Check output:"
echo "    cat exports/daily_summary.md"
echo "    open exports/jobs_for_review.csv"
echo ""
echo "STEP 2 — Edit the plist run time if needed:"
echo ""
echo "  open $PLIST_PATH"
echo "  (Change the Hour and Minute values inside StartCalendarInterval)"
echo ""
echo "STEP 3 — Activate when ready (your decision):"
echo ""
echo "  launchctl load $PLIST_PATH"
echo ""
echo "OTHER COMMANDS:"
echo ""
echo "  Check status:    launchctl list | grep jobradar"
echo "  View scan log:   tail -f $LOG_DIR/daily_scan.log"
echo "  View stdout:     tail -f $LOG_STDOUT"
echo "  View stderr:     tail -f $LOG_STDERR"
echo "  Deactivate:      launchctl unload $PLIST_PATH"
echo ""
