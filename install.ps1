Write-Host "Installing AcadLabs CLI..." -ForegroundColor Cyan

# Check if python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: python is not installed. Please install Python first." -ForegroundColor Red
    exit 1
}

# Run installation
Write-Host "Running installation..." -ForegroundColor Yellow
python -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git

Write-Host "AcadLabs CLI installed successfully!" -ForegroundColor Green
Write-Host "Try running: acadlabs login" -ForegroundColor Cyan
