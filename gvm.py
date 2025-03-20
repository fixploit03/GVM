import cv2
from PIL import Image, ImageDraw, ImageFont
import argparse
import sys
import os

# Set up command-line arguments
parser = argparse.ArgumentParser(description="Capture screenshots every 30 seconds from a video and create a grid with timestamps.")
parser.add_argument("-i", "--input", required=True, help="Path to the input video file (e.g., video.mp4)")
parser.add_argument("-o", "--output", required=True, help="Output filename for the grid image (e.g., grid.jpg)")
parser.add_argument("-s", "--size", type=int, default=20, help="Font size for the timestamp (default: 20)")
parser.add_argument("-w", "--width", type=int, default=5, help="Number of columns in the grid (default: 5)")
args = parser.parse_args()

# Configuration
video_path = args.input
grid_output = args.output
font_size = args.size
grid_cols = args.width
interval_sec = 30

# Validate arguments
try:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")
    if font_size <= 0:
        raise ValueError("Font size must be a positive integer")
    if grid_cols <= 0:
        raise ValueError("Grid width must be a positive integer")
    if not grid_output.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise ValueError("Output file must have a valid image extension (.jpg, .jpeg, .png)")
except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")
    sys.exit(1)

# Open the video
try:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Failed to open video file")
except Exception as e:
    print(f"Error opening video: {e}")
    sys.exit(1)

# Get video information
try:
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or total_frames <= 0:
        raise ValueError("Invalid video metadata (FPS or frame count)")
    duration_sec = total_frames / fps
    total_screenshots = int(duration_sec // interval_sec) + 1
except Exception as e:
    print(f"Error retrieving video info: {e}")
    cap.release()
    sys.exit(1)

# Load font
try:
    font = ImageFont.truetype("arial.ttf", font_size)
except Exception:
    try:
        font = ImageFont.load_default()
        print("Warning: Arial font not found, using default font")
    except Exception as e:
        print(f"Error loading font: {e}")
        cap.release()
        sys.exit(1)

# Pre-calculate text size
try:
    sample_timestamp = "00:00:00"  # Updated for HH:MM:SS format
    text_bbox = font.getbbox(sample_timestamp)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    margin = max(10, font_size // 2)
    stroke_width = max(1, font_size // 10)
except Exception as e:
    print(f"Error calculating text size: {e}")
    cap.release()
    sys.exit(1)

# Capture screenshots
screenshots = []
try:
    for i in range(total_screenshots):
        current_time = i * interval_sec
        if current_time >= duration_sec:
            break
        
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Failed to read frame at {current_time} seconds, stopping")
            break
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        # Improved timestamp with HH:MM:SS
        hours = int(current_time // 3600)
        minutes = int((current_time % 3600) // 60)
        seconds = int(current_time % 60)
        timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Add timestamp with stroke
        draw = ImageDraw.Draw(img)
        img_width, img_height = img.size
        x = img_width - text_width - margin
        y = img_height - text_height - margin
        
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                draw.text((x + offset_x, y + offset_y), timestamp, fill=(0, 0, 0), font=font)
        
        draw.text((x, y), timestamp, fill=(255, 255, 255), font=font)
        
        # Resize image to prevent dimension overflow (50% of original size)
        img = img.resize((img_width // 2, img_height // 2), Image.Resampling.LANCZOS)
        
        screenshots.append(img)
        print(f"Screenshot captured at {timestamp} ({current_time} seconds)")
except Exception as e:
    print(f"Error during screenshot capture: {e}")
    cap.release()
    sys.exit(1)

cap.release()
print(f"Total screenshots captured: {len(screenshots)}")

# Create and save the grid with dimension checking
try:
    if screenshots:
        width, height = screenshots[0].size
        grid_rows = (len(screenshots) + grid_cols - 1) // grid_cols
        grid_width = width * grid_cols
        grid_height = height * grid_rows
        
        # Check if dimensions exceed typical limits (65500 pixels)
        if grid_width > 65000 or grid_height > 65000:
            print(f"Warning: Grid dimensions ({grid_width}x{grid_height}) exceed typical limit of 65500 pixels")
            # Further reduce size if needed
            scale_factor = min(65000 // grid_width, 65000 // grid_height)
            if scale_factor < 1:
                width = width * scale_factor
                height = height * scale_factor
                screenshots = [img.resize((int(width), int(height)), Image.Resampling.LANCZOS) for img in screenshots]
                grid_width = width * grid_cols
                grid_height = height * grid_rows
        
        grid_image = Image.new("RGB", (int(grid_width), int(grid_height)), (255, 255, 255))
        for i, img in enumerate(screenshots):
            grid_image.paste(img, ((i % grid_cols) * int(width), (i // grid_cols) * int(height)))
        
        grid_image.save(grid_output)
        print(f"Grid saved as: {grid_output} with {grid_cols} columns and {grid_rows} rows")
    else:
        print("Error: No screenshots captured, grid not created")
except Exception as e:
    print(f"Error creating or saving grid: {e}")
    sys.exit(1)
