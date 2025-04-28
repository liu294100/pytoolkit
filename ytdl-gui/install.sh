#!/bin/bash

# ==========================================================================
# Configuration Section
# ==========================================================================

# --- Python Path ---
# Set the full path to your python executable here.
# Leave empty ("") to use 'python3' or 'python' found in the system PATH.
# Example: PYTHON_EXE_CONFIG="/home/user/.pyenv/versions/3.10.5/bin/python"
PYTHON_EXE_CONFIG=""

# --- Proxy URL ---
# Set your proxy server URL here if needed.
# Leave empty ("") if you don't need a proxy.
# Example: PROXY_URL_CONFIG="http://user:password@proxy.example.com:8080"
PROXY_URL_CONFIG=""

# --- Requirements File ---
# The name of your requirements file.
REQUIREMENTS_FILE="requirements.txt"

# ==========================================================================
# Script Logic (Do not modify below unless you know what you are doing)
# ==========================================================================

# --- Functions ---
error_exit() {
    echo ""
    echo "ERROR: $1" >&2
    echo "Script finished with errors."
    exit 1
}

echo ""
echo "Python Installation Script"
echo "=========================="
echo "Using requirements file: ${REQUIREMENTS_FILE}"
echo ""


# --- Determine Python Command ---
PYTHON_CMD=""
if [ -z "$PYTHON_EXE_CONFIG" ]; then
    # Try python3 first, then python if python3 doesn't exist
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        echo "Using default 'python3' from system PATH."
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        echo "Using default 'python' from system PATH."
    else
        error_exit "Neither 'python3' nor 'python' found in PATH. Please set PYTHON_EXE_CONFIG."
    fi
else
    if [ ! -x "$PYTHON_EXE_CONFIG" ]; then
        error_exit "Configured Python executable not found or not executable at '${PYTHON_EXE_CONFIG}'."
    fi
    PYTHON_CMD="${PYTHON_EXE_CONFIG}" # Quotes handle spaces
    echo "Using configured Python at: ${PYTHON_CMD}"
fi
echo ""


# --- Determine Proxy Argument ---
PROXY_ARG=""
if [ -n "$PROXY_URL_CONFIG" ]; then
    # Use explicit quotes for the argument to handle potential special chars in URL safely with eval
    PROXY_ARG="--proxy \"${PROXY_URL_CONFIG}\""
    echo "Using configured proxy: ${PROXY_URL_CONFIG}"
else
    echo "No proxy configured."
fi
echo ""


# --- Check if requirements file exists ---
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    error_exit "Requirements file '${REQUIREMENTS_FILE}' not found in the current directory ($(pwd))."
fi


# --- Execute pip install ---
# Using eval to correctly handle the optionally quoted proxy argument
INSTALL_COMMAND="\"${PYTHON_CMD}\" -m pip install -r \"${REQUIREMENTS_FILE}\" ${PROXY_ARG}"

echo "Running command:"
echo "${INSTALL_COMMAND}" # Show the command clearly before execution
echo "========================================================================"
eval ${INSTALL_COMMAND}

# Check the exit status of the pip command
if [ $? -ne 0 ]; then
    error_exit "pip install command failed. Please check the output above."
fi

echo ""
echo "========================================================================"
echo "Installation completed successfully."
exit 0