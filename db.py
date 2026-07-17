import sqlite3
import json
from config import DB_PATH
from contextlib import contextmanager

@contextmanager
def db_session():
    """Context manager for SQLite database sessions.
    Automatically commits or rolls back, and guarantees connection closure.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes the database, creating all tables if they do not exist."""
    import os
    from config import DB_PATH
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                sizes TEXT,
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category) REFERENCES categories (name) ON DELETE RESTRICT
            )
        """)
        
        # Cart table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)
        
        # Admins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inquiries table (to keep a log of all customer inquiries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                items_json TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Chat history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# --- ADMIN MANAGEMENT ---

def is_admin(user_id):
    """Checks if a user is registered as an admin."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def add_admin(user_id, username=None):
    """Registers a new admin."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False

def get_admins():
    """Retrieves all registered admins."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM admins")
        return [dict(row) for row in cursor.fetchall()]

def has_any_admin():
    """Checks if there are any admins registered in the database."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM admins")
        count = cursor.fetchone()[0]
        return count > 0

# --- CATEGORY MANAGEMENT ---

def add_category(name):
    """Adds a new category."""
    name_clean = name.strip()
    if not name_clean:
        return False
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (name_clean,))
            return True
    except sqlite3.IntegrityError:
        return False # Category already exists

def delete_category(name):
    """Deletes a category."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            # First check if there are products in this category
            cursor.execute("SELECT COUNT(*) FROM products WHERE category = ?", (name,))
            if cursor.fetchone()[0] > 0:
                return False # Cannot delete category with products (foreign key restriction)
            
            cursor.execute("DELETE FROM categories WHERE name = ?", (name,))
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False

def get_categories():
    """Lists all category names."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories ORDER BY name ASC")
        return [row["name"] for row in cursor.fetchall()]

# --- PRODUCT MANAGEMENT ---

def add_product(name, category, description, price, sizes, photo_file_id):
    """Adds a product to the catalog."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO products (name, category, description, price, sizes, photo_file_id) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name.strip(), category.strip(), description.strip() if description else None, 
                 float(price), sizes.strip() if sizes else None, photo_file_id)
            )
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding product: {e}")
        return None

def delete_product(product_id):
    """Removes a product from the database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False

def get_product(product_id):
    """Retrieves a single product by ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_products_by_category(category_name):
    """Retrieves all products in a given category."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE category = ? ORDER BY id DESC", (category_name,))
        return [dict(row) for row in cursor.fetchall()]

def search_products(query):
    """Searches products by matching query in name or description."""
    with db_session() as conn:
        cursor = conn.cursor()
        like_query = f"%{query.strip()}%"
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC",
            (like_query, like_query)
        )
        return [dict(row) for row in cursor.fetchall()]

# --- CART MANAGEMENT ---

def add_to_cart(user_id, product_id, quantity=1):
    """Adds a product to user's cart or increments the quantity if already present."""
    with db_session() as conn:
        cursor = conn.cursor()
        # Check if product is already in cart
        cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        row = cursor.fetchone()
        
        if row:
            new_qty = row["quantity"] + quantity
            cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_qty, user_id, product_id))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))

def update_cart_quantity(user_id, product_id, quantity):
    """Updates the quantity of a product in the cart. Removes it if quantity is 0 or less."""
    if quantity <= 0:
        remove_from_cart(user_id, product_id)
        return
        
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (quantity, user_id, product_id))

def remove_from_cart(user_id, product_id):
    """Removes an item from the cart."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))

def clear_cart(user_id):
    """Clears the user's cart."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))

def get_cart(user_id):
    """Retrieves all cart items with product details for a user."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.product_id, c.quantity, p.name, p.price, p.category, p.sizes, p.photo_file_id 
               FROM cart c 
               JOIN products p ON c.product_id = p.id 
               WHERE c.user_id = ?""",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

# --- INQUIRY LOGGING ---

def save_inquiry(user_id, customer_name, customer_phone, items_list):
    """Saves a customer inquiry to the database."""
    items_json = json.dumps(items_list)
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inquiries (user_id, customer_name, customer_phone, items_json) 
                   VALUES (?, ?, ?, ?)""",
                (user_id, customer_name, customer_phone, items_json)
            )
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error saving inquiry: {e}")
        return None

def get_inquiries(limit=20):
    """Retrieves recent inquiries for admins to view."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        inquiries = []
        for row in rows:
            d = dict(row)
            d["items"] = json.loads(d["items_json"])
            inquiries.append(d)
        return inquiries

# --- CHAT HISTORY MANAGEMENT ---

def save_chat_message(user_id, role, message):
    """Saves a conversation message (user or model) to chat history."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
                (user_id, role, message)
            )
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error saving chat message: {e}")
        return None

def get_chat_history(user_id, limit=20):
    """Retrieves recent conversation history for a user, sorted descending by ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, message FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

def clear_chat_history(user_id):
    """Deletes conversation history for a user."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            return True
    except sqlite3.Error:
        return False

# --- NEW HELPERS FOR EXCEL UPSERTS ---

def get_product_by_name_and_category(name, category):
    """Retrieves a product matching the exact name and category."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE name = ? AND category = ?", (name.strip(), category.strip()))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_product(product_id, name, category, description, price, sizes, photo_file_id):
    """Updates product attributes in the database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE products 
                   SET name = ?, category = ?, description = ?, price = ?, sizes = ?, photo_file_id = ?
                   WHERE id = ?""",
                (name.strip(), category.strip(), 
                 description.strip() if description else None, 
                 float(price), 
                 sizes.strip() if sizes else None, 
                 photo_file_id, 
                 product_id)
            )
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating product: {e}")
        return False
