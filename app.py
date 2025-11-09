"""
Web UI for Digital Picture Frame Control
Flask-based interface for configuration and management
"""
from flask import Flask, render_template, request, jsonify
import json
import os
import subprocess
import psutil

app = Flask(__name__)
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from JSON file"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

@app.route('/')
def index():
    """Main control panel"""
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify(load_config())
    
    elif request.method == 'POST':
        config = request.json
        save_config(config)
        return jsonify({"status": "success", "message": "Configuration updated"})

@app.route('/api/sources/scan', methods=['POST'])
def scan_sources():
    """Scan configured sources for images"""
    config = load_config()
    image_count = 0
    
    # Count images in local paths
    for path in config['sources']['local_paths']:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                image_count += len([f for f in files if f.lower().endswith(
                    ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))])
    
    # Count images in Unraid shares
    for share in config['sources']['unraid_shares']:
        if os.path.exists(share):
            for root, dirs, files in os.walk(share):
                image_count += len([f for f in files if f.lower().endswith(
                    ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))])
    
    return jsonify({"image_count": image_count})

@app.route('/api/sources/add', methods=['POST'])
def add_source():
    """Add a new image source"""
    data = request.json
    source_type = data.get('type')  # 'local' or 'unraid'
    path = data.get('path')
    
    if not path or not os.path.exists(path):
        return jsonify({"status": "error", "message": "Invalid path"}), 400
    
    config = load_config()
    
    if source_type == 'local':
        if path not in config['sources']['local_paths']:
            config['sources']['local_paths'].append(path)
    elif source_type == 'unraid':
        if path not in config['sources']['unraid_shares']:
            config['sources']['unraid_shares'].append(path)
    
    save_config(config)
    return jsonify({"status": "success", "message": "Source added"})

@app.route('/api/sources/remove', methods=['POST'])
def remove_source():
    """Remove an image source"""
    data = request.json
    source_type = data.get('type')
    path = data.get('path')
    
    config = load_config()
    
    if source_type == 'local' and path in config['sources']['local_paths']:        config['sources']['local_paths'].remove(path)
    elif source_type == 'unraid' and path in config['sources']['unraid_shares']:
        config['sources']['unraid_shares'].remove(path)
    
    save_config(config)
    return jsonify({"status": "success", "message": "Source removed"})

@app.route('/api/overlay/toggle', methods=['POST'])
def toggle_overlay():
    """Toggle overlay on/off"""
    data = request.json
    overlay_name = data.get('name')
    
    config = load_config()
    
    if overlay_name in config['overlays']:
        config['overlays'][overlay_name]['enabled'] = not config['overlays'][overlay_name]['enabled']
        save_config(config)
        return jsonify({
            "status": "success", 
            "enabled": config['overlays'][overlay_name]['enabled']
        })
    
    return jsonify({"status": "error", "message": "Overlay not found"}), 404

@app.route('/api/overlay/configure', methods=['POST'])
def configure_overlay():
    """Update overlay configuration"""
    data = request.json
    overlay_name = data.get('name')
    settings = data.get('settings')    
    config = load_config()
    
    if overlay_name in config['overlays']:
        config['overlays'][overlay_name].update(settings)
        save_config(config)
        return jsonify({"status": "success", "message": "Overlay configured"})
    
    return jsonify({"status": "error", "message": "Overlay not found"}), 404

@app.route('/api/display/control', methods=['POST'])
def display_control():
    """Control display (start/stop/restart)"""
    action = request.json.get('action')
    
    # TODO: Implement process control for display.py
    # For now, return placeholder response
    return jsonify({
        "status": "success",
        "message": f"Display {action} command received",
        "note": "Process control to be implemented"
    })

@app.route('/api/system/stats')
def system_stats():
    """Get system statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return jsonify({
        "cpu": cpu_percent,
        "memory": {
            "percent": memory.percent,            "used_gb": memory.used / (1024**3),
            "total_gb": memory.total / (1024**3)
        }
    })

if __name__ == '__main__':
    config = load_config()
    web_config = config.get('web_ui', {})
    
    app.run(
        host=web_config.get('host', '0.0.0.0'),
        port=web_config.get('port', 5000),
        debug=True
    )