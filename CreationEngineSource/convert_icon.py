from PIL import Image
import os

try:
    img = Image.open(r"c:\Users\thatg\Desktop\Creator\assets\icon.png")
    # Convert to RGBA to preserve transparency
    img = img.convert("RGBA")
    # Save as .ico with multiple sizes proper for Windows
    img.save(r"c:\Users\thatg\Desktop\Creator\assets\icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("SUCCESS: icon.ico created")
except Exception as e:
    print(f"ERROR: {e}")
