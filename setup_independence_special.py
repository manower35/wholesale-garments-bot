import sys
import os
import db
import vector_db

sys.stdout.reconfigure(encoding='utf-8')

print("🇮🇳 Setting up '🇮🇳 Independence Special (15 August)' Category...")

CATEGORY_NAME = "🇮🇳 Independence Special"

# 1. Selected items for 15th August Special Sale
INDEPENDENCE_ITEMS = [
    {
        "name": "🇮🇳 Independence Special Tricolor Lehenga Choli Set",
        "category": CATEGORY_NAME,
        "description": "Special 15 August Tricolor Lehenga Choli with dupatta set for school & festive celebrations.",
        "sizes": "24, 26, 28, 30, 32, 34",
        "price": 0.0,
        "photo_file_id": "kids_colourful_lehenga_choli.jpg"
    },
    {
        "name": "🇮🇳 15 August Special Green & Gold Embroidered Gown",
        "category": CATEGORY_NAME,
        "description": "Green & Gold ethnic embroidered flared gown for 15th August celebrations.",
        "sizes": "24, 26, 28, 30, 32",
        "price": 0.0,
        "photo_file_id": "kids_green_gold_lehenga_gown.jpg"
    },
    {
        "name": "🇮🇳 Independence Day Special Royal Gold Lehenga Choli",
        "category": CATEGORY_NAME,
        "description": "Royal Gold embroidered festive lehenga choli set.",
        "sizes": "22, 24, 26, 28, 30, 32",
        "price": 0.0,
        "photo_file_id": "kids_gold_lehenga_choli.jpg"
    },
    {
        "name": "🇮🇳 15th August Mirror Work Ethnic Sharara Set",
        "category": CATEGORY_NAME,
        "description": "Traditional mirror embroidered Sharara & Dupatta set for 15 August sales.",
        "sizes": "24, 26, 28, 30, 32, 34",
        "price": 0.0,
        "photo_file_id": "kids_mirror_sharara_set.jpg"
    },
    {
        "name": "🇮🇳 Patriotic White & Saffron Rose Satin Frock",
        "category": CATEGORY_NAME,
        "description": "Elegant white satin frock with yellow/saffron rose garland details.",
        "sizes": "20, 22, 24, 26, 28, 30",
        "price": 0.0,
        "photo_file_id": "kids_yellow_rose_garland_satin_frock.jpg"
    },
    {
        "name": "🇮🇳 15 August Designer Off-White Plazo Suit",
        "category": CATEGORY_NAME,
        "description": "Designer off-white embroidered Plazo & Dupatta set.",
        "sizes": "24, 26, 28, 30, 32",
        "price": 0.0,
        "photo_file_id": "kids_plazo_252.jpg"
    },
    {
        "name": "🇮🇳 Independence Special Royal Silk Sharara Suit",
        "category": CATEGORY_NAME,
        "description": "Royal ethnic silk Sharara suit for Independence Day functions.",
        "sizes": "24, 26, 28, 30, 32, 34",
        "price": 0.0,
        "photo_file_id": "unique_girls_sharara_suit_1784383419273.jpg"
    },
    {
        "name": "🇮🇳 Freedom Special Shimmer Floral Ball Gown",
        "category": CATEGORY_NAME,
        "description": "Shimmer floral neck ball gown for Independence Day school events.",
        "sizes": "22, 24, 26, 28, 30",
        "price": 0.0,
        "photo_file_id": "kids_shimmer_floral_neck_ball_gown.jpg"
    }
]

added_ids = []
for item in INDEPENDENCE_ITEMS:
    prod_id = db.add_product(
        name=item["name"],
        category=item["category"],
        description=item["description"],
        price=item["price"],
        sizes=item["sizes"],
        photo_file_id=item["photo_file_id"]
    )
    added_ids.append(prod_id)
    print(f"  🇮🇳 Added #{prod_id} - '{item['name']}'")

# Format photos to 3:4 portrait view
from format_images_aspect_ratio import format_image_to_portrait
for item in INDEPENDENCE_ITEMS:
    photo_file = item["photo_file_id"]
    if os.path.exists(photo_file):
        format_image_to_portrait(photo_file)
    elif os.path.exists(os.path.join("garment_photos", photo_file)):
        format_image_to_portrait(os.path.join("garment_photos", photo_file))

# Rebuild FAISS index
print("\n[*] Rebuilding FAISS vector index...")
vector_db.rebuild_index()

print(f"\n✅ Successfully created '{CATEGORY_NAME}' with {len(added_ids)} special designs!")
