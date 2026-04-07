@echo off

echo Installing AcadLabs CLI...

:: Check if python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: python is not installed. Please install Python first.
    exit /b 1
)

:: Run installation
python -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git

echo AcadLabs CLI installed successfully!
echo Try running: acadlabs login
