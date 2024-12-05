#!/bin/bash

# This script checks the status of the Nessus license and the age of the Nessus plugin updates.
# It emits metrics for these checks to a Prometheus-compatible format for monitoring.

# Set constants for file paths
NESSUSD_MESSAGES="/var/vcap/store/nessus-manager/opt/nessus/var/nessus/logs/nessusd.messages"
PROM_FILE="/var/vcap/jobs/node_exporter/config/nessus.prom"
TEMPFILE=$(mktemp)

# Set the log file path for troubleshooting
LOG_FILE="/var/log/nessus_metrics.log"

# Function for logging messages with timestamps
log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Set trap for graceful error handling on script termination
trap 'log "Script terminated prematurely"; exit 1' SIGINT SIGTERM

# Ensure the log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Ensure appropriate permissions for log file and directory
chmod 700 "$(dirname "$LOG_FILE")"
chmod 600 "$LOG_FILE"

# Check the status of the Nessus license
log "Checking Nessus license..."
NESSUS_LICENSE_OUTPUT=$(sudo grep -A1 'nessusd-reloader: started' "$NESSUSD_MESSAGES" | tail -n 1)
log "Nessus license check output: $NESSUS_LICENSE_OUTPUT"
if echo "$NESSUS_LICENSE_OUTPUT" | grep -q 'Could not validate the license used on this scanner'; then
    NESSUS_LICENSE=1
else
    NESSUS_LICENSE=0
fi
log "Nessus license check complete. Result: $NESSUS_LICENSE"

# Check the age of the last Nessus plugin update
log "Checking plugin age..."
if ! PLUGIN_UPDATE_ENTRY=$(sudo grep -e 'Finished plugin update' -e 'Nessus is reloading: Plugin auto-update' "$NESSUSD_MESSAGES" | tail -n 1); then
    log "Error checking plugin update entry. Command: sudo grep -e 'Finished plugin update' -e 'Nessus is reloading: Plugin auto-update' $NESSUSD_MESSAGES | tail -n 1"
    exit 1
fi
log "Plugin update entry: $PLUGIN_UPDATE_ENTRY"

# Calculate the age of the plugin update in days
if [ -z "$PLUGIN_UPDATE_ENTRY" ]; then
    log "No plugin update entry found."
    PLUGIN_AGE=-1
else
    # Remove timezone information from the date string for proper parsing
    PLUGIN_DATE=$(echo "$PLUGIN_UPDATE_ENTRY" | awk -F '[\[\]]' '{print $2}' | sed 's/ +0000//')
    if ! PLUGIN_AGE=$(( ( $(date +%s) - $(date -d "$PLUGIN_DATE" +%s) ) / 86400 )); then
        log "Error calculating plugin age."
        exit 1
    fi
fi
log "Plugin age check complete. Age: $PLUGIN_AGE days"

# Emit metrics to a temporary file in Prometheus format
log "Emitting metrics..."
{
    echo "# HELP nessus_manager_license_invalid Nessus manager license status"
    echo "# TYPE nessus_manager_license_invalid gauge"
    echo "nessus_manager_license_invalid $NESSUS_LICENSE"
    echo "# HELP nessus_manager_plugin_age Nessus manager plugin age"
    echo "# TYPE nessus_manager_plugin_age gauge"
    echo "nessus_manager_plugin_age $PLUGIN_AGE"
} > "$TEMPFILE"

# Move the temporary file to the final destination
if ! sudo mv "$TEMPFILE" "$PROM_FILE"; then
    log "Error moving tempfile to $PROM_FILE."
    exit 1
fi
log "Metrics emitted successfully."

# Clean up the temporary file
rm -f "$TEMPFILE"

log "Script completed successfully."
