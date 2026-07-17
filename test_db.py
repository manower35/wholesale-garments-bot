import os
import shutil
import unittest
import db

class TestDatabase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Override the database path for testing
        cls.test_db_path = "test_database.db"
        # Temporarily modify the db.DB_PATH for testing
        db.DB_PATH = cls.test_db_path
        # Clean up any leftover test db
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
            
    def setUp(self):
        # Initialize tables for each test
        db.init_db()
        
    def tearDown(self):
        # Delete test db after each test to ensure isolation
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
    def test_admin_operations(self):
        # Check initially no admins
        self.assertFalse(db.has_any_admin())
        self.assertFalse(db.is_admin(12345))
        
        # Add admin
        self.assertTrue(db.add_admin(12345, "syed_ahmer"))
        self.assertTrue(db.has_any_admin())
        self.assertTrue(db.is_admin(12345))
        
        # Test get_admins
        admins = db.get_admins()
        self.assertEqual(len(admins), 1)
        self.assertEqual(admins[0]["user_id"], 12345)
        self.assertEqual(admins[0]["username"], "syed_ahmer")
        
    def test_category_operations(self):
        # Test adding category
        self.assertTrue(db.add_category("Kurtis"))
        self.assertTrue(db.add_category("Dresses"))
        
        # Duplicate category should fail
        self.assertFalse(db.add_category("Kurtis"))
        
        # Check category list
        categories = db.get_categories()
        self.assertEqual(categories, ["Dresses", "Kurtis"])
        
        # Delete empty category
        self.assertTrue(db.delete_category("Dresses"))
        self.assertEqual(db.get_categories(), ["Kurtis"])
        
    def test_product_operations(self):
        db.add_category("Kurtis")
        
        # Add product
        p_id = db.add_product(
            name="Designer Cotton Kurti",
            category="Kurtis",
            description="Premium quality cotton kurti for wholesale",
            price=450.0,
            sizes="M, L, XL, XXL",
            photo_file_id="file_id_cotton_kurti"
        )
        self.assertIsNotNone(p_id)
        
        # Retrieve product
        product = db.get_product(p_id)
        self.assertEqual(product["name"], "Designer Cotton Kurti")
        self.assertEqual(product["price"], 450.0)
        self.assertEqual(product["sizes"], "M, L, XL, XXL")
        self.assertEqual(product["photo_file_id"], "file_id_cotton_kurti")
        
        # Retrieve products by category
        kurtis = db.get_products_by_category("Kurtis")
        self.assertEqual(len(kurtis), 1)
        self.assertEqual(kurtis[0]["id"], p_id)
        
        # Search products
        search_res = db.search_products("Cotton")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["id"], p_id)
        
        # Delete product
        self.assertTrue(db.delete_product(p_id))
        self.assertIsNone(db.get_product(p_id))
        
    def test_cart_operations(self):
        db.add_category("Kurtis")
        p_id = db.add_product("Cotton Kurti", "Kurtis", "Cotton kurti", 350.0, "M, L", "photo_id")
        
        user_id = 99999
        
        # Initially empty cart
        self.assertEqual(len(db.get_cart(user_id)), 0)
        
        # Add to cart
        db.add_to_cart(user_id, p_id, 2)
        cart = db.get_cart(user_id)
        self.assertEqual(len(cart), 1)
        self.assertEqual(cart[0]["product_id"], p_id)
        self.assertEqual(cart[0]["quantity"], 2)
        self.assertEqual(cart[0]["price"], 350.0)
        
        # Increment quantity
        db.add_to_cart(user_id, p_id, 3)
        self.assertEqual(db.get_cart(user_id)[0]["quantity"], 5)
        
        # Update quantity
        db.update_cart_quantity(user_id, p_id, 10)
        self.assertEqual(db.get_cart(user_id)[0]["quantity"], 10)
        
        # Remove item
        db.remove_from_cart(user_id, p_id)
        self.assertEqual(len(db.get_cart(user_id)), 0)
        
        # Test clear cart
        db.add_to_cart(user_id, p_id, 1)
        db.clear_cart(user_id)
        self.assertEqual(len(db.get_cart(user_id)), 0)
        
    def test_inquiry_operations(self):
        user_id = 99999
        items = [
            {"product_id": 1, "name": "Cotton Kurti", "price": 350.0, "quantity": 10},
            {"product_id": 2, "name": "Designer Dress", "price": 850.0, "quantity": 5}
        ]
        
        inq_id = db.save_inquiry(user_id, "Jane Doe", "+919876543210", items)
        self.assertIsNotNone(inq_id)
        
        inquiries = db.get_inquiries()
        self.assertEqual(len(inquiries), 1)
        self.assertEqual(inquiries[0]["id"], inq_id)
        self.assertEqual(inquiries[0]["customer_name"], "Jane Doe")
        self.assertEqual(inquiries[0]["customer_phone"], "+919876543210")
        self.assertEqual(inquiries[0]["items"], items)

    def test_chat_history_operations(self):
        user_id = 88888
        
        # Test empty chat history initially
        history = db.get_chat_history(user_id)
        self.assertEqual(len(history), 0)
        
        # Save messages
        msg1_id = db.save_chat_message(user_id, "user", "Hello, do you sell kurtis?")
        msg2_id = db.save_chat_message(user_id, "model", "Yes, we do! We sell wholesale Kurtis.")
        
        self.assertIsNotNone(msg1_id)
        self.assertIsNotNone(msg2_id)
        
        # Retrieve history
        history = db.get_chat_history(user_id, limit=10)
        self.assertEqual(len(history), 2)
        
        # Check order: get_chat_history returns DESC order by default (most recent first)
        self.assertEqual(history[0]["role"], "model")
        self.assertEqual(history[0]["message"], "Yes, we do! We sell wholesale Kurtis.")
        self.assertEqual(history[1]["role"], "user")
        self.assertEqual(history[1]["message"], "Hello, do you sell kurtis?")
        
        # Test clear chat history
        self.assertTrue(db.clear_chat_history(user_id))
        history_after = db.get_chat_history(user_id)
        self.assertEqual(len(history_after), 0)

if __name__ == "__main__":
    unittest.main()
