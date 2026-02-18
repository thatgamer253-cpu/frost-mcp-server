#!/usr/bin/env python3
import sys
import os
import unittest
from digital_ego import DigitalEgo

class TestDigitalEgo(unittest.TestCase):
    def setUp(self):
        # Use a temporary ego file for testing
        self.test_root = "."
        self.ego = DigitalEgo(self.test_root)
        self.ego.competency_map = {} # Reset for test

    def test_record_event(self):
        self.ego.record_event("C++ Fix", False)
        self.assertEqual(self.ego.competency_map["C++ Fix"]["failures"], 1)
        self.ego.record_event("C++ Fix", True)
        self.assertEqual(self.ego.competency_map["C++ Fix"]["successes"], 1)

    def test_limitation_trigger(self):
        # 3 failures should trigger limitation
        for _ in range(3):
            self.ego.record_event("C++ Fix", False)
        
        limitation = self.ego.get_limitation("C++ Fix")
        self.assertIsNotNone(limitation)
        self.assertIn("struggling with C++ Fix", limitation)

    def test_awareness_check(self):
        report = self.ego.awareness_check()
        self.assertIn("vram_ok", report)
        self.assertIn("alerts", report)

if __name__ == "__main__":
    unittest.main()
