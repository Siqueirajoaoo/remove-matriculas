"""Testes dos padrões de matrícula (não baixam modelos de OCR nem usam PyTorch).
Precisam só das dependências de requirements.txt instaladas.

Rodar, a partir da pasta do projeto:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from remover.patterns import is_registration, normalize  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_uppercases_and_strips_spaces(self):
        self.assertEqual(normalize(" pt - abc. "), "PT-ABC")

    def test_converts_typographic_dashes(self):
        self.assertEqual(normalize("G–ABCD"), "G-ABCD")  # en dash
        self.assertEqual(normalize("G−ABCD"), "G-ABCD")  # minus sign


class RegistrationTests(unittest.TestCase):
    def test_accepts_common_registrations(self):
        for text in ["PT-ABC", "pp-xyz", "PR-ABC", "PT - ABC", "G-ABCD", "D-EABC",
                     "9M-ABC", "VH-XYZ", "EC-MXY", "N12345", "N123AB", "N1A"]:
            with self.subTest(text=text):
                self.assertTrue(is_registration(text))

    def test_rejects_aircraft_models_and_words(self):
        for text in ["F-16", "A-320", "B-52", "NO-GO", "HELLO", "PT", "", "   ", "N0123", "12345"]:
            with self.subTest(text=text):
                self.assertFalse(is_registration(text))


if __name__ == "__main__":
    unittest.main()
