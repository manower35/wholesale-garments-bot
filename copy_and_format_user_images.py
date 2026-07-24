import os
import shutil
import sys
import db
import vector_db
from format_images_aspect_ratio import format_image_to_portrait

sys.stdout.reconfigure(encoding='utf-8')

UPLOAD_DIR = r"C:\Users\attar\.gemini\antigravity\brain\f04ad2b8-5ed2-419b-9c47-6f046c0f38d6\.user_uploaded"
BASE_DIR = r"c:\Users\attar\Desktop\Wholesale Readymade Garments"

# Map uploaded media files to garment items
items_mapping = [
    {
        "uploaded": "media__1784897056588.jpg",
        "target": "independence_tricolor_twin_gown.jpg",
        "prod_id": 199
    },
    {
        "uploaded": "media__1784897056699.jpg",
        "target": "independence_flag_bearer_gown.jpg",
        "prod_id": 200
    },
    {
        "uploaded": "media__1784897056713.jpg",
        "target": "independence_puff_sleeve_ball_gown.jpg",
        "prod_id": 201
    },
    {
        "uploaded": "media__1784897056722.jpg",
        "target": "independence_silk_dupatta_festive_gown.jpg",
        "prod_id": 202
    },
    {
        "uploaded": "media__1784897056731.jpg",
        "target": "independence_3tier_tricolor_dress.jpg",
        "prod_id": 203
    }
]

print("🇮🇳 Copying & Formatting 5 Uploaded Independence Day Garment Photos...")

for item in items_mapping:
    src_file = os.path.join(UPLOAD_DIR, item["uploaded"])
    dest_file = os.path.join(BASE_DIR, item["target"])
    
    if os.path.exists(src_file):
        shutil.copy(src_file, dest_file)
        print(f"  📸 Copied {item['uploaded']} -> {item['target']}")
        
        try:
            format_image_to_portrait(dest_file)
            print(f"  🎨 Formatted {item['target']} to 600x800 3:4 portrait view.")
        except Exception as e:
            print(f"  ⚠️ Aspect ratio format warning: {e}")
    else:
        print(f"  ❌ Source file missing: {src_file}")

    # Update SQLite database row
    with db.db_session() as conn:
        c = conn.cursor()
        c.execute("UPDATE products SET photo_file_id = ? WHERE id = ?", (item["target"], item["prod_id"]))
        conn.commit()
    print(f"  ✅ Updated Product #{item['prod_id']} in database.")

# Rebuild FAISS index
print("\n[*] Rebuilding FAISS vector index...")
vector_db.rebuild_index()

print("\n🎉 All 5 Independence Special photos are now fully active & formatted in catalog!")
