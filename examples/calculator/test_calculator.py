import unittest
import calculator


class CalculatorTests(unittest.TestCase):
    def test_existing_operations(self):
        self.assertEqual(calculator.add(2, 3), 5)
        self.assertEqual(calculator.subtract(2, 3), -1)

    def test_multiply(self):
        self.assertEqual(calculator.multiply(6, 7), 42)

    def test_multiply_edge_cases(self):
        self.assertEqual(calculator.multiply(-3, 4), -12)
        self.assertEqual(calculator.multiply(0, 9), 0)
        self.assertAlmostEqual(calculator.multiply(0.5, 3), 1.5)
