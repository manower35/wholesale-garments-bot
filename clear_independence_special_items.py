import sys
import db
import vector_db

sys.stdout.reconfigure(encoding='utf-8')

print("[*] Clearing items from '🇮🇳 Independence Special' category...")

# Remove products assigned to 🇮🇳 Independence Special
with db.db_session() as conn:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE category = ?", ("🇮🇳 Independence Special",))
    deleted_count = cursor.rowcount
    conn.commit()

print(f"[+] Removed {deleted_count} sample items from '🇮🇳 Independence Special'.")

# Ensure category exists in categories table for future #add commands
db.add_category("🇮🇳 Independence Special")

# Rebuild FAISS index
print("[*] Rebuilding FAISS vector index...")
vector_db.rebuild_index()

print("✅ '🇮🇳 Independence Special' category is now clear and ready for your custom phone photo uploads!")
