from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
import config

# Admin Main Menu Keyboards
def get_admin_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["📁 Manage Categories", "👗 Manage Products"],
        ["📋 View Inquiries", "📊 AI Report"],
        ["👥 Add Admin ID", "🔙 Exit Admin Menu"]
    ], resize_keyboard=True)

async def send_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the admin main menu."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ Access denied. Only admins can access this area.")
        return

    # Clear any admin states
    context.user_data["admin_state"] = None
    context.user_data["new_product"] = {}

    await update.message.reply_text(
        text="⚙️ **AT SELECTION - Admin Panel**\n"
             "Manage your categories, products, and view recent customer inquiries.",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- CATEGORY MANAGEMENT ---

async def manage_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows options for managing categories."""
    categories = db.get_categories()
    
    text = "📁 **Current Categories:**\n"
    if categories:
        for idx, cat in enumerate(categories):
            text += f" • {cat}\n"
    else:
        text += " *(No categories created yet)*"
        
    keyboard = [
        [InlineKeyboardButton("➕ Add Category", callback_data="admin_cat_add")],
        [InlineKeyboardButton("🗑️ Delete Category", callback_data="admin_cat_del")]
    ]
    
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_add_category(query, context: ContextTypes.DEFAULT_TYPE):
    """Asks for category name."""
    context.user_data["admin_state"] = "awaiting_category_name"
    await query.message.reply_text(
        text="✍️ Please enter the **Category Name** you want to add:\n"
             "*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves category name."""
    name = update.message.text.strip()
    if name.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    success = db.add_category(name)
    context.user_data["admin_state"] = None
    
    if success:
        await update.message.reply_text(f"✅ Category **'{name}'** added successfully!")
    else:
        await update.message.reply_text(f"⚠️ Failed to add. Category might already exist.")
        
    await send_admin_menu(update, context)

async def start_delete_category(query, context: ContextTypes.DEFAULT_TYPE):
    """Lists categories with delete buttons."""
    categories = db.get_categories()
    if not categories:
        await query.message.reply_text("📭 No categories to delete.")
        return
        
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"🗑️ Delete {cat}", callback_data=f"admin_cat_del_confirm:{cat}")])
        
    await query.message.reply_text(
        text="⚠️ **Warning: You can only delete a category if it has no products!**\n"
             "Select the category to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def confirm_delete_category(query, context: ContextTypes.DEFAULT_TYPE, category_name):
    """Executes category deletion."""
    success = db.delete_category(category_name)
    if success:
        await query.message.reply_text(f"✅ Category **'{category_name}'** deleted successfully!")
    else:
        await query.message.reply_text(
            f"❌ Failed to delete **'{category_name}'**.\n"
            f"Make sure there are no products assigned to this category before deleting it."
        )
    # Refresh admin panel
    # We send text message as query is callback
    # Create fake message to run send_admin_menu
    from handlers_user import get_main_menu_keyboard
    await query.message.reply_text(
        text="Updated admin panel state.",
        reply_markup=get_admin_menu_keyboard()
    )

# --- PRODUCT MANAGEMENT ---

async def manage_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows options for managing products."""
    keyboard = [
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_prod_add")],
        [InlineKeyboardButton("🗑️ Delete Product", callback_data="admin_prod_del")],
        [InlineKeyboardButton("📥 Import Excel", callback_data="admin_prod_import")]
    ]
    await update.message.reply_text(
        text="👗 **Product Management**\n"
             "Choose an operation:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- ADD PRODUCT CONVERSATION ---

async def start_add_product(query, context: ContextTypes.DEFAULT_TYPE):
    """First step: Select category."""
    categories = db.get_categories()
    if not categories:
        await query.message.reply_text(
            "⚠️ You must create at least one category before adding products!"
        )
        return
        
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"admin_prod_add_cat:{cat}")])
        
    context.user_data["new_product"] = {}
    await query.message.reply_text(
        text="👗 **Add Product - Step 1 of 6**\n\n"
             "Select the **Category** for the new product:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def select_product_add_category(query, context: ContextTypes.DEFAULT_TYPE, category):
    """Second step: Ask for name."""
    context.user_data["new_product"]["category"] = category
    context.user_data["admin_state"] = "prod_add_name"
    await query.message.reply_text(
        text=f"📂 Category selected: **{category}**\n\n"
             f"**Step 2 of 6**: Please enter the **Product Name**:\n"
             f"*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_product_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Third step: Ask for description."""
    name = update.message.text.strip()
    if name.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    context.user_data["new_product"]["name"] = name
    context.user_data["admin_state"] = "prod_add_desc"
    await update.message.reply_text(
        text=f"✍️ Name: **{name}**\n\n"
             f"**Step 3 of 6**: Enter the **Product Description** (or type 'none' to skip):\n"
             f"*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_product_add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fourth step: Ask for price."""
    desc = update.message.text.strip()
    if desc.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    context.user_data["new_product"]["description"] = "" if desc.lower() == "none" else desc
    context.user_data["admin_state"] = "prod_add_price"
    await update.message.reply_text(
        text=f"**Step 4 of 6**: Enter the **Wholesale Price** in Rs (number only):\n"
             f"*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_product_add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fifth step: Ask for sizes."""
    price_text = update.message.text.strip()
    if price_text.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    try:
        price = float(price_text)
        context.user_data["new_product"]["price"] = price
        context.user_data["admin_state"] = "prod_add_sizes"
        await update.message.reply_text(
            text=f"💰 Price set: **Rs. {price}**\n\n"
                 f"**Step 5 of 6**: Enter available **Sizes** comma-separated (e.g. 'M, L, XL, XXL' or 'Set of 4' or type 'none' to skip):\n"
                 f"*(Or type 'cancel' to abort)*",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("⚠️ Invalid price. Please enter a valid number (e.g., 450 or 450.50):")

async def process_product_add_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sixth step: Ask for photo."""
    sizes = update.message.text.strip()
    if sizes.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    context.user_data["new_product"]["sizes"] = "" if sizes.lower() == "none" else sizes
    context.user_data["admin_state"] = "prod_add_photo"
    await update.message.reply_text(
        text=f"📏 Sizes set: **{sizes}**\n\n"
             f"**Step 6 of 6**: Please **Upload the Product Photo** (Send as photo, not document):\n"
             f"*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_product_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step: Save product."""
    if not update.message.photo:
        await update.message.reply_text("⚠️ That was not a photo. Please send a photo of the product:")
        return
        
    # Get highest resolution photo file ID
    file_id = update.message.photo[-1].file_id
    new_prod = context.user_data.get("new_product")
    
    # Save product
    prod_id = db.add_product(
        name=new_prod["name"],
        category=new_prod["category"],
        description=new_prod["description"],
        price=new_prod["price"],
        sizes=new_prod["sizes"],
        photo_file_id=file_id
    )
    
    context.user_data["admin_state"] = None
    context.user_data["new_product"] = {}
    
    if prod_id:
        # Sync with FAISS vector database
        try:
            import vector_db
            product_obj = db.get_product(prod_id)
            if product_obj:
                vector_db.add_product_to_vector_db(product_obj)
        except Exception as e:
            print(f"Error syncing new product to vector DB: {e}")

        await update.message.reply_text(
            f"✅ Product **'{new_prod['name']}'** added successfully under category **'{new_prod['category']}'**!"
        )
    else:
        await update.message.reply_text("❌ Failed to add product to database.")
        
    await send_admin_menu(update, context)

# --- DELETE PRODUCT ---

async def start_delete_product_category(query, context: ContextTypes.DEFAULT_TYPE):
    """Delete Product Step 1: Select Category."""
    categories = db.get_categories()
    if not categories:
        await query.message.reply_text("📭 No categories available.")
        return
        
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"admin_prod_del_cat:{cat}")])
        
    await query.message.reply_text(
        text="🗑️ **Delete Product**\n\nSelect category of the product to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def list_products_for_deletion(query, context: ContextTypes.DEFAULT_TYPE, category):
    """Delete Product Step 2: Select Product from List."""
    products = db.get_products_by_category(category)
    if not products:
        await query.message.reply_text(f"📭 No products found in **{category}**.")
        return
        
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"❌ {p['name']} (Rs.{p['price']})", callback_data=f"admin_prod_del_confirm:{p['id']}:{category}")])
        
    await query.message.reply_text(
        text=f"🗑️ **Delete Product**\n\nSelect which product in **{category}** to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def confirm_delete_product(query, context: ContextTypes.DEFAULT_TYPE, product_id, category):
    """Executes product deletion."""
    product = db.get_product(product_id)
    success = db.delete_product(product_id)
    
    if success and product:
        # Sync with FAISS vector database
        try:
            import vector_db
            vector_db.delete_product_from_vector_db(product_id)
        except Exception as e:
            print(f"Error removing product from vector DB: {e}")

        await query.message.reply_text(f"✅ Product **'{product['name']}'** deleted successfully.")
    else:
        await query.message.reply_text("❌ Failed to delete product or product not found.")
        
    # Refresh by showing list again
    await list_products_for_deletion(query, context, category)

# --- VIEW INQUIRIES ---

async def view_recent_inquiries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays recent inquiries logged in the database."""
    inquiries = db.get_inquiries(limit=10)
    if not inquiries:
        await update.message.reply_text("📭 No customer inquiries found in log.")
        return
        
    text = "📋 **Recent Garment Inquiries (Last 10):**\n\n"
    for inq in inquiries:
        text += (
            f"🆔 **Inquiry #{inq['id']}** | {inq['created_at'][:16]}\n"
            f"👤 **Customer:** {inq['customer_name']}\n"
            f"📱 **Phone:** {inq['customer_phone']}\n"
            f"🛒 **Items:**\n"
        )
        total = 0
        for item in inq["items"]:
            sub = item['price'] * item['quantity']
            total += sub
            text += f"   • {item['name']} ({item.get('sizes', 'Standard')}) x {item['quantity']} = Rs.{sub}\n"
        text += f"💰 **Total Est:** Rs. {total}\n"
        text += f"⚙️ **Status:** `{inq['status'].upper()}`\n"
        text += "-------------------------------\n\n"
        
    # Send inquiry list
    # If the message is too long, we might hit limits, but 10 inquiries fit comfortably.
    await update.message.reply_text(text=text, parse_mode="Markdown")

# --- ADD ADMIN ---

async def start_add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instructs admin on how to add another admin."""
    context.user_data["admin_state"] = "awaiting_new_admin_id"
    await update.message.reply_text(
        text="👥 **Add New Admin**\n\n"
             "Please enter the **Telegram User ID** (numbers only) of the user you want to make an admin.\n\n"
             "💡 *Tip: The user can find their User ID by messaging [@userinfobot](https://t.me/userinfobot) on Telegram.*\n\n"
             "*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves new admin ID."""
    text = update.message.text.strip()
    if text.lower() == "cancel":
        await send_admin_menu(update, context)
        return
        
    try:
        new_admin_id = int(text)
        success = db.add_admin(new_admin_id, username=f"admin_{new_admin_id}")
        context.user_data["admin_state"] = None
        
        if success:
            await update.message.reply_text(f"✅ User ID **{new_admin_id}** is now registered as an Admin!")
        else:
            await update.message.reply_text(f"ℹ️ User ID **{new_admin_id}** is already an admin or database error.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ID. Please enter a valid number ID (e.g. 123456789):")
        return
        
    await send_admin_menu(update, context)

# --- GLOBAL CALLBACK ROUTER FOR ADMIN ---

async def handle_admin_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes callback queries matching admin commands."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.message.reply_text("⛔ Unauthorized.")
        return
        
    if data == "admin_cat_add":
        await start_add_category(query, context)
        
    elif data == "admin_cat_del":
        await start_delete_category(query, context)
        
    elif data.startswith("admin_cat_del_confirm:"):
        category_name = data.split(":", 1)[1]
        await confirm_delete_category(query, context, category_name)
        
    elif data == "admin_prod_add":
        await start_add_product(query, context)
        
    elif data.startswith("admin_prod_add_cat:"):
        category = data.split(":", 1)[1]
        await select_product_add_category(query, context, category)
        
    elif data == "admin_prod_del":
        await start_delete_product_category(query, context)
        
    elif data == "admin_prod_import":
        await start_import_excel(query, context)
        
    elif data.startswith("admin_prod_del_cat:"):
        category = data.split(":", 1)[1]
        await list_products_for_deletion(query, context, category)
        
    elif data.startswith("admin_prod_del_confirm:"):
        parts = data.split(":")
        product_id = int(parts[1])
        category = parts[2]
        await confirm_delete_product(query, context, product_id, category)

# --- GLOBAL TEXT MESSAGE ROUTER FOR ADMIN ---

async def handle_admin_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes admin state inputs when admin panel conversation is active."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        return False
        
    state = context.user_data.get("admin_state")
    text = update.message.text
    
    # 1. State machine processing
    if state == "awaiting_category_name":
        await process_add_category(update, context)
        return True
    elif state == "prod_add_name":
        await process_product_add_name(update, context)
        return True
    elif state == "prod_add_desc":
        await process_product_add_desc(update, context)
        return True
    elif state == "prod_add_price":
        await process_product_add_price(update, context)
        return True
    elif state == "prod_add_sizes":
        await process_product_add_sizes(update, context)
        return True
    elif state == "prod_add_photo":
        await process_product_add_photo(update, context)
        return True
    elif state == "awaiting_new_admin_id":
        await process_add_admin_id(update, context)
        return True
    elif state == "prod_import_excel":
        if text.strip().lower() == "cancel":
            context.user_data["admin_state"] = None
            await send_admin_menu(update, context)
        else:
            await update.message.reply_text("⚠️ Please upload a valid `.xlsx` spreadsheet, or type 'cancel' to exit:")
        return True
        
    # 2. Command routing
    if text == "📁 Manage Categories":
        await manage_categories_menu(update, context)
        return True
    elif text == "👗 Manage Products":
        await manage_products_menu(update, context)
        return True
    elif text == "📋 View Inquiries":
        await view_recent_inquiries(update, context)
        return True
    elif text == "👥 Add Admin ID":
        await start_add_admin_id(update, context)
        return True
    elif text == "📊 AI Report":
        await generate_ai_report(update, context)
        return True
    elif text == "🔙 Exit Admin Menu":
        # Clear user state and send back to main menu
        context.user_data["admin_state"] = None
        context.user_data["new_product"] = {}
        from handlers_user import start_command
        await start_command(update, context)
        return True
        
    return False


# --- AI REPORT (CrewAI) ---

async def generate_ai_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate an AI-powered daily business report using CrewAI Report Agent."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ Access denied. Only admins can generate reports.")
        return

    await update.message.reply_text(
        "📊 **Generating AI Business Report...**\n\n"
        "🤖 The CrewAI Report Agent is analyzing your inquiries and catalog data.\n"
        "This may take 15-30 seconds...",
        parse_mode="Markdown"
    )

    try:
        from crew_agents import run_report_crew
        report = await run_report_crew()
        
        # Split report if too long for Telegram (4096 char limit)
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                await update.message.reply_text(text=chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                text=f"📊 **AT SELECTION — AI Business Report**\n\n{report}",
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to generate report: {str(e)}\n\n"
            "Make sure CrewAI is installed and Gemini API key is configured.",
            parse_mode="Markdown"
        )

# --- BULK EXCEL PRODUCT IMPORT ---

async def start_import_excel(query, context: ContextTypes.DEFAULT_TYPE):
    """Sets admin state to awaiting excel file upload."""
    context.user_data["admin_state"] = "prod_import_excel"
    await query.message.reply_text(
        text="📥 **Bulk Excel Product Import**\n\n"
             "Please upload a **Garment Catalog `.xlsx`** file.\n\n"
             "The sheet *must* contain the following headers:\n"
             "• **Category**\n"
             "• **Name** (or 'Garment Name')\n"
             "• **Price** (wholesale numbers only)\n\n"
             "You can also include optional headers: **Description**, **Sizes**, **Image_Filename**.\n\n"
             "*(Or type 'cancel' to abort)*",
        parse_mode="Markdown"
    )

async def process_product_import_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads the uploaded Excel file, calls the importer, and reports results."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ Unauthorized.")
        return
        
    document = update.message.document
    if not document:
        await update.message.reply_text("⚠️ No document found. Please upload a valid Excel spreadsheet:")
        return
        
    filename = document.file_name
    if not filename.endswith((".xlsx", ".xls")):
        await update.message.reply_text("⚠️ Invalid file format. Please upload a `.xlsx` file:")
        return
        
    await update.message.reply_text("⏳ **Processing spreadsheet...** Please wait.")
    
    try:
        import os
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download file
        new_file = await context.bot.get_file(document.file_id)
        local_path = os.path.join(temp_dir, filename)
        await new_file.download_to_drive(local_path)
        
        # Import products
        import excel_importer
        import vector_db
        
        results = excel_importer.import_excel_catalog(local_path)
        
        # Clean up temp file
        if os.path.exists(local_path):
            os.remove(local_path)
            
        if results["success"]:
            # Trigger index rebuild to ensure everything matches and is clean
            vector_db.rebuild_index()
            
            res_msg = (
                f"✅ **Bulk Import Complete!**\n\n"
                f"📥 **File processed:** `{filename}`\n"
                f"➕ **New products added:** {results['inserted']}\n"
                f"🔄 **Existing products updated:** {results['updated']}\n"
                f"⏭️ **Skipped products:** {results['skipped']}\n"
            )
            
            if results["errors"]:
                res_msg += "\n⚠️ **Details/Errors encountered:**\n"
                for err in results["errors"][:10]:
                    res_msg += f"• {err}\n"
                if len(results["errors"]) > 10:
                    res_msg += f"• ...and {len(results['errors']) - 10} more errors.\n"
                    
            await update.message.reply_text(res_msg, parse_mode="Markdown")
        else:
            err_details = "\n".join(results["errors"])
            await update.message.reply_text(
                f"❌ **Import Failed:**\n{err_details}"
            )
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ **An error occurred during import:**\n`{str(e)}`"
        )
        
    # Reset admin state and return to menu
    context.user_data["admin_state"] = None
    await send_admin_menu(update, context)

