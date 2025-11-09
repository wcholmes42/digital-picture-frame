# Digital Picture Frame

A sophisticated digital picture frame application with dynamic overlays, power management, and image optimization.

## Features

### Core Display
- **Smart Image Scaling**: Cover mode fills screen while preserving aspect ratio
- **EXIF Rotation**: Automatically rotates images based on camera orientation
- **Brightness Dimming**: Programmatic 50% brightness reduction for comfortable viewing
- **Image Sources**: Supports local paths and network shares (Unraid)

### Overlay System
- **Unified Top Bar**: Dark semi-transparent bar with white text
- **Clock Display**: 12-hour format with blinking colon separator
- **Date Display**: Full date with day of week
- **Matching Fonts**: Both overlays use 48px Arial font
- **Precise Positioning**: Text positioned -2px from top for optimal appearance

### Power Management
- **Auto Cycle**: 60 seconds slideshow → 30 seconds blank
- **Monitor Control**: Windows API integration to power off display
- **Manual Controls**: 
  - `B` key - Toggle monitor on/off
  - `SPACE` - Next image
  - `R` - Reload config/images
  - `ESC` - Exit

### Web UI
- Configuration interface on port 5000
- Live settings updates
- Browse and configure image sources

## Installation

### Prerequisites
```powershell
# Python 3.11+
winget install Python.Python.3.11

# Install dependencies
pip install pygame pillow flask requests --break-system-packages
```

### Setup
```powershell
# Map network share (if using Unraid)
net use P: \\192.168.68.42\frame /user:a a

# Run application
cd C:\PictureFrame
python display.py
```

## Configuration

Edit `config.json`:

```json
{
  "display": {
    "resolution": [1920, 1080],
    "slideshow_interval": 30,
    "fullscreen": true
  },
  "sources": {
    "local_paths": [],
    "unraid_shares": ["P:\\"]
  },
  "overlays": {
    "clock": {
      "enabled": true,
      "format": "%I:%M %p",
      "font_size": 48
    },
    "date": {
      "enabled": true,
      "format": "%A, %B %d, %Y",
      "font_size": 48
    }
  }
}
```

## Architecture

### display.py
Main display engine with:
- Image loading and processing (PIL/Pillow)
- Pygame rendering loop
- Overlay composition
- Power management
- Keyboard controls

### app.py
Flask web interface for:
- Configuration management
- Source browsing
- Live settings updates

### Key Classes
- `PictureFrameDisplay` - Main display controller
- Monitor power control via Windows API (ctypes)
- Image enhancement (brightness, rotation)

## Technical Details

### Image Processing Pipeline
1. Load image from source
2. Apply EXIF rotation (auto-orientation)
3. Convert to RGB
4. Scale to cover screen (maintaining aspect)
5. Center crop to exact screen size
6. Apply 50% brightness dimming
7. Render overlays
8. Display via pygame

### Overlay Rendering
1. Calculate text dimensions
2. Draw dark bar (120 alpha black)
3. Position text at -2px vertical offset
4. Render with white color (250 alpha)

### Power Save Cycle
```
[60s Slideshow] → [30s Monitor OFF] → [Repeat]
```

Monitor control uses:
- SendMessage (WM_SYSCOMMAND)
- Mouse event simulation
- SetThreadExecutionState

## File Structure
```
C:\PictureFrame\
├── display.py          # Main display engine
├── app.py             # Web UI (Flask)
├── config.json        # Configuration
├── requirements.txt   # Python dependencies
├── start.ps1         # Auto-start script
└── templates/
    └── index.html    # Web UI template
```

## Development Notes

### Scoreboard: 5 points 🏆
Built through iterative refinement with focus on:
- Clean visual design
- Precise positioning
- Smooth power management
- Reliable image processing

### Future Enhancements
- Weather API integration
- System stats overlay
- Custom fonts support
- Transition effects
- Time-based dimming schedules
- Multiple display profiles

## Version
- **Initial Release**: November 8, 2025
- **Commit**: 81a2a21
- **Platform**: Windows 10/11
- **Python**: 3.11.9
- **Display**: 1920x1080 fullscreen

---

Built with pizza fuel and late-night hacking energy. 🍕⚡
