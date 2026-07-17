import os
import unittest
from unittest.mock import patch
import openpyxl
import db
import excel_importer

class TestExcelImporter(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "test_import_database.db"
        db.DB_PATH = cls.test_db_path
        
    def setUp(self):
        # Clear database and initialize schema
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        db.init_db()
        
        # Create a pre-existing product in DB to test "update" logic
        db.add_category("TestCategory")
        db.add_product(
            name="Existing Product",
            category="TestCategory",
            description="Old Description",
            price=100.0,
            sizes="S",
            photo_file_id="old_photo.jpg"
        )
        
    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
    @patch('vector_db.add_product_to_vector_db')
    def test_excel_import_success(self, mock_add_vector):
        # Generate a temporary Excel spreadsheet
        excel_path = "temp_test_import.xlsx"
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"
        
        # Set headers
        headers = ["Category", "Name", "Description", "Price", "Sizes", "Image_Filename"]
        ws.append(headers)
        
        # Append rows
        # Row 2: A new product
        ws.append(["Kids Wear", "New Frock", "Cute summer frock", 450.0, "22, 24", "frock.jpg"])
        # Row 3: An existing product (should trigger update)
        ws.append(["TestCategory", "Existing Product", "Updated Description", 120.0, "S, M", "new_photo.jpg"])
        # Row 4: Invalid price
        ws.append(["Kids Wear", "Invalid Price Prod", "Description", "NotANumber", "24", ""])
        # Row 5: Missing Category
        ws.append(["", "Missing Cat Prod", "Description", 150.0, "M", ""])
        
        wb.save(excel_path)
        wb.close()
        
        try:
            # Run importer
            results = excel_importer.import_excel_catalog(excel_path)
            
            # Assert counts
            self.assertTrue(results["success"])
            self.assertEqual(results["inserted"], 1) # 'New Frock'
            self.assertEqual(results["updated"], 1)  # 'Existing Product'
            self.assertEqual(results["skipped"], 2)  # Invalid price & missing category
            self.assertEqual(len(results["errors"]), 2)
            
            # Assert DB records
            # Verify new product exists
            new_prod = db.get_product_by_name_and_category("New Frock", "Kids Wear")
            self.assertIsNotNone(new_prod)
            self.assertEqual(new_prod["price"], 450.0)
            self.assertEqual(new_prod["sizes"], "22, 24")
            self.assertEqual(new_prod["photo_file_id"], "frock.jpg")
            
            # Verify existing product was updated
            updated_prod = db.get_product_by_name_and_category("Existing Product", "TestCategory")
            self.assertIsNotNone(updated_prod)
            self.assertEqual(updated_prod["description"], "Updated Description")
            self.assertEqual(updated_prod["price"], 120.0)
            self.assertEqual(updated_prod["sizes"], "S, M")
            self.assertEqual(updated_prod["photo_file_id"], "new_photo.jpg")
            
            # Verify mock vector db sync was called
            self.assertTrue(mock_add_vector.called)
            
        finally:
            if os.path.exists(excel_path):
                os.remove(excel_path)

if __name__ == "__main__":
    unittest.main()
