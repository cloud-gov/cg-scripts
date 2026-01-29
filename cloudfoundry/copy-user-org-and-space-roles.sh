#!/bin/bash
# Script to copy Cloud Foundry user roles from source to target user
set -e -u -o pipefail

# Function to display usage
usage() {
    echo "Usage: $0 --source-user-id <user-id> --source-origin <origin> --target-user-id <user-id> --target-origin <origin> [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --source-user-id    Source CF username"
    echo "  --source-origin     UAA origin for source user"
    echo "  --target-user-id    Target CF username"
    echo "  --target-origin     UAA origin for target user"
    echo ""
    echo "Optional:"
    echo "  --dry-run-source    Show source user roles only"
    echo "  --dry-run-target    Show commands to setup target user roles"
    echo "  --dry-run           Print all commands without executing (legacy mode)"
    echo "  --delete            Delete source user after role transfer"
    echo "  --deactivate        Deactivate source user in UAA after role transfer"
    echo "  --verbose           Enable verbose logging"
    echo ""
    echo "Examples:"
    echo "  # Show source user roles"
    echo "  $0 --source-user-id john.doe --source-origin uaa --target-user-id jane.doe --target-origin uaa --dry-run-source"
    echo ""
    echo "  # Show target setup commands"
    echo "  $0 --source-user-id john.doe --source-origin uaa --target-user-id jane.doe --target-origin uaa --dry-run-target"
    echo ""
    echo "  # Copy roles and delete source user"
    echo "  $0 --source-user-id john.doe --source-origin uaa --target-user-id jane.doe --target-origin uaa --delete"
    echo ""
    echo "Notes:"
    echo "- This will not copy over uaa group memberships like 'scim.read' or 'cloud_controller.admin'."
    echo "- Log into the CF CLI and ensure you have the necessary permissions to assign roles to the target user."
    echo "- Current limit is a hard coded maximum of 5000 roles per user due to CF API pagination."
    exit 1
}

# Initialize variables
SOURCE_USER_ID=""
SOURCE_ORIGIN=""
TARGET_USER_ID=""
TARGET_ORIGIN=""
DRY_RUN=false
DRY_RUN_SOURCE=false
DRY_RUN_TARGET=false
DELETE=false
DEACTIVATE=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source-user-id)
            SOURCE_USER_ID="$2"
            shift 2
            ;;
        --source-origin)
            SOURCE_ORIGIN="$2"
            shift 2
            ;;
        --target-user-id)
            TARGET_USER_ID="$2"
            shift 2
            ;;
        --target-origin)
            TARGET_ORIGIN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --dry-run-source)
            DRY_RUN_SOURCE=true
            shift
            ;;
        --dry-run-target)
            DRY_RUN_TARGET=true
            shift
            ;;
        --delete)
            DELETE=true
            shift
            ;;
        --deactivate)
            DEACTIVATE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$SOURCE_USER_ID" || -z "$SOURCE_ORIGIN" || -z "$TARGET_USER_ID" || -z "$TARGET_ORIGIN" ]]; then
    echo "Error: Missing required parameters"
    usage
fi

# Validate mutually exclusive options
if [[ "$DELETE" == true && "$DEACTIVATE" == true ]]; then
    echo "Error: Cannot both delete and deactivate source user"
    exit 1
fi

# Logging function
log() {
    if [[ "$VERBOSE" == true ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
    fi
}

# Function to execute or print commands based on dry-run mode
execute_command() {
    local cmd="$1"
    echo "Command: $cmd"
    if [[ "$DRY_RUN" == false ]]; then
        eval "$cmd"
    fi
}

# Function to get user GUID from CF API
get_user_guid() {
    local user_id="$1"
    local origin="$2"
    
    cf curl "/v3/users?origins=${origin}&usernames=${user_id}" | jq -r '.resources[0].guid // empty'
}

# Function to check if user exists
check_user_exists() {
    local user_id="$1"
    local origin="$2"
    local user_guid
    
    user_guid=$(get_user_guid "$user_id" "$origin")
    if [[ -z "$user_guid" || "$user_guid" == "null" ]]; then
        return 1
    else
        return 0
    fi
}

# Function to get org name from space
get_org_name_from_space() {
    local space_guid="$1"
    local space_info org_guid
    
    space_info=$(cf curl "/v3/spaces/$space_guid")
    org_guid=$(echo "$space_info" | jq -r '.relationships.organization.data.guid // empty')
    
    if [[ -n "$org_guid" ]]; then
        query_org_name "$org_guid"
    fi
}

# Function to query org name
query_org_name() {
    local org_guid="$1"
    if [[ -n "$org_guid" ]]; then
        cf curl "/v3/organizations/$org_guid" | jq -r '.name // empty'
    fi
}

# Function to query space name
query_space_name() {
    local space_guid="$1"
    if [[ -n "$space_guid" ]]; then
        cf curl "/v3/spaces/$space_guid" | jq -r '.name // empty'
    fi
}

# Function to add organization_user role via CF API
add_organization_user_role() {
    local user_guid="$1"
    local org_guid="$2"
    local org_name="$3"
    
    local payload=""
    payload=$(cat <<EOF
{
  "type": "organization_user",
  "relationships": {
    "user": {
      "data": {
        "guid": "$user_guid"
      }
    },
    "organization": {
      "data": {
        "guid": "$org_guid"
      }
    }
  }
}
EOF
)
    
    if [[ "$DRY_RUN" == true || "$DRY_RUN_TARGET" == true ]]; then
        echo "cf curl -X POST '/v3/roles' -d '$payload'"
    else
        echo "Adding organization_user role for $TARGET_USER_ID in org $org_name..."
        local response=""
        local status_code=""
        
        response=$(cf curl -X POST "/v3/roles" -d "$payload")
        status_code=$(echo "$response" | jq -r '.errors[0].code // empty')
        
        if [[ -n "$status_code" ]]; then
            # Check if it's a duplicate role error (10008)
            if [[ "$status_code" == "10008" ]]; then
                echo "  User already has organization_user role in $org_name"
            else
                echo "  Error: Failed to add organization_user role: $response"
                return 1
            fi
        else
            echo "  Successfully added organization_user role in $org_name"
        fi
    fi
}

# Function to get all user roles via API
get_user_roles_via_api() {
    local user_guid="$1"
    
    # Get all roles with increased page size to avoid pagination
    cf curl "/v3/roles?user_guids=${user_guid}&per_page=5000" | jq -r '
        .resources[] |
        .type + "|" + 
        (.relationships.organization.data.guid // "") + "|" + 
        (.relationships.space.data.guid // "")
    '
}

# Display script header
if [[ "$DRY_RUN_SOURCE" == false && "$DRY_RUN_TARGET" == false ]]; then
    echo "========================================="
    echo "Cloud Foundry User Role Transfer Script"
    echo "========================================="
    echo "Source User: $SOURCE_USER_ID (Origin: $SOURCE_ORIGIN)"
    echo "Target User: $TARGET_USER_ID (Origin: $TARGET_ORIGIN)"
    echo "Dry Run: $DRY_RUN"
    echo "Delete Source User: $DELETE"
    echo "Deactivate Source User: $DEACTIVATE"
    echo "========================================="
    echo ""
fi

log "Starting role discovery process"

# Arrays to store roles and role information
declare -a ORG_ROLES
declare -a SPACE_ROLES
declare -a ORG_USER_ROLES
declare -a SOURCE_ORG_ROLES
declare -a SOURCE_SPACE_ROLES
declare -a SOURCE_ORG_USER_ROLES

# Verify users exist
log "Verifying source user exists"
if ! check_user_exists "$SOURCE_USER_ID" "$SOURCE_ORIGIN"; then
    echo "Error: Source user '$SOURCE_USER_ID' with origin '$SOURCE_ORIGIN' not found"
    exit 1
fi

SOURCE_USER_GUID=$(get_user_guid "$SOURCE_USER_ID" "$SOURCE_ORIGIN")
log "Source user GUID: $SOURCE_USER_GUID"

# Verify target user exists (skip for dry-run-source)
if [[ "$DRY_RUN_SOURCE" == false ]]; then
    log "Verifying target user exists"
    if ! check_user_exists "$TARGET_USER_ID" "$TARGET_ORIGIN"; then
        echo "Error: Target user '$TARGET_USER_ID' with origin '$TARGET_ORIGIN' not found"
        exit 1
    fi
    TARGET_USER_GUID=$(get_user_guid "$TARGET_USER_ID" "$TARGET_ORIGIN")
    log "Target user GUID: $TARGET_USER_GUID"
fi

# Get all roles for source user
log "Getting user roles via API"
ROLES_OUTPUT=$(get_user_roles_via_api "$SOURCE_USER_GUID")

# Process roles and build command arrays
while IFS='|' read -r role_type org_guid space_guid; do
    # Skip empty lines
    if [[ -z "$role_type" ]]; then
        continue
    fi
    
    # Get org name
    org_name=""
    if [[ -n "$org_guid" ]]; then
        org_name=$(query_org_name "$org_guid")
    elif [[ -n "$space_guid" ]]; then
        # For space roles, get org name via the space
        org_name=$(get_org_name_from_space "$space_guid")
    fi


    # Get space name if space_guid exists
    space_name=""
    if [[ -n "$space_guid" ]]; then
        space_name=$(query_space_name "$space_guid")
        
        # For space roles, if we don't have org_name yet, get it from the space
        if [[ -z "$org_name" ]]; then
            # Get the organization info from the space
            space_info=$(cf curl "/v3/spaces/$space_guid")
            org_guid_from_space=$(echo "$space_info" | jq -r '.relationships.organization.data.guid // empty')
            if [[ -n "$org_guid_from_space" ]]; then
                org_name=$(query_org_name "$org_guid_from_space")
            fi
        fi
    fi
    
    # Map role types to CF CLI role names
    case "$role_type" in
        "organization_manager")
            cli_role="OrgManager"
            ;;
        "organization_billing_manager")
            cli_role="BillingManager"
            ;;
        "organization_auditor")
            cli_role="OrgAuditor"
            ;;
        "organization_user")
            cli_role="organization_user"
            ;;
        "space_manager")
            cli_role="SpaceManager"
            ;;
        "space_developer")
            cli_role="SpaceDeveloper"
            ;;
        "space_auditor")
            cli_role="SpaceAuditor"
            ;;
        "space_supporter")
            cli_role="SpaceSupporter"
            ;;
        *)
            echo "Error: Unknown role type detected: $role_type" >&2
            log "Unknown role type: $role_type"
            exit 1
            ;;
    esac
    
    # Build command arrays based on role type
    if [[ -z "$space_guid" ]]; then
        # Organization role
        if [[ "$role_type" == "organization_user" ]]; then
            ORG_USER_ROLES+=("$org_guid:$org_name")
            SOURCE_ORG_USER_ROLES+=("$org_name:$cli_role")
        else
            ORG_ROLES+=("cf set-org-role \"$TARGET_USER_ID\" \"$org_name\" $cli_role --origin \"$TARGET_ORIGIN\"")
            SOURCE_ORG_ROLES+=("$org_name:$cli_role")
        fi
    else
        # Space role
        SPACE_ROLES+=("cf set-space-role \"$TARGET_USER_ID\" \"$org_name\" \"$space_name\" $cli_role --origin \"$TARGET_ORIGIN\"")
        SOURCE_SPACE_ROLES+=("$org_name:$space_name:$cli_role")
    fi
done <<< "$ROLES_OUTPUT"

# Handle dry-run-source mode
if [[ "$DRY_RUN_SOURCE" == true ]]; then
    echo "========================================="
    echo "Source User Roles"
    echo "========================================="
    echo "User: $SOURCE_USER_ID (Origin: $SOURCE_ORIGIN)"
    echo "GUID: $SOURCE_USER_GUID"
    echo ""
    
    if [[ ${#SOURCE_ORG_ROLES[@]} -gt 0 ]]; then
        echo "Organization Roles:"
        for role_info in "${SOURCE_ORG_ROLES[@]}"; do
            IFS=':' read -r org role <<< "$role_info"
            echo "  - $org: $role"
        done
    else
        echo "No organization roles found"
    fi
    
    if [[ ${#SOURCE_ORG_USER_ROLES[@]} -gt 0 ]]; then
        echo ""
        echo "Organization User Roles:"
        for role_info in "${SOURCE_ORG_USER_ROLES[@]}"; do
            IFS=':' read -r org role <<< "$role_info"
            echo "  - $org: $role"
        done
    fi
    
    echo ""
    
    if [[ ${#SOURCE_SPACE_ROLES[@]} -gt 0 ]]; then
        echo "Space Roles:"
        for role_info in "${SOURCE_SPACE_ROLES[@]}"; do
            IFS=':' read -r org space role <<< "$role_info"
            echo "  - $org/$space: $role"
        done
    else
        echo "No space roles found"
    fi
    
    exit 0
fi

# Handle dry-run-target mode
if [[ "$DRY_RUN_TARGET" == true ]]; then
    echo "========================================="
    echo "Target User Setup Commands"
    echo "========================================="
    echo "Target User: $TARGET_USER_ID (Origin: $TARGET_ORIGIN)"
    echo ""
    
    if [[ ${#ORG_ROLES[@]} -gt 0 ]]; then
        echo "# Organization role commands:"
        for cmd in "${ORG_ROLES[@]}"; do
            echo "$cmd"
        done
    else
        echo "# No organization roles to assign"
    fi
    
    echo ""
    
    if [[ ${#ORG_USER_ROLES[@]} -gt 0 ]]; then
        echo "# Organization user role commands (via API):"
        for role_info in "${ORG_USER_ROLES[@]}"; do
            IFS=':' read -r org_guid org_name <<< "$role_info"
            echo "# Add organization_user role for org: $org_name"
        done
    fi
    
    echo ""
    
    if [[ ${#SPACE_ROLES[@]} -gt 0 ]]; then
        echo "# Space role commands:"
        for cmd in "${SPACE_ROLES[@]}"; do
            echo "$cmd"
        done
    else
        echo "# No space roles to assign"
    fi
    
    # Show post-transfer actions if specified
    echo ""
    echo "# Post-transfer actions:"
    if [[ "$DELETE" == true ]]; then
        echo "cf delete-user \"$SOURCE_USER_ID\" --origin \"$SOURCE_ORIGIN\" -f"
    elif [[ "$DEACTIVATE" == true ]]; then
        echo "uaac user deactivate \"$SOURCE_USER_ID\" --origin \"$SOURCE_ORIGIN\""
    fi
    
    exit 0
fi

# Execute role assignments
echo ""
echo "========================================="
echo "Role Assignment Commands"
echo "========================================="

# Track success for post-transfer actions
SUCCESS=true

# Execute organization role assignments
if [[ ${#ORG_ROLES[@]} -gt 0 ]]; then
    echo "Organization Roles:"
    for cmd in "${ORG_ROLES[@]}"; do
        if [[ "$DRY_RUN" == false ]]; then
            if ! eval "$cmd"; then
                echo "Error: Failed to execute: $cmd"
                SUCCESS=false
            fi
        else
            execute_command "$cmd"
        fi
    done
else
    echo "No organization roles found for $SOURCE_USER_ID"
fi

echo ""

# Execute organization_user role assignments
if [[ ${#ORG_USER_ROLES[@]} -gt 0 ]]; then
    echo "Organization User Roles:"
    for role_info in "${ORG_USER_ROLES[@]}"; do
        IFS=':' read -r org_guid org_name <<< "$role_info"
        
        # Add organization_user role
        if ! add_organization_user_role "$TARGET_USER_GUID" "$org_guid" "$org_name"; then
            SUCCESS=false
        fi
    done
else
    echo "No organization_user roles found for $SOURCE_USER_ID"
fi

echo ""

# Execute space role assignments
if [[ ${#SPACE_ROLES[@]} -gt 0 ]]; then
    echo "Space Roles:"
    for cmd in "${SPACE_ROLES[@]}"; do
        if [[ "$DRY_RUN" == false ]]; then
            if ! eval "$cmd"; then
                echo "Error: Failed to execute: $cmd"
                SUCCESS=false
            fi
        else
            execute_command "$cmd"
        fi
    done
else
    echo "No space roles found for $SOURCE_USER_ID"
fi

echo ""
echo "========================================="
echo "Post-Transfer Actions"
echo "========================================="

# Only perform post-transfer actions if role assignment was successful
if [[ "$SUCCESS" == true || "$DRY_RUN" == true ]]; then
    # Handle delete option
    if [[ "$DELETE" == true ]]; then
        echo "Deleting user $SOURCE_USER_ID..."
        DELETE_CMD="cf delete-user \"$SOURCE_USER_ID\" --origin \"$SOURCE_ORIGIN\" -f"
        execute_command "$DELETE_CMD"
    fi
    
    # Handle deactivate option
    if [[ "$DEACTIVATE" == true ]]; then
        echo "Deactivating user $SOURCE_USER_ID..."
        DEACTIVATE_CMD="uaac user deactivate \"$SOURCE_USER_ID\" --origin \"$SOURCE_ORIGIN\""
        execute_command "$DEACTIVATE_CMD"
    fi
else
    echo "Skipping post-transfer actions due to role assignment failures"
    exit 1
fi

echo ""
echo "========================================="
echo "Script completed!"
echo "========================================="

# Summary
if [[ "$DRY_RUN" == false && "$DRY_RUN_SOURCE" == false && "$DRY_RUN_TARGET" == false ]]; then
    echo ""
    echo "Summary:"
    echo "- Organization roles assigned: ${#ORG_ROLES[@]}"
    echo "- Organization user roles assigned: ${#ORG_USER_ROLES[@]}"
    echo "- Space roles assigned: ${#SPACE_ROLES[@]}"
    if [[ "$DELETE" == true ]]; then
        echo "- Source user deleted: $SOURCE_USER_ID"
    elif [[ "$DEACTIVATE" == true ]]; then
        echo "- Source user deactivated: $SOURCE_USER_ID"
    fi
fi