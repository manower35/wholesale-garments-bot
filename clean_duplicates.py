import sys
import os
import db
import vector_db

sys.stdout.reconfigure(encoding='utf-8')

print("[*] Starting Catalog & Photo Deduplication...")

# 1. Fetch all products
categories = db.get_categories()
all_products = []
for c in categories:
    all_products.extend(db.get_products_by_category(c))

print(f"Total product rows before cleanup: {len(all_products)}")

# Track seen photos and seen (name + category) pairs
seen_photos = set()
seen_names = set()

deleted_count = 0

with db.db_session() as conn:
    cursor = conn.cursor()
    for p in all_products:
        photo = p.get("photo_file_id")
        name = p.get("name", "").strip().lower()
        category = p.get("category", "").strip().lower()
        name_cat_key = f"{category}::{name}"
        
        # Check if photo or name_cat is duplicate
        is_dup_photo = photo and (photo in seen_photos)
        is_dup_name = name_cat_key in seen_names
        
        if is_dup_photo or is_dup_name:
            cursor.execute("DELETE FROM products WHERE id = ?", (p["id"],))
            deleted_count += 1
            print(f"  ❌ Removed duplicate product #{p['id']} - '{p['name']}' (Photo: {photo})")
        else:
            if photo:
                seen_photos.add(photo)
            seen_names.add(name_cat_key)

print(f"\n[+] Successfully removed {deleted_count} duplicate product entries.")

# 2. Print clean category breakdown
print("\n=== CLEAN UNIQUE CATALOG BREAKDOWN ===")
total_unique = 0
for cat in categories:
    if cat.startswith("🛍"): continue
    prods = db.get_products_by_category(cat)
    count = len(prods)
    total_unique += count
    print(f"📁 {cat}: {count} unique designs")

print(f"\n✨ Total Unique Products in Catalog: {total_unique}")

# 3. Rebuild Vector Index
print("\n[*] Rebuilding FAISS vector index with unique products...")
vector_db.rebuild_index()
print("[+] Vector DB index rebuilt successfully.")
