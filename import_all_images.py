import os
import re
import db
import vector_db
import config

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(WORKSPACE_DIR, "garment_photos")

GARMENT_NAMING = {
    "Sharara & Suit Sets": "Kids Designer Sharara Set",
    "Girls Denim Sets": "Girls Denim Top & Cargo Pant Set",
    "Nightwear & Lounge Sets": "Girls Floral Lounge Set",
    "Kids Dresses": "Kids Party Frock Gown"
}

def infer_category_and_name(filename: str, product_counter: int) -> tuple[str, str]:
    """Infers product category and clean display name from image filename."""
    name_clean = os.path.splitext(filename)[0]
    
    lower = filename.lower()
    if any(k in lower for k in ["sharara", "suit", "lehenga", "plazo", "palazzo", "kurti", "joda"]):
        category = "Sharara & Suit Sets"
    elif any(k in lower for k in ["denim", "pant", "cargo", "jeans"]):
        category = "Girls Denim Sets"
    elif any(k in lower for k in ["nightwear", "lounge", "pyjama", "pajama", "track"]):
        category = "Nightwear & Lounge Sets"
    else:
        category = "Kids Dresses"

    # If filename is a raw date or default WhatsApp timestamp, assign a clean title
    if re.search(r'\b(2026|2025|2024|whatsapp|img|pic|photo|image|\d{8,})\b', name_clean, re.IGNORECASE) or len(name_clean) < 3:
        clean_title = f"{GARMENT_NAMING.get(category, 'Wholesale Garment Set')} #{product_counter}"
    else:
        clean_title = re.sub(r'[_\-]+', ' ', name_clean).title().strip()

    return category, clean_title

def import_bulk_photos():
    print("====================================================")
    print("   AT SELECTION - Bulk 2000+ Image Importer         ")
    print("====================================================")
    
    db.init_db()

    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR, exist_ok=True)

    image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    found_files = []

    for f in os.listdir(PHOTOS_DIR):
        if f.lower().endswith(image_extensions):
            found_files.append((f, os.path.join(PHOTOS_DIR, f), os.path.join("garment_photos", f)))

    for f in os.listdir(WORKSPACE_DIR):
        if f.lower().endswith(image_extensions) and not f.lower().startswith(('logo', 'qr')):
            found_files.append((f, os.path.join(WORKSPACE_DIR, f), f))

    if not found_files:
        print(f"[!] No image files found in {PHOTOS_DIR} or workspace.")
        return

    print(f"[*] Found {len(found_files)} product images. Processing import...")

    imported_count = 0
    updated_count = 0
    counter = 101

    for filename, abs_path, rel_path in found_files:
        category, name = infer_category_and_name(filename, counter)
        counter += 1
        db.add_category(category)

        existing = db.get_product_by_name_and_category(name, category)
        if existing:
            db.update_product(
                product_id=existing['id'],
                name=name,
                category=category,
                description=existing.get('description') or f"Wholesale {name} - High Quality Fabric & Stitching",
                price=existing.get('price') or 0.0,
                sizes=existing.get('sizes') or "24, 26, 28, 30, 32, 34",
                photo_file_id=rel_path
            )
            updated_count += 1
        else:
            db.add_product(
                name=name,
                category=category,
                description=f"Wholesale {name} - High Quality Garment Set",
                price=0.0,
                sizes="24, 26, 28, 30, 32, 34",
                photo_file_id=rel_path
            )
            imported_count += 1

    print(f"[+] Database updated: {imported_count} new products added, {updated_count} existing updated.")

    try:
        vector_db.rebuild_index()
        print("[+] Vector Database Index successfully rebuilt!")
    except Exception as e:
        print(f"[!] Vector Index rebuild note: {e}")

if __name__ == "__main__":
    import_bulk_photos()
