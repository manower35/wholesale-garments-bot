import os
import sys
from PIL import Image, ImageOps
import db

sys.stdout.reconfigure(encoding='utf-8')

print("🎨 Starting 3:4 Vertical Portrait Image Formatting for WhatsApp Mobile Cards...")

# Target Dimensions: 600 width x 800 height (Vertical 3:4 ratio)
TARGET_WIDTH = 600
TARGET_HEIGHT = 800
TARGET_SIZE = (TARGET_WIDTH, TARGET_HEIGHT)
BACKGROUND_COLOR = (255, 255, 255) # Pure White studio background

def format_image_to_portrait(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            
            # Create a 600x800 white canvas
            canvas = Image.new("RGB", TARGET_SIZE, BACKGROUND_COLOR)
            
            # Resize image to fit within 600x800 canvas while preserving aspect ratio
            img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
            
            # Center the image on the canvas
            offset_x = (TARGET_WIDTH - img.width) // 2
            offset_y = (TARGET_HEIGHT - img.height) // 2
            canvas.paste(img, (offset_x, offset_y))
            
            # Save back to file
            canvas.save(file_path, "JPEG", quality=92, optimize=True)
            return True
    except Exception as e:
        print(f"  [!] Error processing {file_path}: {e}")
        return False

# Fetch all products from DB
categories = db.get_categories()
all_products = []
for c in categories:
    all_products.extend(db.get_products_by_category(c))

processed_count = 0
failed_count = 0

for p in all_products:
    photo_file = p.get("photo_file_id")
    if not photo_file:
        continue
        
    # Check paths
    target_path = None
    if os.path.exists(photo_file):
        target_path = photo_file
    elif os.path.exists(os.path.join("garment_photos", photo_file)):
        target_path = os.path.join("garment_photos", photo_file)
        
    if target_path:
        success = format_image_to_portrait(target_path)
        if success:
            processed_count += 1
        else:
            failed_count += 1

print(f"\n✨ Image Formatting Complete!")
print(f"📸 Successfully formatted: {processed_count} garment photos to 600x800 (3:4 Vertical Portrait)")
if failed_count > 0:
    print(f"⚠️ Failed: {failed_count} photos")
