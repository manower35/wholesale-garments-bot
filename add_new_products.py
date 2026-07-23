import os
import shutil
import sqlite3
import openpyxl

workspace_dir = r"c:\Users\attar\Desktop\Wholesale Readymade Garments"
brain_dir = r"C:\Users\attar\.gemini\antigravity\brain\3d0a652e-4bdf-435f-96b8-cb5125ac77ed"
db_path = os.path.join(workspace_dir, "database.db")
excel_path = os.path.join(workspace_dir, "garment_catalog.xlsx")

new_products = [
    {
        "src_file": "media__1784378446689.jpg",
        "dest_name": "kids_smocked_puff_sleeve_gown.jpg",
        "name": "Smocked Puff Sleeve Satin Party Gown",
        "category": "Kids Dresses",
        "price": 690.0,
        "sizes": "24, 26, 28, 30, 32, 34",
        "description": "Elegant girls satin party gown featuring a smocked elasticated bodice, puff sleeves, flower corsage details on shoulder and waist belt. Colors: Deep Purple, Royal Blue, Hot Pink."
    },
    {
        "src_file": "media__1784378446697.jpg",
        "dest_name": "kids_red_rose_garland_satin_frock.jpg",
        "name": "Red Rose Garland Off-Shoulder Satin Frock",
        "category": "Kids Dresses",
        "price": 680.0,
        "sizes": "22, 24, 26, 28, 30, 32",
        "description": "Charming girls satin party frock decorated with a striking horizontal red rose bouquet across the chest and a pleated flared skirt. Colors: Off-White, Lavender, Pastel Yellow, Cream Gold."
    },
    {
        "src_file": "media__1784378446717.jpg",
        "dest_name": "kids_yellow_rose_garland_satin_frock.jpg",
        "name": "Cream Rose Corsage Off-Shoulder Satin Frock",
        "category": "Kids Dresses",
        "price": 690.0,
        "sizes": "24, 26, 28, 30, 32, 34",
        "description": "Gorgeous girls off-shoulder satin flared frock with prominent cream-yellow rose corsage bouquet across the neck. Colors: Navy Blue, Bright Pink, Deep Magenta."
    },
    {
        "src_file": "media__1784378446730.jpg",
        "dest_name": "kids_shimmer_floral_neck_ball_gown.jpg",
        "name": "Shimmer Satin Floral Neckline Ball Gown",
        "category": "Kids Dresses",
        "price": 720.0,
        "sizes": "24, 26, 28, 30, 32, 34",
        "description": "Premium shimmering satin floor-length ball gown featuring an intricate 3D floral appliqued neckline and matching waist bow. Colors: Mint Green, Pastel Pink, Shimmer Lavender."
    },
    {
        "src_file": "media__1784378446748.jpg",
        "dest_name": "kids_pleated_shoulder_flower_satin_gown.jpg",
        "name": "Pleated Satin Gown with Flower Sleeves & Bow",
        "category": "Kids Dresses",
        "price": 710.0,
        "sizes": "24, 26, 28, 30, 32, 34",
        "description": "Stylish girls box-pleated satin gown featuring 3D floral sleeve embellishments and a center waist bow accent. Colors: Crimson Red, Emerald Green, Warm Bronze."
    }
]

def main():
    print("=== Copying Images & Registering Products ===")
    
    # 1. Copy images
    for p in new_products:
        src = os.path.join(brain_dir, p["src_file"])
        dest = os.path.join(workspace_dir, p["dest_name"])
        if os.path.exists(src):
            shutil.copy(src, dest)
            print(f"[+] Copied {p['src_file']} -> {p['dest_name']}")
        else:
            print(f"[!] Source file missing: {src}")

    # 2. Database Insert
    import db
    db.init_db()
    
    for p in new_products:
        prod_id = db.add_product(
            name=p["name"],
            category=p["category"],
            description=p["description"],
            price=p["price"],
            sizes=p["sizes"],
            photo_file_id=p["dest_name"]
        )
        print(f"[+] Inserted Product ID #{prod_id}: {p['name']}")
        
    # 3. Excel Update
    if os.path.exists(excel_path):
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.active
        
        # append rows
        for p in new_products:
            sheet.append([
                p["category"],
                p["name"],
                p["price"],
                p["sizes"],
                p["description"],
                p["dest_name"]
            ])
        wb.save(excel_path)
        print("[+] Updated garment_catalog.xlsx with 5 new rows.")

    # 4. Vector DB update
    try:
        import vector_db
        vector_db.rebuild_index()
        print("[+] Rebuilt FAISS vector index.")
    except Exception as e:
        print(f"[-] Vector DB update note: {e}")

if __name__ == "__main__":
    main()
