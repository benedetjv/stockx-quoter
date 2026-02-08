from PIL import Image
import os

img_path = r"c:\Users\João\Desktop\k\stockx\stockx-logo.jpg"
icon_path = r"c:\Users\João\Desktop\k\stockx\icon.ico"

try:
    img = Image.open(img_path)
    # Create multiple sizes for the icon
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(icon_path, format='ICO', sizes=icon_sizes)
    print(f"Icon saved to {icon_path} with multiple sizes.")
except Exception as e:
    print(f"Error converting icon: {e}")
