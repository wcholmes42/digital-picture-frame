# Digital Picture Frame Auto-Start Script
# Run at system startup

# Set working directory
Set-Location "C:\PictureFrame"

# Start Flask web UI in background
Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command `"cd C:\PictureFrame; & 'C:\Users\Mind 2 AI Maker Kit\AppData\Local\Programs\Python\Python311\python.exe' app.py`"" -WindowStyle Hidden

# Wait for web UI to start
Start-Sleep -Seconds 3

# Start picture frame display (foreground)
& 'C:\Users\Mind 2 AI Maker Kit\AppData\Local\Programs\Python\Python311\python.exe' display.py
