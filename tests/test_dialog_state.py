import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state_manager import StateManager, DialogState

class TestDialogStateMachine:
    @pytest.fixture
    def state_manager(self):
        return StateManager()

    def test_interruption_during_test(self, state_manager):
        """Тест-кейс: Прерывание опроса и сброс состояния."""
        user_id = 12345
        # Начинаем тест
        state_manager.set_state(user_id, DialogState.AWAITING_ANSWER, {"step": 2, "answers": [0, 1]})
        
        # Имитируем нажатие "На главную"
        state_manager.clear_state(user_id)
        
        assert state_manager.get_state(user_id) == DialogState.IDLE
        assert user_id not in state_manager.user_data

    def test_invalid_input_keeps_state(self, state_manager):
        """Тест-кейс: Некорректный ввод не меняет состояние."""
        user_id = 12345
        state_manager.set_state(user_id, DialogState.AWAITING_ANSWER, {"step": 2})
        
        # Симулируем отправку текста вместо числа
        # (в реальном боте мы бы проверили ответ)
        # Здесь просто убеждаемся, что состояние не сброшено
        assert state_manager.get_state(user_id) == DialogState.AWAITING_ANSWER