#!/bin/bash
# Setup cron job for live scraper (runs every 24 hours)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Try to use venv python first, fallback to system python
if [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python3"
else
    PYTHON_PATH=$(which python3)
fi
CRON_LOG="$SCRIPT_DIR/logs/scraper_cron.log"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Create cron job entry
CRON_JOB="0 0 * * * cd $SCRIPT_DIR && $PYTHON_PATH live_scraper.py refresh >> $CRON_LOG 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "live_scraper.py refresh"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "live_scraper.py refresh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✓ Cron job installed successfully!"
echo ""
echo "Schedule: Runs every day at midnight (00:00)"
echo "Command: $PYTHON_PATH live_scraper.py refresh"
echo "Log file: $CRON_LOG"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove this cron job: crontab -e (then delete the line)"
echo ""
echo "To test manually: cd $SCRIPT_DIR && $PYTHON_PATH live_scraper.py refresh"

