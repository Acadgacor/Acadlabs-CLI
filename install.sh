#!/bin/bash

echo "Installing AcadLabs CLI..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pipx is installed
if command -v pipx &> /dev/null; then
    pipx install git+https://github.com/Acadgacor/acadlabs-cli.git --force
else
    # Fallback to pip
    python3 -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git
fi

echo "AcadLabs CLI installed successfully!"
echo "Try running: acadlabs login"
