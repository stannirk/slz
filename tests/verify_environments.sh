#!/bin/bash
# SLZ Environment Verification Script
# This script verifies that SLZ remains functional across different Python versions
# and remains isolated from external library "noise".

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== SLZ Environmental Robustness Test ===${NC}"

# Function to run tests in a clean venv
run_test_env() {
    local python_bin=$1
    local extra_deps=$2
    local label=$3

    if ! command -v "$python_bin" &> /dev/null; then
        echo -e "Skipping $label: $python_bin not found."
        return
    fi

    echo -e "${BLUE}Testing $label...${NC}"
    
    # Create temp venv
    local venv_dir="temp_venv_$(date +%s)_$RANDOM"
    "$python_bin" -m venv "$venv_dir"
    source "$venv_dir/bin/activate"

    # Install dependencies
    pip install --upgrade pip &> /dev/null
    if [ -n "$extra_deps" ]; then
        echo "  > Installing extra noise: $extra_deps"
        pip install $extra_deps &> /dev/null
    fi
    
    # Install SLZ
    pip install . &> /dev/null

    # Run tests
    python -m unittest discover tests

    # Cleanup
    deactivate
    rm -rf "$venv_dir"
    echo -e "${GREEN}  > PASS${NC}"
}

# 1. Test standard supported versions
run_test_env "python3" "" "System Default Python"

# 2. Test with "Noisy" dependencies (simulating a complex dev environment)
run_test_env "python3" "requests numpy pandas" "Noisy Environment (Heavy Deps)"

# 3. Try common Python versions if they exist
for ver in "3.8" "3.9" "3.10" "3.11" "3.12" "3.13"; do
    run_test_env "python$ver" "" "Python $ver"
done

echo -e "${GREEN}=== All environmental checks passed! ===${NC}"
