from PIL import Image
import os

img_path = 'stockxlogohd.png'
icon_path = 'icon.ico'

if os.path.exists(img_path):
    img = Image.open(img_path)
    img.save(icon_path, format='ICO', sizes=[(256, 256)])
    print(f"Converted {img_path} to {icon_path}")
else:
    print(f"{img_path} not found.")
