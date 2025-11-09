"""
Digital Picture Frame Display Engine
Full-screen image display with overlay support
"""
import pygame
import json
import os
import time
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import random
import colorsys
import ctypes

class PictureFrameDisplay:
    # Windows API constants
    HWND_BROADCAST = 0xFFFF
    WM_SYSCOMMAND = 0x0112
    SC_MONITORPOWER = 0xF170
    MONITOR_OFF = 2
    MONITOR_ON = -1
    
    def __init__(self, config_path="config.json"):
        # Load configuration
        self.config_path = config_path
        self.config_mtime = 0
        self.load_config()
        
        # Initialize pygame
        pygame.init()
        
        # Set up display
        display_config = self.config['display']
        self.width, self.height = display_config['resolution']
        
        if display_config['fullscreen']:
            self.screen = pygame.display.set_mode(
                (self.width, self.height),
                pygame.FULLSCREEN | pygame.NOFRAME
            )
        else:            self.screen = pygame.display.set_mode((self.width, self.height))
        
        pygame.display.set_caption("Digital Picture Frame")
        self.clock = pygame.time.Clock()
        
        # Image management
        self.current_image = None
        self.image_list = []
        self.current_index = 0
        self.last_change = time.time()
        self.interval = display_config['slideshow_interval']
        
        # Blank/power save mode
        self.blank_mode = False
        self.mode_start_time = time.time()
        self.slideshow_duration = 999999999  # Will be set by load_config()
        self.blank_duration = 30  # Will be set by load_config()
        
        # Load images from sources
        self.load_images()
        
    def turn_monitor_off(self):
        """Turn off monitor using Windows API"""
        try:
            ctypes.windll.user32.SendMessageW(
                self.HWND_BROADCAST,
                self.WM_SYSCOMMAND,
                self.SC_MONITORPOWER,
                self.MONITOR_OFF
            )
            print("Monitor powered OFF")
        except Exception as e:
            print(f"Failed to turn off monitor: {e}")
    
    def turn_monitor_on(self):
        """Turn on monitor using Windows API"""
        try:
            # Method 1: SendMessage
            ctypes.windll.user32.SendMessageW(
                self.HWND_BROADCAST,
                self.WM_SYSCOMMAND,
                self.SC_MONITORPOWER,
                self.MONITOR_ON
            )
            # Method 2: Simulate mouse movement to wake (more reliable)
            ctypes.windll.user32.mouse_event(1, 0, 0, 0, 0)
            # Method 3: Set thread execution state to prevent sleep
            ES_CONTINUOUS = 0x80000000
            ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED)
            print("Monitor powered ON")
        except Exception as e:
            print(f"Failed to turn on monitor: {e}")
        
    def load_config(self):
        """Load or reload configuration from file"""
        try:
            with open(self.config_path) as f:
                self.config = json.load(f)
            self.config_mtime = os.path.getmtime(self.config_path)
            
            # Update display settings
            display_config = self.config['display']
            self.interval = display_config['slideshow_interval']
            
            # Update power save settings
            if display_config.get('enable_power_save', False):
                self.slideshow_duration = display_config.get('power_save_slideshow_duration', 60)
                self.blank_duration = display_config.get('power_save_blank_duration', 30)
            else:
                self.slideshow_duration = 999999999  # Effectively disabled
                self.blank_duration = 30
                
            print(f"Config reloaded - interval: {self.interval}s, power save: {display_config.get('enable_power_save', False)}")
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def check_config_changes(self):
        """Check if config file has been modified and reload if needed"""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime != self.config_mtime:
                print("Config file changed - reloading...")
                self.load_config()
                self.load_images()  # Reload images if sources changed
                return True
        except Exception as e:
            print(f"Error checking config: {e}")
        return False
    
    def load_images(self):
        """Scan all configured sources for images"""
        self.image_list = []
        
        # Load from local paths
        for path in self.config['sources']['local_paths']:
            if os.path.exists(path):
                self.scan_directory(path)
        
        # Load from Unraid shares
        for share in self.config['sources']['unraid_shares']:
            if os.path.exists(share):
                self.scan_directory(share)
        
        # Shuffle for variety
        random.shuffle(self.image_list)        
        print(f"Loaded {len(self.image_list)} images")
    
    def scan_directory(self, path):
        """Recursively scan directory for image files"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for root, dirs, files in os.walk(path):
            for file in files:
                if Path(file).suffix.lower() in valid_extensions:
                    self.image_list.append(os.path.join(root, file))
    
    def load_current_image(self):
        """Load and scale current image to fit screen"""
        if not self.image_list:
            print("ERROR: No images in list")
            return None
        
        try:
            img_path = self.image_list[self.current_index]
            print(f"Loading: {img_path}")
            img = Image.open(img_path)
            print(f"  Opened: {img.size}, mode: {img.mode}")
            
            # Apply EXIF rotation if present
            img = ImageOps.exif_transpose(img)
            print(f"  After rotation: {img.size}")
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate scale to fill screen (cover mode)
            img_ratio = img.width / img.height
            screen_ratio = self.width / self.height
            
            if img_ratio > screen_ratio:
                # Image is wider - scale to height, crop width
                new_height = self.height
                new_width = int(img.width * (self.height / img.height))
            else:
                # Image is taller - scale to width, crop height
                new_width = self.width
                new_height = int(img.height * (self.width / img.width))
            
            # Scale image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"  Scaled to: {img.size}")
            
            # Crop to screen size (center crop)
            left = (new_width - self.width) // 2
            top = (new_height - self.height) // 2
            img = img.crop((left, top, left + self.width, top + self.height))
            print(f"  Cropped to: {img.size}")
            
            # Apply brightness dimming (50% brightness as POC)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.5)  # 0.5 = 50% brightness
            print(f"  Dimmed to 50% brightness")
            
            return img
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            return None
    
    def draw_text_with_glow(self, draw, pos, text, font, color, glow_size=3):
        """Draw text with a subtle glow effect"""
        x, y = pos
        
        # Create very light glow color (barely visible white)
        glow_color = (255, 255, 255, 40)
        
        # Draw glow in multiple directions
        for offset_x in range(-glow_size, glow_size + 1):
            for offset_y in range(-glow_size, glow_size + 1):
                if offset_x != 0 or offset_y != 0:  # Skip center
                    draw.text((x + offset_x, y + offset_y), text, font=font, fill=glow_color)
        
        # Draw main text on top
        draw.text(pos, text, font=font, fill=color)
    
    def get_average_image_color(self, image):
        """Calculate average color of entire image with enhanced contrast"""
        # Resize for faster processing
        small = image.resize((100, 100), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())
        
        # Calculate average RGB
        r_sum, g_sum, b_sum = 0, 0, 0
        for pixel in pixels:
            r_sum += pixel[0]
            g_sum += pixel[1]
            b_sum += pixel[2]
        
        count = len(pixels)
        avg_r = r_sum / count / 255.0
        avg_g = g_sum / count / 255.0
        avg_b = b_sum / count / 255.0
        
        # Convert to HSL
        h, l, s = colorsys.rgb_to_hls(avg_r, avg_g, avg_b)
        
        # Double the contrast: if dark, make 2x darker; if light, make 2x lighter
        if l < 0.5:
            l = max(0, l * 0.5)  # Make twice as dark
        else:
            l = min(1.0, l + (1.0 - l) * 0.5)  # Make twice as bright
        
        # Convert back to RGB
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        
        return (int(r * 255), int(g * 255), int(b * 255), 230)
    
    def get_contrast_color(self, image, pos, width, height):
        """Calculate complementary color for maximum contrast using color theory"""
        # Sample region where text will be drawn
        x1, y1 = int(pos[0]), int(pos[1])
        x2, y2 = min(x1 + int(width), image.width), min(y1 + int(height), image.height)
        
        # Ensure valid bounds
        x1, y1 = max(0, x1), max(0, y1)
        if x2 <= x1 or y2 <= y1:
            return (255, 255, 255, 230)  # Default to white
        
        # Crop region and calculate average color
        region = image.crop((x1, y1, x2, y2))
        pixels = list(region.getdata())
        
        # Calculate average RGB
        r_sum, g_sum, b_sum = 0, 0, 0
        for pixel in pixels:
            if isinstance(pixel, int):
                r_sum += pixel
                g_sum += pixel
                b_sum += pixel
            else:
                r_sum += pixel[0]
                g_sum += pixel[1]
                b_sum += pixel[2]
        
        count = len(pixels)
        avg_r = r_sum / count / 255.0
        avg_g = g_sum / count / 255.0
        avg_b = b_sum / count / 255.0
        
        # Convert RGB to HSL
        h, l, s = colorsys.rgb_to_hls(avg_r, avg_g, avg_b)
        
        # Calculate complementary hue (opposite on color wheel)
        comp_h = (h + 0.5) % 1.0
        
        # Boost saturation for vibrant contrast
        comp_s = min(1.0, s + 0.3)
        
        # Adjust lightness for readability
        # If background is dark, use light complementary; if light, use dark
        if l < 0.5:
            comp_l = min(0.9, l + 0.5)  # Brighten
        else:
            comp_l = max(0.2, l - 0.5)  # Darken
        
        # Convert back to RGB
        comp_r, comp_g, comp_b = colorsys.hls_to_rgb(comp_h, comp_l, comp_s)
        
        return (int(comp_r * 255), int(comp_g * 255), int(comp_b * 255), 230)
    
    def render_overlays(self, image):
        """Apply all enabled overlays to the image"""
        draw = ImageDraw.Draw(image, 'RGBA')
        
        # Calculate overlay info
        clock_info = None
        date_info = None
        
        # Clock overlay
        if self.config['overlays']['clock']['enabled']:
            cfg = self.config['overlays']['clock']
            now = datetime.now()
            text = now.strftime(cfg['format'])
            if now.second % 2 == 1:
                text = text.replace(':', ' ')
            
            try:
                font = ImageFont.truetype("arial.ttf", cfg['font_size'])
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = self.width - text_width - 20
            clock_info = (text, font, x, text_width, text_height)
        
        # Date overlay
        if self.config['overlays']['date']['enabled']:
            cfg = self.config['overlays']['date']
            now = datetime.now()
            text = now.strftime(cfg['format'])
            
            try:
                font = ImageFont.truetype("arial.ttf", cfg['font_size'])
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = 20
            date_info = (text, font, x, text_width, text_height)
        
        # Draw bar sized to clock height
        if clock_info:
            clock_text, clock_font, clock_x, clock_width, clock_height = clock_info
            
            # Bar height with even padding
            padding = 8
            bar_height = clock_height + (padding * 2)
            
            # Draw darkened bar at top
            draw.rectangle([0, 0, self.width, bar_height], fill=(0, 0, 0, 120))
            
            # Use pure white for all text
            white_color = (255, 255, 255, 250)
            
            # Position text at very top of bar (or slightly above)
            text_y = -2  # Negative to move text up into/above bar top edge
            
            # Draw clock
            draw.text((clock_x, text_y), clock_text, font=clock_font, fill=white_color)
            
            # Draw date at same height
            if date_info:
                date_text, date_font, date_x, date_width, date_height = date_info
                draw.text((date_x, text_y), date_text, font=date_font, fill=white_color)
        
        # Weather overlay (if API configured)
        if self.config['overlays']['weather']['enabled']:
            self.render_weather(image, draw)
        
        # System stats overlay
        if self.config['overlays']['system_stats']['enabled']:
            self.render_system_stats(image, draw)
        
        return image    
    def render_clock(self, image, draw):
        """Render clock overlay with blinking colon and adaptive contrast"""
        cfg = self.config['overlays']['clock']
        now = datetime.now()
        text = now.strftime(cfg['format'])
        
        # Blink colon on odd seconds
        if now.second % 2 == 1:
            text = text.replace(':', ' ')
        
        try:
            font = ImageFont.truetype("arial.ttf", cfg['font_size'])
        except:
            font = ImageFont.load_default()
        
        # Calculate position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        pos = self.calculate_position(cfg['position'], text_width, text_height)
        
        # Draw darkened bar across full width
        padding = 15
        bar_y1 = pos[1] - padding
        bar_y2 = pos[1] + text_height + padding
        draw.rectangle([0, bar_y1, self.width, bar_y2], fill=(0, 0, 0, 120))
        
        # Get average image color and make it brighter
        color = self.get_average_image_color(image)
        # Brighten the color
        r, g, b, a = color
        r = min(255, int(r * 1.8))
        g = min(255, int(g * 1.8))
        b = min(255, int(b * 1.8))
        bright_color = (r, g, b, 250)
        
        # Draw text on top of bar
        draw.text(pos, text, font=font, fill=bright_color)
    
    def render_date(self, image, draw):
        """Render date overlay with adaptive contrast"""
        cfg = self.config['overlays']['date']
        now = datetime.now()
        text = now.strftime(cfg['format'])        
        try:
            font = ImageFont.truetype("arial.ttf", cfg['font_size'])
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        pos = self.calculate_position(cfg['position'], text_width, text_height)
        
        # Draw darkened bar across full width
        padding = 15
        bar_y1 = pos[1] - padding
        bar_y2 = pos[1] + text_height + padding
        draw.rectangle([0, bar_y1, self.width, bar_y2], fill=(0, 0, 0, 120))
        
        # Get average image color and make it brighter
        color = self.get_average_image_color(image)
        # Brighten the color
        r, g, b, a = color
        r = min(255, int(r * 1.8))
        g = min(255, int(g * 1.8))
        b = min(255, int(b * 1.8))
        bright_color = (r, g, b, 250)
        
        # Draw text on top of bar
        draw.text(pos, text, font=font, fill=bright_color)
    
    def render_weather(self, image, draw):
        """Render weather overlay (placeholder - needs API integration)"""
        cfg = self.config['overlays']['weather']
        if not cfg.get('api_key'):
            return
        
        # TODO: Implement weather API call
        text = "Weather API not configured"
        
        try:
            font = ImageFont.truetype("arial.ttf", cfg['font_size'])
        except:            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        pos = self.calculate_position(cfg['position'], text_width, text_height)
        
        # Draw text only (no background)
        draw.text(pos, text, font=font, fill=tuple(cfg['color']))
    
    def render_system_stats(self, image, draw):
        """Render system stats overlay (CPU, Memory, etc)"""
        cfg = self.config['overlays']['system_stats']
        
        # TODO: Implement system stats collection
        text = "System Stats"
        
        try:
            font = ImageFont.truetype("arial.ttf", cfg['font_size'])
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]        
        pos = self.calculate_position(cfg['position'], text_width, text_height)
        
        # Draw text only (no background)
        draw.text(pos, text, font=font, fill=tuple(cfg['color']))
    
    def calculate_position(self, position, text_width, text_height):
        """Calculate pixel position from position string"""
        margin = 20
        
        positions = {
            'top-left': (margin, margin),
            'top-right': (self.width - text_width - margin, margin),
            'bottom-left': (margin, self.height - text_height - margin),
            'bottom-right': (self.width - text_width - margin, 
                           self.height - text_height - margin),
            'center': ((self.width - text_width) // 2, 
                      (self.height - text_height) // 2)
        }
        
        return positions.get(position, (margin, margin))
    
    def next_image(self):
        """Advance to next image in slideshow"""
        if not self.image_list:
            print("No images in list")
            return        
        self.current_index = (self.current_index + 1) % len(self.image_list)
        print(f"Advancing to image {self.current_index + 1}/{len(self.image_list)}")
        self.last_change = time.time()
        self.current_image = self.load_current_image()
    
    def run(self):
        """Main display loop"""
        running = True
        
        # Hide mouse cursor during slideshow
        pygame.mouse.set_visible(False)
        
        # Load first image
        if self.image_list:
            self.current_image = self.load_current_image()
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.mouse.set_visible(True)
                    running = False
                elif event.type == pygame.KEYDOWN:
                    print(f"Key pressed: {event.key}")  # Debug key code
                    
                    # Wake monitor if in blank mode
                    if self.blank_mode and event.key != pygame.K_ESCAPE:
                        print("Key detected - waking monitor")
                        self.turn_monitor_on()
                        self.blank_mode = False
                        self.mode_start_time = time.time()
                        self.last_change = time.time()
                    
                    if event.key == pygame.K_ESCAPE:
                        # Show mouse cursor before exiting
                        pygame.mouse.set_visible(True)
                        running = False
                    elif event.key == pygame.K_SPACE:
                        print("Space pressed - advancing image")
                        self.next_image()
                    elif event.key == pygame.K_b:
                        # Manual blank toggle for testing
                        if self.blank_mode:
                            print("B pressed - waking monitor")
                            self.turn_monitor_on()
                            self.blank_mode = False
                            self.mode_start_time = time.time()
                        else:
                            print("B pressed - blanking monitor")
                            self.turn_monitor_off()
                            self.blank_mode = True
                            self.mode_start_time = time.time()
                    elif event.key == pygame.K_r:
                        print("R pressed - reloading config and images")
                        # Reload config
                        with open("config.json") as f:
                            self.config = json.load(f)
                        # Reload image list and interval
                        self.interval = self.config['display']['slideshow_interval']
                        self.load_images()
                        self.current_image = self.load_current_image()
            
            # Check for config file changes (live reload)
            self.check_config_changes()
            
            # Check if time to switch between slideshow and blank mode
            time_in_mode = time.time() - self.mode_start_time
            if self.blank_mode:
                # In blank mode - check if time to return to slideshow
                if time_in_mode > self.blank_duration:
                    print("Exiting blank mode - resuming slideshow")
                    self.turn_monitor_on()
                    self.blank_mode = False
                    self.mode_start_time = time.time()
                    self.last_change = time.time()  # Reset image timer
            else:
                # In slideshow mode - check if time to blank
                if time_in_mode > self.slideshow_duration:
                    print("Entering blank mode for 30 seconds")
                    self.turn_monitor_off()
                    self.blank_mode = True
                    self.mode_start_time = time.time()
            
            # Render based on current mode
            if self.blank_mode:
                # Show black screen
                self.screen.fill((0, 0, 0))
            else:
                # Normal slideshow mode
                # Check if time to change image
                if time.time() - self.last_change > self.interval:
                    self.next_image()
                
                # Render current image with overlays
                if self.current_image:
                    # Apply overlays
                    display_image = self.current_image.copy()
                    display_image = self.render_overlays(display_image)
                    
                    # Convert PIL image to pygame surface
                    mode = display_image.mode
                    size = display_image.size
                    data = display_image.tobytes()
                    
                    py_image = pygame.image.fromstring(data, size, mode)
                    self.screen.blit(py_image, (0, 0))
                else:
                    print("WARNING: No current_image to display")
            
            pygame.display.flip()
            self.clock.tick(30)  # 30 FPS for smooth overlays
        
        pygame.quit()

if __name__ == "__main__":
    # Create and run display
    try:
        frame = PictureFrameDisplay()
        frame.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        pygame.quit()
        sys.exit(1)