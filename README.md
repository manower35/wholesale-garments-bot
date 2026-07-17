# AT SELECTION — Telegram Catalog Bot with LangChain & AI Memory

A premium, database-driven Telegram Catalog and Wholesale Inquiry Bot for **AT SELECTION (Wholesale Readymade Garments)**, owned by **Syed Ahmer**. 

Built in Python using the modern `python-telegram-bot` (v21+) framework and powered by **LangChain** and **Google Gemini** for conversational AI memory.

---

## ⚡ Features
- **🤖 LangChain AI Chat Memory**: Customers can ask natural questions about fabrics, sizing, shipping, or stock (e.g. *"Do you have any blue Kurtis in size M?"*). The AI remembers the context of the conversation.
- **📁 Dynamic Catalog Context**: The AI automatically reads the latest products, sizes, prices, and categories from your SQLite database to answer customer inquiries accurately without hallucinations.
- **🧹 Memory Reset (`/reset`)**: Customers can reset their AI chat memory at any time to start a fresh conversation.
- **🛍️ Category Browsing**: Clean photo carousel with inline "Next", "Previous", "Add to Cart", and "Back to Categories" buttons.
- **🔍 Full-Text Search**: Customers can search the catalog for matching garments instantly.
- **🛒 Inquiry Cart**: Customers can adjust quantities, delete items, clear their cart, and review totals.
- **🚀 Wholesale Inquiry Submission**: Customers fill in their contact details, and the bot automatically saves the inquiry and notifies the admin.
- **💬 Click-to-Chat WhatsApp Link**: After checkout, a custom button creates a pre-filled WhatsApp message containing the full order summary to send to Syed Ahmer.
- **📞 Shop Details**: Direct links to location maps, WhatsApp chat, and Instagram profile based on the business card.
- **⚙️ Complete Admin Panel** (restricted to Admin IDs):
  - Add/delete product categories.
  - Add new products (step-by-step assistant: uploads photo, sets name, description, price, sizes).
  - Delete products under any category.
  - View a log of the last 10 customer inquiries directly in Telegram.
  - Add other admin IDs.

---

## 📂 Code Structure
- [config.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/config.py) — Configures business info, phone numbers, map links, and environment variables.
- [db.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/db.py) — Handles all SQLite operations (products, categories, carts, inquiries, admins, chat history).
- [ai_agent.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/ai_agent.py) — Custom `SQLiteChatMessageHistory` class and the LangChain Expression Language (LCEL) chain integration with Google Gemini.
- [handlers_user.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/handlers_user.py) — Core catalog browsing, cart operations, search, customer inquiry checkout, and routing general queries to the AI agent.
- [handlers_admin.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/handlers_admin.py) — Conversations for adding products, managing categories, viewing logs, and adding admins.
- [main.py](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/main.py) — Registers all handlers and runs the Telegram bot.
- [requirements.txt](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/requirements.txt) — Project packages.
- [run.bat](file:///c:/Users/attar/Desktop/Wholesale%20Readymade%20Garments/run.bat) — Convenient double-click launcher for Windows.

---

## 🚀 Setup & Launch Instructions

### Step 1: Create a Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send the command `/newbot` and follow the instructions to set a name and username.
3. Save the **HTTP API Token** (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### Step 2: Get a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click **Create API Key** and copy the generated key.

### Step 3: Configure Environment Variables
1. Rename `.env.example` to `.env` (or let `run.bat` auto-create it).
2. Open `.env` in a text editor and update:
   ```env
   BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   ```
3. (Optional) Change the `ADMIN_SETUP_TOKEN` to something unique (e.g., `mySecretToken123`).

### Step 4: Run the Bot
- Simply double-click **`run.bat`** in this directory. 
- The script will automatically verify your setup and start the bot.

---

## 🔑 How to Claim Admin Status
1. When you run the bot for the first time, open Telegram and search for your bot username.
2. Start the bot by typing `/start`.
3. Send the admin setup token configured in your `.env` file (default is `admin12345`) as a message.
4. The bot will accept it and reply: *"You are now registered as an Admin!"*
5. Type `/start` again, and you will see the **⚙️ Admin Panel** option appear in the main keyboard!
