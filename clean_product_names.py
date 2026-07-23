import os
import re
import db
import vector_db

def clean_and_rename_products():
    print("====================================================")
    print("   Cleaning & Formatting Product Display Names     ")
    print("====================================================")
    db.init_db()

    categories = db.get_categories()
    updated_count = 0

    garment_titles = {
        "Kids Dresses": [
            "Kids Smocked Party Frock",
            "Girls Tiered Net Ball Gown",
            "Kids Sequin Satin Party Frock",
            "Girls Rose Corsage Satin Dress",
            "Kids Shimmer Flared Party Gown",
            "Girls Off-Shoulder Velvet Frock",
            "Kids Floral Print Summer Dress",
            "Girls Pleated Shoulder Gown",
            "Kids Heavy Glitter Party Frock",
            "Girls Designer Layered Gown"
        ],
        "Sharara & Suit Sets": [
            "Kids Mirror Work Sharara Set",
            "Girls Embroidered Georgette Sharara",
            "Kids Cotton Floral Suit Set",
            "Girls Traditional Designer Sharara"
        ],
        "Girls Denim Sets": [
            "Girls Denim Top & Cargo Pant Set",
            "Kids Denim Jacket & Shorts Set",
            "Girls Trendy Casual Denim Set",
            "Kids Fashion Denim Overalls"
        ],
        "Nightwear & Lounge Sets": [
            "Girls Floral Printed Lounge Set",
            "Kids Cotton Tunic & Pajama Set",
            "Girls Soft Printed Nightwear Set"
        ]
    }

    title_index = {}

    for cat in categories:
        products = db.get_products_by_category(cat)
        default_titles = garment_titles.get(cat, ["Kids Wholesale Garment Set"])
        
        for p in products:
            name = p['name']
            # Check if name contains raw date string (e.g. "2026 07", "WhatsApp Image", "Img", "Pic")
            if re.search(r'\b(2026|2025|2024|whatsapp|img|pic|photo)\b', name, re.IGNORECASE) or len(name) < 3:
                idx = title_index.get(cat, 0)
                base_title = default_titles[idx % len(default_titles)]
                title_index[cat] = idx + 1
                
                # Append item ID to guarantee unique clean display name
                clean_name = f"{base_title} (Design #{p['id']})"

                db.update_product(
                    product_id=p['id'],
                    name=clean_name,
                    category=cat,
                    description=p.get('description') or f"Wholesale {base_title} set - High quality fabric & fine stitching.",
                    price=p.get('price') or 0.0,
                    sizes=p.get('sizes') or "24, 26, 28, 30, 32, 34",
                    photo_file_id=p.get('photo_file_id')
                )
                updated_count += 1
                print(f"[+] Updated ID #{p['id']}: '{name}' -> '{clean_name}'")

    print(f"\n[+] Total {updated_count} date-based names successfully updated!")

    # Rebuild Vector Index
    try:
        vector_db.rebuild_index()
        print("[+] Vector Database re-indexed!")
    except Exception as e:
        print(f"[!] Index rebuild note: {e}")

if __name__ == "__main__":
    clean_and_rename_products()
