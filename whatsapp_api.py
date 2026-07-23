import json
import logging
import re
import os
import asyncio
import datetime
import difflib
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import config
import db
import ai_agent
import vector_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("whatsapp_api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_absolute_photo_path(photo_file_id: str) -> str | None:
    if not photo_file_id:
        return None
    if os.path.isabs(photo_file_id) and os.path.exists(photo_file_id):
        return photo_file_id
    abs_path = os.path.join(BASE_DIR, photo_file_id)
    if os.path.exists(abs_path):
        return abs_path
    return None

def format_markdown_for_whatsapp(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'_\1_', text)
    return text

def phone_to_user_id(whatsapp_from: str) -> int:
    try:
        digits = re.sub(r'\D', '', str(whatsapp_from).split('@')[0])
        if not digits:
            return 999999999
        return int(digits[-9:])
    except Exception:
        return 999999999

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class WhatsAppRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def _send_json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self._send_json_response(200, {"status": "online"})
        else:
            self._send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/api/whatsapp/message":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                sender_jid = payload.get("from", "")
                sender_name = payload.get("senderName", "Customer")
                body = payload.get("body", "").strip()
                quoted_body = payload.get("quotedBody", "").strip()
                has_media = payload.get("hasMedia", False)
                media_data = payload.get("mediaData")
                media_mime = payload.get("mediaMime")

                if not sender_jid:
                    self._send_json_response(400, {"error": "Missing 'from'"})
                    return

                user_id = phone_to_user_id(sender_jid)
                result = process_whatsapp_user_message(user_id, sender_name, body, quoted_body, has_media, sender_jid, media_data, media_mime)
                formatted_reply = format_markdown_for_whatsapp(result.get("reply", ""))
                resp = {"status": "success", "reply": formatted_reply}
                if result.get("mediaPath") and os.path.exists(result["mediaPath"]):
                    resp["mediaPath"] = result["mediaPath"]
                if result.get("gallery"):
                    resp["gallery"] = result["gallery"]
                self._send_json_response(200, resp)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                self._send_json_response(500, {"reply": "🙏 Kuch problem hua. Dobara try karo."})
        else:
            self._send_json_response(404, {"error": "Not found"})

def find_matching_product_photo(user_message: str) -> str | None:
    if not user_message or user_message.lower().strip() in ["hi", "hello", "hey", "/start", "start", "menu", "catalog"]:
        return get_absolute_photo_path("logo.jpg")
    try:
        db_matched = db.search_products(user_message)
        if db_matched:
            for item in db_matched:
                if item.get("photo_file_id"):
                    photo = get_absolute_photo_path(item["photo_file_id"])
                    if photo:
                        return photo
    except:
        pass
    return None

USER_PAGINATION_STATE = {}

def generate_executive_stock_report() -> str:
    now = datetime.datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%I:%M %p")

    categories = db.get_categories()
    summary_lines = []
    total_count = 0

    icon_map = {
        "Frock & Dresses": "👗",
        "Plazo & Sharara": "👘",
        "Western Wear": "👚",
        "Crop Top & Choli": "💃",
        "Nightwear & Lounge": "🌙"
    }

    for c in categories:
        if c and not c.startswith("🛍"):
            prods = db.get_products_by_category(c)
            count = len(prods)
            if count > 0:
                icon = icon_map.get(c, "📁")
                summary_lines.append(f"  {icon} *{c}*: *{count} items*")
                total_count += count

    inquiries_count = len(db.get_inquiries())

    report_text = (
        f"🏬 *{config.BUSINESS_NAME}*\n"
        f"_{config.BUSINESS_SUBTITLE}_\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *OFFICIAL LIVE STOCK & INVENTORY REPORT*\n"
        f"📅 *Date:* {date_str}  |  🕒 *Time:* {time_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *Active Catalog Breakdown:*\n" +
        "\n".join(summary_lines) + f"\n\n"
        f"✨ *Total Active Stock Designs*: *{total_count}*\n"
        f"📑 *Total Orders Inquiries Received*: *{inquiries_count}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Owner:* {config.OWNER_NAME}\n"
        f"📞 *Contact:* +91 {config.OWNER_PHONES[0]}\n"
        f"📍 *Shop:* {config.BUSINESS_ADDRESS}"
    )
    return report_text

def build_gallery_for_page(products: list, remaining_count: int = 0) -> list:
    gallery = []
    seen_media = set()
    for p in products:
        photo = get_absolute_photo_path(p.get("photo_file_id"))
        if photo and photo not in seen_media and "logo.jpg" not in photo:
            seen_media.add(photo)
            sizes = p.get("sizes") if p.get("sizes") else "All sizes"
            caption = (
                f"👗 *{p['name']}*\n"
                f"📐 Size: {sizes}\n"
                f"🔢 No: *{p['id']}*\n\n"
                f"👉 Rate/Quotation ke liye is photo par *Swipe-Reply* karo!"
            )
            gallery.append({"caption": caption, "mediaPath": photo})

    if gallery and remaining_count > 0:
        gallery[-1]["caption"] += f"\n\n➡️ *{remaining_count} MORE ITEMS AVAILABLE!*\n📲 Reply *NEXT* to view next {min(remaining_count, 10)} photos!"
    elif gallery:
        gallery[-1]["caption"] += "\n\n✅ *End of catalog for this category!*"

    return gallery

def extract_product_id_from_text(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r'(?:no|id|#)\s*:?\s*#?(\d{1,5})', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match_num = re.search(r'\b(\d{1,5})\b', text)
    if match_num:
        return int(match_num.group(1))
    return None

def match_category_by_alias(text_lower: str) -> str | None:
    if not text_lower:
        return None
        
    categories = db.get_categories()
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', text_lower).lower().strip()
    
    # 1. Exact or Substring match on category names
    for cat in categories:
        if cat and not cat.startswith("🛍"):
            clean_cat = re.sub(r'[^a-zA-Z0-9\s]', '', cat).lower().strip()
            if clean_cat and (clean_cat == clean_text or clean_text in clean_cat or clean_cat in clean_text):
                return cat

    alias_map = {
        "🇮🇳 Independence Special": [
            "independence", "independene", "indepandence", "independant", "indepent",
            "15 august", "15august", "15augst", "15agust", "15aug", "15 aug",
            "august", "augst", "agust", "tiranga", "freedom", "flag",
            "independence special", "august special", "patriotic", "15th august"
        ],
        "Frock & Dresses": [
            "frock", "frocks", "froc", "froks", "frok", "frocx",
            "dress", "dresses", "dres", "gown", "gowns", "gwon", "gwons",
            "garment", "garments", "skirt", "ball gown"
        ],
        "Western Wear": [
            "western", "wester", "westeen", "western wear", "denim", "denims",
            "jean", "jeans", "pants", "pant", "trousers", "tunic", "shorts"
        ],
        "Plazo & Sharara": [
            "plazo", "palazzo", "palzo", "plazos", "sharara", "shararas", "sarara", "sararas",
            "suit", "suits", "anarkali", "kurti", "dupatta"
        ],
        "Crop Top & Choli": [
            "crop top", "croptop", "crop", "choli", "crop top choli",
            "lehenga", "lehnga", "lehanga", "lehenga choli", "ghagra"
        ],
        "Nightwear & Lounge": [
            "nightwear", "nigtwear", "night wear", "night", "lounge", "loungewear",
            "sleepwear", "pyjama", "pajama", "pyjamas", "pajamas", "nighty"
        ]
    }

    # 2. Substring match on explicit alias map
    for cat_name, keywords in alias_map.items():
        for kw in keywords:
            if kw in clean_text or clean_text in kw:
                if cat_name in categories:
                    return cat_name

    # 3. Fuzzy matching (difflib) for spelling typos
    all_keywords = []
    kw_to_cat = {}
    for cat_name, keywords in alias_map.items():
        if cat_name in categories:
            for kw in keywords:
                all_keywords.append(kw)
                kw_to_cat[kw] = cat_name
                
    close_matches = difflib.get_close_matches(clean_text, all_keywords, n=1, cutoff=0.65)
    if close_matches:
        matched_kw = close_matches[0]
        return kw_to_cat[matched_kw]

    return None

def is_admin_whatsapp(sender_jid: str) -> bool:
    if not sender_jid:
        return True
    if str(sender_jid).lower() in ["self", "me", "owner", "admin"]:
        return True
    clean_num = re.sub(r'\D', '', str(sender_jid).split('@')[0])
    if not clean_num:
        return True
    for owner_phone in config.OWNER_PHONES:
        clean_owner = re.sub(r'\D', '', str(owner_phone))
        if clean_num and clean_owner and (clean_num.endswith(clean_owner) or clean_owner.endswith(clean_num)):
            return True
    user_id = phone_to_user_id(sender_jid)
    return db.is_admin(user_id)

RECENT_USER_UPLOADS = {}

def process_whatsapp_user_message(user_id: int, sender_name: str, body: str, quoted_body: str = "", has_media: bool = False, sender_jid: str = "", media_data: str = None, media_mime: str = None) -> dict:
    text_lower = (body or "").lower().strip()

    # Cache incoming standalone photo uploads for 5 minutes
    if media_data:
        import base64
        try:
            ext = ".jpg"
            if media_mime and "png" in media_mime: ext = ".png"
            elif media_mime and "webp" in media_mime: ext = ".webp"
            
            timestamp_id = int(datetime.datetime.now().timestamp() * 1000)
            file_name = f"unique_upload_{timestamp_id}{ext}"
            target_path = os.path.join(BASE_DIR, file_name)
            
            img_bytes = base64.b64decode(media_data)
            with open(target_path, "wb") as f:
                f.write(img_bytes)
            
            try:
                from format_images_aspect_ratio import format_image_to_portrait
                format_image_to_portrait(target_path)
            except Exception:
                pass
                
            RECENT_USER_UPLOADS[user_id] = {
                "photo_file_id": file_name,
                "timestamp": datetime.datetime.now()
            }
            logger.info(f"Cached recent photo upload for user #{user_id}: {file_name}")
        except Exception as err:
            logger.error(f"Error caching media upload: {err}")

    # ==========================================
    # 0. 🛠️ MOBILE ADMIN COMMANDS (#delete and #add)
    # ==========================================
    is_delete_cmd = (
        text_lower.startswith("#delete") or
        text_lower.startswith("/delete") or
        text_lower == "delete" or
        text_lower.startswith("delete ")
    )
    if is_delete_cmd:
        if not is_admin_whatsapp(sender_jid):
            return {"reply": "⚠️ *Admin Security Barrier:* Only authorized shop owners/admins can delete items from catalog."}
        
        combined_text = f"{quoted_body} {body}"
        prod_id = extract_product_id_from_text(combined_text)
        if not prod_id:
            return {"reply": "⚠️ *Product ID missing for deletion!*\n\n👉 *Usage:* Type `#delete 141` or *Swipe-Reply* to any product photo card with `#delete`."}
        
        product = db.get_product(prod_id)
        if not product:
            return {"reply": f"❌ *Product ID #{prod_id} not found in catalog!*"}
        
        # Delete from DB
        db.delete_product(prod_id)
        
        # Delete associated photo file from disk if present
        if product.get("photo_file_id"):
            photo_path = get_absolute_photo_path(product["photo_file_id"])
            if photo_path and os.path.exists(photo_path) and "logo.jpg" not in photo_path:
                try:
                    os.remove(photo_path)
                except Exception as e:
                    logger.warning(f"Could not remove image file {photo_path}: {e}")
                    
        # Update vector DB index
        vector_db.delete_product_from_vector_db(prod_id)
        
        return {
            "reply": (
                f"🗑️ *PRODUCT DELETED FROM CATALOG!*\n\n"
                f"🆔 Product ID: *#{prod_id}*\n"
                f"👗 Garment Name: *{product['name']}*\n"
                f"📁 Category: *{product['category']}*\n"
                f"📐 Sizes: *{product.get('sizes', 'Standard')}*"
            )
        }

    is_add_cmd = (
        text_lower.startswith("#add") or
        text_lower.startswith("/add") or
        text_lower.startswith("add ")
    )
    if is_add_cmd:
        if not is_admin_whatsapp(sender_jid):
            return {"reply": "⚠️ *Admin Security Barrier:* Only authorized shop owners/admins can add items to catalog."}
        
        photo_filename = ""
        cached = RECENT_USER_UPLOADS.get(user_id)
        if cached:
            elapsed = (datetime.datetime.now() - cached["timestamp"]).total_seconds()
            if elapsed <= 300: # 5 minutes
                photo_filename = cached["photo_file_id"]
                RECENT_USER_UPLOADS.pop(user_id, None)

        if not media_data and not photo_filename:
            return {
                "reply": (
                    "⚠️ *Photo Required to Add Product!*\n\n"
                    "📷 Please **ATTACH A PHOTO** from your phone gallery first, and write in the photo caption:\n"
                    "`#add 15 August | 24-34`\n\n"
                    "👉 *Step 1:* Tap Paperclip 📎 / Camera in WhatsApp\n"
                    "👉 *Step 2:* Select garment photo from gallery\n"
                    "👉 *Step 3:* Type `#add 15 August | 24-34` in caption & Send!"
                )
            }
        
        raw_cmd = re.sub(r'^(?:#add|/add|add)\s*', '', body, flags=re.IGNORECASE).strip()
        
        parts = [p.strip() for p in raw_cmd.split("|") if p.strip()]
        cat_input = "Frock & Dresses"
        sizes_input = "24, 26, 28, 30, 32, 34"
        name_input = ""
        
        if len(parts) == 1:
            cat_input = parts[0]
        elif len(parts) == 2:
            cat_input = parts[0]
            if re.search(r'\d', parts[1]) or "size" in parts[1].lower():
                sizes_input = parts[1]
            else:
                name_input = parts[1]
        elif len(parts) >= 3:
            cat_input = parts[0]
            name_input = parts[1]
            sizes_input = parts[2]
            
        matched_category = match_category_by_alias(cat_input) or cat_input
        if not name_input:
            clean_cat_title = matched_category.replace("🇮🇳", "").strip()
            name_input = f"{clean_cat_title} Design"
            
        desc_input = f"Wholesale {name_input} available at AT SELECTION."
        
        if media_data and not photo_filename:
            import base64
            try:
                ext = ".jpg"
                if media_mime and "png" in media_mime: ext = ".png"
                elif media_mime and "webp" in media_mime: ext = ".webp"
                
                timestamp_id = int(datetime.datetime.now().timestamp() * 1000)
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name_input.lower().replace(' ', '_'))[:20]
                file_name = f"unique_{clean_name}_{timestamp_id}{ext}"
                target_path = os.path.join(BASE_DIR, file_name)
                
                img_bytes = base64.b64decode(media_data)
                with open(target_path, "wb") as f:
                    f.write(img_bytes)
                photo_filename = file_name
                logger.info(f"Successfully saved uploaded product photo: {target_path}")
                
                try:
                    from format_images_aspect_ratio import format_image_to_portrait
                    format_image_to_portrait(target_path)
                except Exception as fmt_err:
                    logger.warning(f"Aspect ratio format warning: {fmt_err}")
            except Exception as e:
                logger.error(f"Failed to save uploaded photo: {e}", exc_info=True)
                
        # Insert into SQLite
        new_prod_id = db.add_product(
            name=name_input,
            category=matched_category,
            description=desc_input,
            price=0.0,
            sizes=sizes_input,
            photo_file_id=photo_filename
        )
        
        # Update vector DB
        new_prod = db.get_product(new_prod_id)
        if new_prod:
            vector_db.add_product_to_vector_db(new_prod)
            
        return {
            "reply": (
                f"✅ *PRODUCT ADDED TO CATALOG!*\n\n"
                f"🆔 Product ID: *#{new_prod_id}*\n"
                f"📁 Category: *{matched_category}*\n"
                f"📐 Sizes: *{sizes_input}*\n"
                f"📷 Photo: *{'Saved (3:4 Portrait)' if photo_filename else 'No image attached'}*"
            )
        }

    # Detect if message is a Product Card / Swipe-Reply / Forwarded Image Card
    is_product_card_msg = (
        bool(quoted_body) or
        body.startswith("👗") or
        "swipe-reply" in text_lower or
        "rate/quotation" in text_lower or
        ("size:" in text_lower and ("no:" in text_lower or "#" in text_lower))
    )

    # ==========================================
    # 1. 📸 SWIPE-REPLY OR PRODUCT CARD SENT BY CUSTOMER
    # ==========================================
    if is_product_card_msg:
        combined_text = f"{quoted_body} {body}"
        prod_id = extract_product_id_from_text(combined_text)

        if prod_id:
            product = db.get_product(prod_id)
            if product:
                items_list = [{
                    "product_id": product['id'],
                    "name": product['name'],
                    "category": product['category'],
                    "sizes": product.get('sizes', 'All'),
                    "quantity": 1
                }]
                db.save_inquiry(user_id, sender_name, str(user_id), items_list)
                reply = (
                    f"✅ *Received for Quotation!*\n\n"
                    f"👗 Item: *{product['name']}* (No. {prod_id})\n"
                    f"Staff will contact you shortly with rate & stock details. 📞"
                )
                return {"reply": reply}

        # Fallback if product ID couldn't be extracted
        items_list = [{"type": "quoted_photo", "name": f"Customer Quoted Photo Card", "quantity": 1}]
        db.save_inquiry(user_id, sender_name, str(user_id), items_list)
        return {
            "reply": (
                f"✅ *Received for Quotation!*\n"
                f"Staff will contact you shortly with rate & stock details. 📞"
            )
        }

    # ==========================================
    # 2. 📸 DIRECT PHOTO SENT BY CUSTOMER
    # ==========================================
    if has_media and not text_lower:
        items_list = [{"type": "custom_photo", "name": "Customer Sent Direct Photo", "quantity": 1}]
        inquiry_id = db.save_inquiry(user_id, sender_name, str(user_id), items_list)
        return {
            "reply": (
                f"✅ *Received for Quotation!*\n"
                f"Staff will contact you shortly with rate & stock details. 📞"
            )
        }

    # ==========================================
    # 3. 🛍️ EXPLICIT BUY / SEND COMMAND (e.g. "buy 128", "send 128")
    # ==========================================
    buy_match = re.match(r'^(?:buy|send|order|quote)\s+#?(\d{1,5})$', text_lower)
    if buy_match:
        prod_id = int(buy_match.group(1))
        product = db.get_product(prod_id)
        if product:
            items_list = [{
                "product_id": product['id'],
                "name": product['name'],
                "category": product['category'],
                "sizes": product.get('sizes', 'All'),
                "quantity": 1
            }]
            db.save_inquiry(user_id, sender_name, str(user_id), items_list)
            return {
                "reply": (
                    f"✅ *Received for Quotation!*\n\n"
                    f"👗 Item: *{product['name']}* (No. {prod_id})\n"
                    f"Staff will contact you shortly with rate & stock details. 📞"
                )
            }

    # ==========================================
    # 4. RESET / START / MENU / HI
    # ==========================================
    if text_lower in ["/reset", "reset"]:
        db.clear_chat_history(user_id)
        USER_PAGINATION_STATE.pop(user_id, None)
        return {"reply": "🧹 *Chat reset!*"}

    if text_lower in ["!stock", "/stock", "stock", "stock summary", "stock report", "!report", "/report", "report"]:
        return {"reply": generate_executive_stock_report()}

    # GREETINGS & MAIN MENU
    clean_greeting = re.sub(r'[^a-zA-Z0-9]', '', text_lower)
    if clean_greeting in ["start", "menu", "catalog", "hi", "hello", "hey", "welcome", "hie", "hola", "salam", "namaste", "atselection"] or text_lower in ["/start", "start", "/menu", "menu", "/catalog", "catalog", "hi", "hello", "hey"]:
        categories = db.get_categories()
        # Ensure Independence Special comes first
        categories = sorted(categories, key=lambda c: 0 if "independence" in c.lower() or "15" in c.lower() else 1)
        cat_list = []
        for c in categories:
            if c and not c.startswith("🛍"):
                count = len(db.get_products_by_category(c))
                if count > 0:
                    cat_list.append(f"👉 *{c}* ({count} items)")
                elif "independence" in c.lower() or "15" in c.lower():
                    cat_list.append(f"👉 *{c}* (0 items - Uploading soon!)")
        cat_text = "\n".join(cat_list)
        media_path = get_absolute_photo_path("logo.jpg")
        reply = (
            f"🎉 *15 AUGUST INDEPENDENCE DAY SPECIAL SALE IS LIVE!* 🇮🇳\n\n"
            f"🙏 *{config.BUSINESS_NAME}*\n"
            f"_{config.BUSINESS_SUBTITLE}_\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Shop Address:* {config.BUSINESS_ADDRESS}\n"
            f"👤 *Owner:* {config.OWNER_NAME}\n"
            f"📞 *Call / WhatsApp:* +91 {config.OWNER_PHONES[0]}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛍️ *WHOLESALE GARMENTS CATALOG:*\n\n"
            f"{cat_text}\n\n"
            f"📲 *Reply with any Category Name* (e.g. *15 August*, *Frock*, *Plazo*) to view product photos!\n"
            f"👉 *Swipe-Reply* to any photo card for instant wholesale rate & stock quotation!"
        )
        return {"reply": reply, "mediaPath": media_path}

    # CONTACT
    if text_lower in ["contact", "info", "address", "phone"]:
        return {"reply": (
            f"📞 *{config.BUSINESS_NAME}*\n\n"
            f"📍 {config.BUSINESS_ADDRESS}\n"
            f"📞 {config.OWNER_PHONES[0]}\n"
            f"📞 {config.OWNER_PHONES[1]}, {config.OWNER_PHONES[2]}"
        ), "mediaPath": get_absolute_photo_path("logo.jpg")}

    # ADMIN & STAFF INQUIRIES
    if text_lower in ["admin", "admin panel"]:
        return {"reply": (
            f"⚙️ *Admin & Staff Panel*\n\n"
            f"📥 *inquiries* / *orders* - Customer photo requests dekho\n"
            f"📦 *stock* - Stock count dekho"
        )}

    if text_lower in ["inquiries", "orders", "inquiry", "all orders"]:
        try:
            inquiries = db.get_inquiries(limit=15)
            if not inquiries:
                return {"reply": "📥 *No inquiries yet!*"}
            
            text = f"📥 *Customer Photo Inquiries ({len(inquiries)} Recent):*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for inq in inquiries:
                cust_name = inq.get('customer_name', 'Customer')
                cust_phone = inq.get('customer_phone', '')
                created = str(inq.get('created_at', ''))[:16]
                items = inq.get('items', [])
                text += f"📋 *Inquiry #{inq['id']}* | 👤 {cust_name}\n"
                text += f"🕒 {created} | 📱 {cust_phone}\n"
                text += "🛍️ Items:\n"
                for it in items[:5]:
                    if it.get("type") in ["custom_photo", "quoted_photo"]:
                        text += f"   • 📸 {it.get('name', 'Photo Inquiry')}\n"
                    else:
                        text += f"   • {it.get('name', 'Product')} (No. {it.get('product_id', '?')})\n"
                text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            return {"reply": text}
        except Exception as e:
            return {"reply": f"⚠️ Error: {e}"}

    # NEXT PAGE
    is_next_command = (
        text_lower in ["next", "more", "aur", "next page", "aur dikhao", "n", "p2", "p3", "page 2", "page 3"] or
        bool(re.match(r'^(?:next|page|p)\s*\d*$', text_lower))
    )
    if is_next_command:
        state = USER_PAGINATION_STATE.get(user_id)
        if not state:
            state = {"category": "Frock & Dresses", "page": 1}

        cat = state.get("category", "Frock & Dresses")
        current_page = state.get("page", 1) + 1
        products = db.get_products_by_category(cat)
        page_size = 10
        start_idx = (current_page - 1) * page_size
        page_items = products[start_idx:start_idx + page_size]
        if page_items:
            USER_PAGINATION_STATE[user_id] = {"category": cat, "page": current_page}
            remaining = len(products) - (start_idx + len(page_items))
            gallery = build_gallery_for_page(page_items, remaining)
            more = f"\n➡️ *{remaining} more items available!* Reply *NEXT* for remaining photos." if remaining > 0 else "\n✅ *End of catalog for this category!*"
            reply = (
                f"📁 *{cat} (Page {current_page}/{total_pages})*\n"
                f"📷 Sending {len(gallery)} product photos...{more}"
            )
            return {"reply": reply, "gallery": gallery}
        else:
            return {"reply": f"✅ *All {len(products)} items in '{cat}' have been shown!*\nType another category name like *Plazo*, *Western*, *Crop Top*, or *Nightwear* to explore more."}

    # ==========================================
    # 5. 📁 CATEGORY SEARCH (Nightwear, Nighwear, Frock, Sharara, Denim, etc.)
    # ==========================================
    matched_cat = match_category_by_alias(text_lower)
    if matched_cat:
        products = db.get_products_by_category(matched_cat)
        if products:
            page_size = 10
            page_items = products[:page_size]
            USER_PAGINATION_STATE[user_id] = {"category": matched_cat, "page": 1}
            total_pages = (len(products) + page_size - 1) // page_size
            remaining = len(products) - len(page_items)
            gallery = build_gallery_for_page(page_items, remaining)
            more = f"\n➡️ *{remaining} remaining items available!* Reply *NEXT* to see more photos." if remaining > 0 else "\n✅ *All photos shown for this category!*"
            reply = (
                f"📁 *{matched_cat} ({len(products)} total items)*\n"
                f"📷 Sending {len(gallery)} product photos...{more}"
            )
            return {"reply": reply, "gallery": gallery}
        else:
            return {"reply": f"📁 *{matched_cat}*\n\n✨ *Category is currently empty and ready for your 15 August photo uploads!*\n\n📷 Send a product photo with caption:\n`#add {matched_cat} | Garment Name | Sizes` to add new designs directly from your phone!"}

    # ==========================================
    # 6. 🔍 PRODUCT SEARCH BY NAME/KEYWORD (Frock, Gown, Yellow, Velvet, Rose, etc.)
    # ==========================================
    search_results = db.search_products(text_lower)
    if search_results:
        page_items = search_results[:10]
        gallery = build_gallery_for_page(page_items)
        reply = (
            f"📁 *Matching Products for '{body}' ({len(search_results)} found)*\n"
            f"📷 Sending {len(gallery)} product photos..."
        )
        return {"reply": reply, "gallery": gallery}

    # ==========================================
    # 7. STOCK
    # ==========================================
    if text_lower in ["/stock", "stock", "stock summary", "stock report"]:
        return {"reply": generate_executive_stock_report()}

    # ==========================================
    # 8. AI FALLBACK QUERY
    # ==========================================
    media_path = find_matching_product_photo(body)
    try:
        response = asyncio.run(ai_agent.ask_ai_agent(user_id, body))
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        response = None
    if response:
        return {"reply": response, "mediaPath": media_path}
    else:
        return {"reply": f"🙏 Shukriya! {config.BUSINESS_NAME} mein aapka swagat hai.\n📞 Call: {config.OWNER_PHONES[0]}", "mediaPath": media_path}

def run_server(port=None):
    if port is None:
        port = config.WHATSAPP_PORT
    db.init_db()
    httpd = ThreadedHTTPServer(('', port), WhatsAppRequestHandler)
    print("====================================================")
    print(f"  {config.BUSINESS_NAME} - WhatsApp AI Server")
    print(f"  http://localhost:{port}")
    print("====================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
