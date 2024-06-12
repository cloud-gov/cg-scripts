# Nessus Health Check Script

This script checks the status of the Nessus license and the age of the Nessus plugin updates. It emits metrics for these checks to a Prometheus-compatible format for monitoring.

## Prerequisites

Before running the script, you need to reset the Nessus product activation and register the license key. Follow these steps:

1. **Reset the License**:

   - Go to [Tenable Community](https://community.tenable.com/products/1).
   - Click on the current license drop-down "Manage Product".
   - Click "Reset Product Activation".
   - Copy the license key provided.

2. **Log in to the Tooling Jumpbox**:

   - SSH into your tooling jumpbox where you manage your BOSH deployments.

3. **Log in to the VM for Nessus Manager**:

   - Use BOSH to SSH into the Nessus Manager VM:

     ```bash
     bosh -d nessus-manager-prod ssh nessus-manager/0
     ```

   - Once inside the Nessus Manager VM, assume the root user role and issue the Nessus CLI command to update the plugins:

     ```bash
     sudo /opt/nessus/sbin/nessuscli fetch --register LICENSE_KEY
     ```

## Running the Script

After completing the above steps, you can run the health check script. Follow these steps:

1. **Ensure Script Permissions**:

   - Make sure the script has execute permissions:

     ```bash
     chmod +x /path/to/your/script.sh
     ```

2. **Run the Script with Sudo**:

   - Execute the script with `sudo` to ensure it has the necessary permissions:

     ```bash
     sudo /path/to/your/script.sh
     ```

3. **Check the Log File**:

   - The script logs its output to `/var/log/nessus_metrics.log`. Check this log file for detailed output and troubleshooting information:

     ```bash
     sudo cat /var/log/nessus_metrics.log
     ```

## Script Details

The script performs the following tasks:

1. **Checks Nessus License Status**:

   - Searches the Nessus log file for license validation issues and emits a metric indicating the license status.

2. **Checks Nessus Plugin Update Age**:

   - Determines the age of the last Nessus plugin update and emits a metric indicating the plugin age in days.

3. **Emits Metrics**:
   - Writes the metrics to a Prometheus-compatible file for monitoring purposes.

## Troubleshooting

If you encounter any issues, check the log file for detailed output. Ensure that the Nessus log file (`/var/vcap/store/nessus-manager/opt/nessus/var/nessus/logs/nessusd.messages`) is accessible and contains the necessary log entries.

For further assistance, refer to the [Tenable Community](https://community.tenable.com/products/1) or contact your system administrator.

## Script Code

Here is the script for reference:

```bash
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
```
