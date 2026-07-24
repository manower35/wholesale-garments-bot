import os
import shutil
import sys
from PIL import Image
import db
import vector_db
from format_images_aspect_ratio import format_image_to_portrait

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"c:\Users\attar\Desktop\Wholesale Readymade Garments"
CATEGORY_NAME = "🇮🇳 Independence Special"

# Images provided by user in conversation context
input_images = [
    {
        "src": r"input_file_0.png",
        "filename": "independence_tricolor_twin_gown.jpg",
        "name": "🇮🇳 Independence Special Tricolor Twin Sister Gown Set",
        "sizes": "20, 22, 24, 26, 28, 30, 32",
        "description": "Exclusive ATS AT SELECTION Tricolor (Saffron, White, Green) puff sleeve gown with blue Ashoka Chakra brooch."
    },
    {
        "src": r"input_file_1.png",
        "filename": "independence_flag_bearer_gown.jpg",
        "name": "🇮🇳 15 August Flag Bearer Tricolor Flared Party Gown",
        "sizes": "24, 26, 28, 30, 32",
        "description": "Beautiful 15th August flag bearer tricolor flared dress with floral waist accent for school events & sales."
    },
    {
        "src": r"input_file_2.png",
        "filename": "independence_puff_sleeve_ball_gown.jpg",
        "name": "🇮🇳 Independence Day Royal Tricolor Puff-Sleeve Ball Gown",
        "sizes": "22, 24, 26, 28, 30, 32",
        "description": "Royal tricolor puff-sleeve flared ball gown with floral waist detailing."
    },
    {
        "src": r"input_file_3.png",
        "filename": "independence_silk_dupatta_festive_gown.jpg",
        "name": "🇮🇳 15th August Designer Silk Dupatta Style Festive Gown",
        "sizes": "24, 26, 28, 30, 32, 34",
        "description": "Designer silk dupatta drape style tricolor gown for 15th August Independence celebrations."
    },
    {
        "src": r"input_file_4.png",
        "filename": "independence_3tier_tricolor_dress.jpg",
        "name": "🇮🇳 Freedom Special 3-Tier Tricolor Designer Party Dress",
        "sizes": "20, 22, 24, 26, 28, 30",
        "description": "Unique 3-tier tricolor (saffron bodice, white middle, green flared skirt) party dress."
    }
]

print("🇮🇳 Adding 5 Real Independence Day Garment Photos to Catalog...")

# Ensure category exists in categories table
db.add_category(CATEGORY_NAME)

added_ids = []
for item in input_images:
    dest_path = os.path.join(BASE_DIR, item["filename"])
    src_path = item["src"]
    
    if os.path.exists(src_path):
        # Convert and copy image to dest_path
        img = Image.open(src_path).convert("RGB")
        img.save(dest_path, "JPEG", quality=95)
        print(f"  📸 Saved image: {item['filename']}")
        
        # Format to 3:4 portrait (600x800)
        try:
            format_image_to_portrait(dest_path)
            print(f"  🎨 Formatted {item['filename']} to 600x800 3:4 portrait view.")
        except Exception as e:
            print(f"  ⚠️ Formatting error: {e}")
            
    # Add product into SQLite
    prod_id = db.add_product(
        name=item["name"],
        category=CATEGORY_NAME,
        description=item["description"],
        price=0.0,
        sizes=item["sizes"],
        photo_file_id=item["filename"]
    )
    added_ids.append(prod_id)
    print(f"  ✅ Created Product #{prod_id}: '{item['name']}'")

# Rebuild FAISS index
print("\n[*] Rebuilding FAISS vector index...")
vector_db.rebuild_index()

print(f"\n🎉 Successfully added {len(added_ids)} real 15th August Special photos into '{CATEGORY_NAME}'!")
