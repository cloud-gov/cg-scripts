#!/bin/bash
set -e -u

# Load up current values
echo "Looking up ${SOURCE_KEY_PATH} value..."
SOURCE_KEY_VALUE="$(credhub get -n ${SOURCE_KEY_PATH} -q)"

echo "Looking up ${TARGET_KEY_PATH} value..."
TARGET_KEY_VALUE="$(credhub get -n ${TARGET_KEY_PATH} -q)"
               
# Compare variables
echo  "Performing compares..."
if [[ "$SOURCE_KEY_VALUE" != "$TARGET_KEY_VALUE" ]]; then
    echo "SOURCE and TARGET values are different. Updating TARTGET with the value from SOURCE."
    credhub set -n ${TARGET_KEY_PATH} -t value -v "${SOURCE_KEY_VALUE}"
else
    echo "SOURCE and TARGET values match. No changes needed."
fi


echo "~fin~"