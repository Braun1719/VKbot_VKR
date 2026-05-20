import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import calculate_quick_result, calculate_maslach_result, calculate_boyko_result, calculate_heck_hess_result

class TestBurnoutScoring:
    """Группа тестов для проверки корректности подсчета баллов выгорания."""

    def test_quick_test_low_risk(self):
        """Тест-кейс: Проверка нижней границы значений быстрого теста."""
        answers = [0] * 10
        result_text = calculate_quick_result(answers)
        
        assert "низкий уровень выгорания" in result_text
        assert "0%" in result_text

    def test_quick_test_high_risk(self):
        """Тест-кейс: Проверка верхней границы значений."""
        answers = [5] * 10
        result_text = calculate_quick_result(answers)
        
        assert "высокий уровень выгорания" in result_text
        assert "100%" in result_text

    def test_maslach_edge_boundaries(self):
        """Тест-кейс: Граничные значения опросника Маслач."""
 
        answers = [5] * 22  
        result_text = calculate_maslach_result(answers)
        
        assert "Эмоциональное истощение:** 45 из 45" in result_text
        assert "Зона риска выгорания обнаружена" in result_text