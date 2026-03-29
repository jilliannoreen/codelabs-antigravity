import unittest
from unittest.mock import MagicMock
from order import (
    Order, 
    InventoryService, 
    PaymentGateway, 
    InventoryShortageError, 
    PaymentFailedError, 
    InvalidOrderError
)

class TestOrder(unittest.TestCase):
    def setUp(self):
        # Create mock implementations of our external dependencies
        self.mock_inventory = MagicMock(spec=InventoryService)
        self.mock_payment = MagicMock(spec=PaymentGateway)
        self.order = Order(self.mock_inventory, self.mock_payment, "test@example.com")

    def test_add_item_valid(self):
        self.order.add_item("prod_1", 10.0, 2)
        self.assertEqual(self.order.items["prod_1"]["qty"], 2)
        self.assertEqual(self.order.items["prod_1"]["price"], 10.0)

    def test_add_item_invalid_price(self):
        with self.assertRaises(ValueError):
            self.order.add_item("prod_1", -5.0, 1)
            
    def test_add_item_invalid_qty(self):
        with self.assertRaises(ValueError):
            self.order.add_item("prod_1", 10.0, 0)

    def test_remove_item(self):
        self.order.add_item("prod_1", 10.0, 1)
        self.order.remove_item("prod_1")
        self.assertNotIn("prod_1", self.order.items)

    def test_total_price(self):
        self.order.add_item("prod_1", 10.0, 2)
        self.order.add_item("prod_2", 15.0, 1)
        self.assertEqual(self.order.total_price, 35.0)

    def test_apply_discount_vip(self):
        self.order.is_vip = True
        self.order.add_item("prod_1", 100.0, 1)
        self.assertEqual(self.order.apply_discount(), 80.0) # 20% off

    def test_apply_discount_over_100(self):
        self.order.add_item("prod_1", 110.0, 1)
        self.assertEqual(self.order.apply_discount(), 99.0) # 10% off

    def test_apply_discount_no_discount(self):
        self.order.add_item("prod_1", 50.0, 1)
        self.assertEqual(self.order.apply_discount(), 50.0) # No discount

    def test_checkout_empty_cart(self):
        with self.assertRaises(InvalidOrderError):
            self.order.checkout()

    def test_checkout_inventory_shortage(self):
        self.order.add_item("prod_1", 10.0, 5)
        # Mock the inventory to report only 2 items in stock
        self.mock_inventory.get_stock.return_value = 2 
        
        with self.assertRaises(InventoryShortageError):
            self.order.checkout()

    def test_checkout_payment_failed(self):
        self.order.add_item("prod_1", 10.0, 1)
        self.mock_inventory.get_stock.return_value = 10
        # Mock the payment gateway to fail the transaction
        self.mock_payment.charge.return_value = False
        
        with self.assertRaises(PaymentFailedError):
            self.order.checkout()

    def test_checkout_payment_exception(self):
        self.order.add_item("prod_1", 10.0, 1)
        self.mock_inventory.get_stock.return_value = 10
        # Mock the payment gateway to throw a network error
        self.mock_payment.charge.side_effect = Exception("Network timeout")

        with self.assertRaises(PaymentFailedError):
            self.order.checkout()

    def test_checkout_success(self):
        self.order.add_item("prod_1", 10.0, 2)
        
        # Configure the mocks for a successful path
        self.mock_inventory.get_stock.return_value = 5
        self.mock_payment.charge.return_value = True

        # Perform the checkout
        result = self.order.checkout()

        # Assert correct return format and logic
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["charged_amount"], 20.0)
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, "COMPLETED")
        
        # Verify the external services were called exactly as expected
        self.mock_inventory.get_stock.assert_called_once_with("prod_1")
        self.mock_payment.charge.assert_called_once_with(20.0, "USD")
        self.mock_inventory.decrement_stock.assert_called_once_with("prod_1", 2)

if __name__ == '__main__':
    unittest.main()
