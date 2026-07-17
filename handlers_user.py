import os
import urllib.parse
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InputMediaPhoto,
    KeyboardButton
)
from telegram.ext import ContextTypes, MessageHandler, filters
import db
import config
import ai_agent
import vector_db

# Main Menu Keyboards
def get_main_menu_keyboard(user_id):
    keyboard = [
        ["🛍️ Browse Catalog", "🔍 Search Products"],
        ["🛒 View Cart/Inquiry", "📞 Contact & Info"]
    ]
    if db.is_admin(user_id):
        keyboard.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Initialize DB (just in case)
    db.init_db()
    
    # Check if they passed the admin setup token in the command arguments (e.g. /start admin12345)
    if context.args and context.args[0].strip() == config.ADMIN_SETUP_TOKEN:
        if not db.is_admin(user_id):
            db.add_admin(user_id, username)
            await update.message.reply_text(
                "🎉 **Token accepted!**\n"
                "You are now registered as an **Admin**.\n"
                "The ⚙️ Admin Panel button is now visible on your main menu below.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode="Markdown"
            )
            return
        else:
            await update.message.reply_text(
                "ℹ️ You are already registered as an **Admin**!",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode="Markdown"
            )
            return

    welcome_text = (
        f"👋 Welcome to **{config.BUSINESS_NAME}** Catalog Bot!\n"
        f"We specialize in **{config.BUSINESS_SUBTITLE}**.\n\n"
        f"👤 Owner: **{config.OWNER_NAME}**\n"
        f"🕒 Hours: **{config.BUSINESS_HOURS}**\n"
        f"📍 Address: {config.BUSINESS_ADDRESS}\n\n"
        f"Browse our wholesale products, add items to your inquiry list, "
        f"and send them directly to us."
    )
    
    # Check if logo.jpg exists locally
    logo_path = "logo.jpg"
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=welcome_text,
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode="Markdown"
                )
            return
        except Exception as e:
            # Fallback if photo sending fails
            pass
            
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="Markdown"
    )

async def reset_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears the AI chat memory context for the user."""
    user_id = update.effective_user.id
    db.clear_chat_history(user_id)
    context.user_data["state"] = None
    context.user_data["admin_state"] = None
    context.user_data["new_product"] = {}
    await update.message.reply_text(
        "🧹 **AI Chat Memory cleared!** Our conversation context has been reset.",
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="Markdown"
    )

async def stock_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stock and /summary commands. Displays a summary of the catalog."""
    user_id = update.effective_user.id
    
    categories = db.get_categories()
    if not categories:
        await update.message.reply_text(
            "📭 The catalog is currently empty. Please check back later!",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
        
    total_products = 0
    category_summary = []
    
    for cat in categories:
        products = db.get_products_by_category(cat)
        count = len(products)
        total_products += count
        category_summary.append(f"• **{cat}**: {count} product(s)")
        
    summary_text = (
        f"📊 **{config.BUSINESS_NAME} — Catalog Summary**\n\n"
        f"📁 **Total Categories**: {len(categories)}\n"
        f"👗 **Total Products**: {total_products}\n\n"
        + "\n".join(category_summary) + "\n\n"
        f"*(Select '🛍️ Browse Catalog' from the main menu to view products)*"
    )
    
    await update.message.reply_text(
        text=summary_text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="Markdown"
    )

async def handle_admin_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes messages to check if a user is trying to claim admin rights."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text.strip()
    
    if text == config.ADMIN_SETUP_TOKEN:
        if db.is_admin(user_id):
            await update.message.reply_text("ℹ️ You are already an admin!")
            return True
        
        # Add to database
        db.add_admin(user_id, username)
        await update.message.reply_text(
            text="🎉 **Token accepted!**\n"
                 "You are now registered as an **Admin**.\n"
                 "Type /start to refresh your menu and see the ⚙️ Admin Panel option.",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode="Markdown"
        )
        return True
    return False

# --- CONTACT INFO ---

async def send_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the contact details and shop details from the business card."""
    info_text = (
        f"🏬 **{config.BUSINESS_NAME}**\n"
        f"_{config.BUSINESS_SUBTITLE}_\n\n"
        f"👤 **Owner:** {config.OWNER_NAME}\n"
        f"🕒 **Business Hours:** {config.BUSINESS_HOURS}\n\n"
        f"📞 **Phone Numbers:**\n"
        f"  • +91 {config.OWNER_PHONES[0]} (WhatsApp)\n"
        f"  • +91 {config.OWNER_PHONES[1]}\n"
        f"  • +91 {config.OWNER_PHONES[2]}\n\n"
        f"✉️ **Email:** {config.OWNER_EMAILS[0]}\n"
        f"📍 **Shop Address:**\n"
        f"{config.BUSINESS_ADDRESS}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💬 Chat on WhatsApp", url=config.WHATSAPP_LINK),
            InlineKeyboardButton("📸 Visit Instagram", url=config.INSTAGRAM_LINK)
        ],
        [
            InlineKeyboardButton("📍 View Shop Location", url=config.MAPS_LINK)
        ]
    ]
    
    await update.message.reply_text(
        text=info_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- BROWSE CATALOG ---

async def browse_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays category selection to the user."""
    categories = db.get_categories()
    if not categories:
        await update.message.reply_text("📭 The catalog is currently empty. Please check back later!")
        return
        
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_sel:{cat}")])
        
    await update.message.reply_text(
        text="📁 **Please select a product category to browse:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback queries from inline buttons (browsing, cart, checkout)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("cat_sel:"):
        # Selected a category
        category = data.split(":", 1)[1]
        products = db.get_products_by_category(category)
        if not products:
            await query.edit_message_text(
                text=f"📭 No products in **{category}** category yet.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")]]),
                parse_mode="Markdown"
            )
            return
            
        await show_product_carousel(query, products, index=0, category=category)
        
    elif data.startswith("cat_nav:"):
        # Carousel navigation
        parts = data.split(":")
        category = parts[1]
        index = int(parts[2])
        products = db.get_products_by_category(category)
        
        if not products or index < 0 or index >= len(products):
            return
            
        await show_product_carousel(query, products, index, category)
        
    elif data.startswith("prod_add:"):
        # Add to cart from carousel
        parts = data.split(":")
        product_id = int(parts[1])
        category = parts[2]
        index = int(parts[3])
        
        # Add to cart
        db.add_to_cart(user_id, product_id, quantity=1)
        product = db.get_product(product_id)
        
        # We can update the text or alert the user
        await query.answer(text=f"🛍️ Added '{product['name']}' to inquiry cart!", show_alert=False)
        
        # Redraw same product (to keep user in flow, but maybe show updated cart badge)
        products = db.get_products_by_category(category)
        await show_product_carousel(query, products, index, category)
        
    elif data == "back_categories":
        # Go back to categories list
        categories = db.get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_sel:{cat}")])
            
        await query.edit_message_text(
            text="📁 **Please select a product category to browse:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    elif data.startswith("cart_mod:"):
        # Modify quantity in cart
        parts = data.split(":")
        product_id = int(parts[1])
        change = int(parts[2])
        
        cart_items = db.get_cart(user_id)
        current_qty = 0
        for item in cart_items:
            if item["product_id"] == product_id:
                current_qty = item["quantity"]
                break
                
        new_qty = current_qty + change
        db.update_cart_quantity(user_id, product_id, new_qty)
        
        # Refresh cart message
        await show_cart(query.message, user_id, is_callback=True)
        
    elif data.startswith("cart_del:"):
        # Delete item from cart
        product_id = int(data.split(":")[1])
        db.remove_from_cart(user_id, product_id)
        await query.answer("🗑️ Item removed.")
        await show_cart(query.message, user_id, is_callback=True)
        
    elif data == "cart_clear":
        db.clear_cart(user_id)
        await query.answer("🧹 Cart cleared.")
        await show_cart(query.message, user_id, is_callback=True)
        
    elif data == "cart_checkout":
        # Start checkout process
        cart = db.get_cart(user_id)
        if not cart:
            await query.answer("🛒 Your cart is empty!")
            return
            
        # Put user in checkout state
        context.user_data["state"] = "awaiting_checkout_name"
        
        # Ask for name
        await query.message.reply_text(
            text="👤 **Checkout - Step 1 of 2**\n\n"
                 "Please enter your **Full Name** (or Business/Shop Name):",
            parse_mode="Markdown"
        )

def resolve_media(media_str):
    """Helper to check if a media string is a local path.
    Returns open file object if local file exists, otherwise returns original string.
    """
    import os
    if media_str and os.path.exists(media_str):
        try:
            return open(media_str, "rb")
        except Exception:
            pass
    return media_str

async def show_product_carousel(query, products, index, category):
    """Helper to display product carousel using photos and inline navigation."""
    product = products[index]
    total = len(products)
    
    caption = (
        f"✨ **{product['name']}**\n"
        f"🏷️ **Category:** {product['category']}\n"
        f"📏 **Sizes Available:** {product['sizes'] if product['sizes'] else 'N/A'}\n\n"
        f"📝 **Description:**\n{product['description'] if product['description'] else 'No description available.'}"
    )
    
    # Navigation row
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cat_nav:{category}:{index-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("❌", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(f"📄 {index+1} / {total}", callback_data="noop"))
    
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"cat_nav:{category}:{index+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("❌", callback_data="noop"))
        
    keyboard = [
        nav_buttons,
        [InlineKeyboardButton("➕ Add to Inquiry Cart", callback_data=f"prod_add:{product['id']}:{category}:{index}")],
        [InlineKeyboardButton("🔙 Back to Categories", callback_data="back_categories")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if product["photo_file_id"]:
        # Resolve media string (handles local file paths or Telegram file IDs)
        media_obj = resolve_media(product["photo_file_id"])
        
        # If the query message has a photo, edit it. Otherwise, send a new photo message
        if query.message.photo:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=media_obj, caption=caption, parse_mode="Markdown"),
                    reply_markup=reply_markup
                )
            except Exception:
                # Fallback if media edit fails
                # Re-open file if it was a file stream
                media_obj = resolve_media(product["photo_file_id"])
                await query.message.reply_photo(
                    photo=media_obj,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                await query.message.delete()
        else:
            # Message is text only (e.g. from category menu), delete it and send photo
            await query.message.delete()
            await query.message.reply_photo(
                photo=media_obj,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    else:
        # Product has no photo, show as text message
        text = f"🖼️ *No Image Available*\n\n{caption}"
        if query.message.photo:
            # Delete photo message, send text
            await query.message.delete()
            await query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

# --- SEARCH ---

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets user state to awaiting search term."""
    context.user_data["state"] = "awaiting_search_query"
    await update.message.reply_text(
        text="🔍 **Search Products**\n\n"
             "Please type what you are looking for (e.g., 'Cotton', 'Kurti', 'Dress'):",
        parse_mode="Markdown"
    )

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Performs search and displays results."""
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("⚠️ Search query is too short. Please type at least 2 characters.")
        return
        
    results = db.search_products(query)
    context.user_data["state"] = None # Clear state
    
    is_semantic = False
    if not results:
        logger = logging = ai_agent.logger # borrow logger or use standard import
        ai_agent.logger.info(f"Exact match failed. Running semantic vector fallback search for: {query}")
        results = vector_db.search_catalog_semantic(query, k=5)
        is_semantic = True
        
    if not results:
        await update.message.reply_text(
            text=f"📭 No matching products found for **'{query}'**.",
            parse_mode="Markdown"
        )
        return
        
    match_type = "semantic recommendation(s)" if is_semantic else "match(es)"
    await update.message.reply_text(
        text=f"🔍 Found **{len(results)}** {match_type} for **'{query}'**:\n"
             f"Click below to browse search results:",
        parse_mode="Markdown"
    )
    
    # We display search results in a carousel style under a dummy category representing the search query
    # Since they are search results, we can temporarily load them.
    # To simplify, we can just show the list of search results with inline buttons
    keyboard = []
    for item in results[:10]: # Limit to first 10 search results to avoid long list
        keyboard.append([
            InlineKeyboardButton(
                f"{item['name']}",
                # Direct them to view it by navigating to its category
                callback_data=f"cat_sel:{item['category']}"
            )
        ])
    
    await update.message.reply_text(
        text="👇 Click on any product to view its category page:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- CART / INQUIRY FLOW ---

async def display_cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command/Button handler for viewing cart."""
    user_id = update.effective_user.id
    await show_cart(update.message, user_id, is_callback=False)

async def show_cart(message, user_id, is_callback=False):
    """Displays the current shopping cart with item modifications and checkout buttons."""
    cart_items = db.get_cart(user_id)
    
    if not cart_items:
        text = "🛒 **Your Inquiry Cart is empty.**\n\nBrowse the catalog to add items!"
        reply_markup = None
        
        if is_callback:
            await message.edit_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return
        
    text = "🛒 **Your Wholesale Inquiry Cart:**\n\n"
    keyboard = []
    
    for idx, item in enumerate(cart_items):
        text += (
            f"🔸 **{idx+1}. {item['name']}**\n"
            f"   Sizes: {item['sizes'] if item['sizes'] else 'Standard'}\n"
            f"   Quantity: **{item['quantity']}**\n\n"
        )
        
        # Row of adjusters for this product
        keyboard.append([
            InlineKeyboardButton(f"➖ {item['name'][:10]}", callback_data=f"cart_mod:{item['product_id']}:-1"),
            InlineKeyboardButton(f"🔢 {item['quantity']}", callback_data="noop"),
            InlineKeyboardButton(f"➕ {item['name'][:10]}", callback_data=f"cart_mod:{item['product_id']}:1"),
            InlineKeyboardButton("🗑️", callback_data=f"cart_del:{item['product_id']}")
        ])
        
    text += "*(Prices are calculated upon manual review based on bulk quantity, customization, and shipping)*"
    
    keyboard.append([
        InlineKeyboardButton("🧹 Clear Cart", callback_data="cart_clear"),
        InlineKeyboardButton("🚀 Submit Inquiry", callback_data="cart_checkout")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await message.edit_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

async def process_checkout_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes customer name input during checkout."""
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("⚠️ Please enter a valid name (at least 2 letters).")
        return
        
    context.user_data["checkout_name"] = name
    context.user_data["state"] = "awaiting_checkout_phone"
    
    # Request Phone using Keyboard Button (which makes it easy to share contact)
    phone_button = KeyboardButton(text="📱 Share Phone Number", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[phone_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        text="📱 **Checkout - Step 2 of 2**\n\n"
             "Please click the button below to **Share your contact number** "
             "or type it manually in international format (e.g. +91 98765 43210):",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def process_checkout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes customer phone number input, saves inquiry, notifies admin and provides WhatsApp link."""
    user_id = update.effective_user.id
    name = context.user_data.get("checkout_name")
    
    phone = ""
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        # Basic validation
        if len(phone) < 8:
            await update.message.reply_text("⚠️ Please enter a valid phone number.")
            return
            
    # Load cart items
    cart = db.get_cart(user_id)
    if not cart:
        await update.message.reply_text(
            "🛒 Your cart was empty or already submitted!",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        context.user_data["state"] = None
        return
        
    # Save inquiry in DB
    inq_id = db.save_inquiry(user_id, name, phone, cart)
    
    # Create inquiry details message
    inquiry_summary = f"📋 **New Inquiry #{inq_id}**\n"
    inquiry_summary += f"👤 **Customer:** {name}\n"
    inquiry_summary += f"📱 **Phone:** {phone}\n"
    inquiry_summary += f"🆔 **Telegram ID:** {user_id}\n\n"
    
    wa_items_text = ""
    for idx, item in enumerate(cart):
        inquiry_summary += f"• {item['name']} ({item['sizes']}) x {item['quantity']}\n"
        wa_items_text += f"- {item['name']} ({item['sizes']}) x {item['quantity']}\n"
        
    # 1. Notify Admins
    admins = db.get_admins()
    admin_notified = False
    for admin in admins:
        try:
            await context.bot.send_message(
                chat_id=admin["user_id"],
                text=f"🔔 **URGENT: New Garment Inquiry Received!**\n\n{inquiry_summary}",
                parse_mode="Markdown"
            )
            admin_notified = True
        except Exception as e:
            print(f"Failed to notify admin {admin['user_id']}: {e}")
            
    # 2. Build WhatsApp Click-to-Chat Link for Customer
    wa_message = (
        f"Hello Syed Ahmer, I placed a wholesale inquiry for {config.BUSINESS_NAME} via Telegram Bot!\n\n"
        f"Inquiry ID: #{inq_id}\n"
        f"Customer: {name}\n"
        f"Phone: {phone}\n\n"
        f"Items:\n{wa_items_text}\n"
        f"Please verify this inquiry and provide a price quote."
    )
    
    encoded_message = urllib.parse.quote(wa_message)
    wa_link = f"https://wa.me/91{config.OWNER_PHONES[0]}?text={encoded_message}"
    
    # Clear user cart and state
    db.clear_cart(user_id)
    context.user_data["state"] = None
    context.user_data["checkout_name"] = None
    
    # Response keyboard
    success_buttons = [
        [InlineKeyboardButton("💬 Confirm via WhatsApp", url=wa_link)]
    ]
    
    await update.message.reply_text(
        text="🎉 **Inquiry Submitted Successfully!**\n\n"
             "Your wholesale inquiry has been recorded and the owner has been notified.\n\n"
             "👉 **Click the button below** to send a pre-filled summary directly to Syed Ahmer on WhatsApp "
             "to confirm your order instantly!",
        reply_markup=InlineKeyboardMarkup(success_buttons),
        parse_mode="Markdown"
    )
    
    # Send main menu keyboard back
    await update.message.reply_text(
        text="What would you like to do next?",
        reply_markup=get_main_menu_keyboard(user_id)
    )

# --- GLOBAL TEXT MESSAGE ROUTER ---

async def handle_user_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes plain text messages based on user state or main menu selections."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # 1. Check if they typed the Admin Setup Token
    if await handle_admin_token(update, context):
        return
        
    # 2. Check State machine
    state = context.user_data.get("state")
    
    if state == "awaiting_search_query":
        await handle_search_query(update, context)
        return
    elif state == "awaiting_checkout_name":
        await process_checkout_name(update, context)
        return
    elif state == "awaiting_checkout_phone":
        await process_checkout_phone(update, context)
        return
        
    # 3. Main Menu Selections
    if text == "🛍️ Browse Catalog":
        await browse_categories(update, context)
    elif text == "🔍 Search Products":
        await start_search(update, context)
    elif text == "🛒 View Cart/Inquiry":
        await display_cart_command(update, context)
    elif text == "📞 Contact & Info":
        await send_contact_info(update, context)
    elif text == "⚙️ Admin Panel":
        if db.is_admin(user_id):
            # Send them to the admin module (imported locally to avoid circular dependencies)
            from handlers_admin import send_admin_menu
            await send_admin_menu(update, context)
        else:
            await update.message.reply_text("⛔ Access denied. Only admins can access this area.")
    else:
        # Send typing action so user knows AI is working
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        except Exception:
            pass
            
        # Call LangChain AI Agent
        ai_reply = await ai_agent.ask_ai_agent(user_id, update.message.text)
        if ai_reply:
            # Safely convert AI markdown to HTML to prevent Telegram parsing crashes
            def markdown_to_html(text: str) -> str:
                # Escape raw HTML syntax first
                text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                # Convert **bold** to <b>bold</b>
                parts = text.split("**")
                new_parts = []
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        new_parts.append(f"<b>{part}</b>")
                    else:
                        new_parts.append(part)
                text = "".join(new_parts)
                
                # Convert *italic* to <i>italic</i>
                parts = text.split("*")
                new_parts = []
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        new_parts.append(f"<i>{part}</i>")
                    else:
                        new_parts.append(part)
                text = "".join(new_parts)
                return text

            html_reply = markdown_to_html(ai_reply)
            await update.message.reply_text(html_reply, parse_mode="HTML")
        else:
            # Fallback if Gemini key is missing or failed
            await update.message.reply_text(
                text="Please use the buttons below to navigate or type a question about our garments:",
                reply_markup=get_main_menu_keyboard(user_id)
            )
