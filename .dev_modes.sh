#!/bin/bash

# Usage: source .dev_modes.sh [policy|chain|infra]

function set_dev_mode() {
    local mode=$1
    echo "Switching to mode: $mode"

    case $mode in
        policy)
            alias test="pytest tests/governance/"
            alias lint="ruff check src/core/policies/"
            export DEV_ROLE="POLICY_ENGINEER"
            ;;
        chain)
            alias test="make reset-chain && pytest tests/chain/"
            alias deploy="echo 'Running simulated deployment...'"
            export DEV_ROLE="PROTOCOL_DEVELOPER"
            ;;
        infra)
            alias test="make verify-policy && pytest tests/infra/"
            alias logs="tail -f logs/ci.log"
            export DEV_ROLE="INFRA_SRE"
            ;;
        *)
            echo "Unknown mode. Usage: set_dev_mode [policy|chain|infra]"
            return 1
            ;;
    esac

    echo "Role environment set: $DEV_ROLE"
}

# Auto-complete or helper could be added here
export -f set_dev_mode
echo "Role-based dev modes loaded. Use 'set_dev_mode <mode>'"
