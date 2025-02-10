import unittest
from task_decomposition import decompose_task

class TestTaskDecomposition(unittest.TestCase):
    def test_simple_strategy_level1(self):
        # Test simple strategy with level 1 should split by period
        request = "Plan a trip. Book flight. Enjoy the journey."
        result = decompose_task(request)
        expected = ["Plan a trip", "Book flight", "Enjoy the journey"]
        self.assertEqual(result, expected)

    def test_simple_strategy_level2(self):
        # Test simple strategy with level 2 should duplicate steps with nesting
        request = "Plan a trip. Book flight. Enjoy the journey."
        result = decompose_task(request, level=2)
        expected = [
            "Step 1: Plan a trip", "Step 2: Plan a trip",
            "Step 1: Book flight", "Step 2: Book flight",
            "Step 1: Enjoy the journey", "Step 2: Enjoy the journey"
        ]
        self.assertEqual(result, expected)

    def test_keyword_strategy_found(self):
        # Test keyword strategy: keywords present
        request = "Plan your day, then research the topic and eventually buy the new gadget."
        result = decompose_task(request, extra_params={'decomposition_strategy': 'keyword'})
        # Expect subtasks to mention keywords: 'plan', 'research', and 'buy'
        expected_keywords = ['plan', 'research', 'buy']
        for keyword in expected_keywords:
            self.assertTrue(any(keyword in sub.lower() for sub in result), f"Keyword '{keyword}' not found in subtasks {result}")

    def test_keyword_strategy_not_found(self):
        # Test keyword strategy: no predefined keywords found, fallback to full request
        request = "This is a random string without known keywords."
        result = decompose_task(request, extra_params={'decomposition_strategy': 'keyword'})
        self.assertEqual(result, [request.strip()])

    def test_default_strategy(self):
        # Test default strategy for unknown decomposition strategy
        request = "Another complex task that does not require splitting."
        result = decompose_task(request, extra_params={'decomposition_strategy': 'unknown_strategy'})
        self.assertEqual(result, [request.strip()])

if __name__ == '__main__':
    unittest.main()
