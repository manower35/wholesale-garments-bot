import os
import logging
import openpyxl
import db
import vector_db

logger = logging.getLogger(__name__)

def import_excel_catalog(file_path: str) -> dict:
    """
    Parses a product catalog .xlsx spreadsheet and imports it to the database.
    Performs upsert logic (inserts if new, updates if existing by name + category).
    Also updates the FAISS vector database.
    
    Returns a dict summary of the import operation:
    {
        "success": bool,
        "inserted": int,
        "updated": int,
        "skipped": int,
        "errors": list[str]
    }
    """
    summary = {
        "success": False,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    
    if not os.path.exists(file_path):
        summary["errors"].append(f"File not found: {file_path}")
        return summary
        
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet = wb.active
    except Exception as e:
        summary["errors"].append(f"Failed to open/parse Excel file: {str(e)}")
        return summary
        
    # Read rows and search for the header row dynamically
    rows_iter = sheet.iter_rows(values_only=True)
    header_map = {}
    name_col = None
    category_col = None
    price_col = None

    for row in rows_iter:
        if not row or not any(val is not None for val in row):
            continue
        
        # Check if this row looks like the header row
        temp_map = {}
        for idx, cell_val in enumerate(row):
            if cell_val is not None:
                norm = str(cell_val).strip().lower().replace(" ", "_").replace("/", "_")
                temp_map[norm] = idx
        
        # Check if 'category' or 'garment_name' or 'name' is in temp_map
        found_name = any(k in temp_map for k in ["name", "garment_name", "product_name"])
        found_cat = "category" in temp_map
        
        if found_name and found_cat:
            header_map = temp_map
            for k in ["name", "garment_name", "product_name"]:
                if k in header_map:
                    name_col = header_map[k]
                    break
            category_col = header_map["category"]
            price_col = header_map.get("price")
            break

    if name_col is None or category_col is None:
        summary["errors"].append("Could not locate valid header row with 'Garment Name' / 'Category'.")
        wb.close()
        return summary
    
    # Optional columns
    desc_col = header_map.get("description")
    sizes_col = header_map.get("sizes") or header_map.get("available_sizes")
    image_col = header_map.get("image_filename") or header_map.get("image") or header_map.get("photo_file_id") or header_map.get("photo")

    # Read data rows
    row_num = 1 # Header was row 1
    for row in rows_iter:
        row_num += 1
        
        # Check if the row is entirely empty
        if not any(val is not None for val in row):
            continue
            
        # Ensure row list is long enough for mapped columns
        mapped_indices = [name_col, category_col, price_col, desc_col, sizes_col, image_col]
        max_idx = max(filter(lambda x: x is not None, mapped_indices))
        if len(row) <= max_idx:
            # Extend row with None values
            row = list(row) + [None] * (max_idx - len(row) + 1)
            
        name_val = row[name_col]
        category_val = row[category_col]
        price_val = row[price_col] if price_col is not None and price_col < len(row) else 0.0
        
        # If crucial values are missing, skip or log error
        if name_val is None or category_val is None:
            # Skip rows where name and category are completely empty, it might be padding
            if name_val is None and category_val is None:
                continue
            summary["errors"].append(f"Row {row_num}: Missing Name or Category. Skipped.")
            summary["skipped"] += 1
            continue
            
        name = str(name_val).strip()
        category = str(category_val).strip()
        
        if not name or not category:
            summary["errors"].append(f"Row {row_num}: Blank Name or Category. Skipped.")
            summary["skipped"] += 1
            continue
            
        # Parse and validate price
        try:
            if price_val is None or str(price_val).strip() == "":
                price = 0.0
            else:
                price_clean = str(price_val).replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
                price = float(price_clean)
                if price < 0:
                    raise ValueError("Price cannot be negative")
        except Exception as e:
            summary["errors"].append(f"Row {row_num} ('{name}'): Invalid price '{price_val}'. Error: {str(e)}. Skipped.")
            summary["skipped"] += 1
            continue
            
        # Parse optional fields
        description = str(row[desc_col]).strip() if desc_col is not None and row[desc_col] is not None else ""
        sizes = str(row[sizes_col]).strip() if sizes_col is not None and row[sizes_col] is not None else ""
        image_filename = str(row[image_col]).strip() if image_col is not None and row[image_col] is not None else ""
        
        # Ensure category exists in DB
        db.add_category(category)
        
        # Check if product already exists
        existing_prod = db.get_product_by_name_and_category(name, category)
        
        if existing_prod:
            # Update product
            success = db.update_product(
                product_id=existing_prod["id"],
                name=name,
                category=category,
                description=description,
                price=price,
                sizes=sizes,
                photo_file_id=image_filename or existing_prod["photo_file_id"]
            )
            if success:
                summary["updated"] += 1
                # Sync with vector DB
                try:
                    product_obj = db.get_product(existing_prod["id"])
                    if product_obj:
                        vector_db.add_product_to_vector_db(product_obj)
                except Exception as ex:
                    logger.error(f"Failed to sync updated product {name} to Vector DB: {ex}")
            else:
                summary["errors"].append(f"Row {row_num} ('{name}'): Failed to update database record.")
        else:
            # Insert product
            prod_id = db.add_product(
                name=name,
                category=category,
                description=description,
                price=price,
                sizes=sizes,
                photo_file_id=image_filename
            )
            if prod_id:
                summary["inserted"] += 1
                # Sync with vector DB
                try:
                    product_obj = db.get_product(prod_id)
                    if product_obj:
                        vector_db.add_product_to_vector_db(product_obj)
                except Exception as ex:
                    logger.error(f"Failed to sync new product {name} to Vector DB: {ex}")
            else:
                summary["errors"].append(f"Row {row_num} ('{name}'): Failed to insert database record.")

    wb.close()
    summary["success"] = True
    return summary
