from typing import Dict, Optional

class DialogState:
    IDLE = "idle"
    AWAITING_ANSWER = "awaiting_answer"
    AI_WAITING_DESCRIPTION = "ai_waiting_description"
    AI_IN_CONVERSATION = "ai_in_conversation"

class StateManager:
    def __init__(self):
        self.user_states: Dict[int, str] = {}
        self.user_data: Dict[int, Dict] = {}

    def set_state(self, user_id: int, state: str, data: Optional[Dict] = None):
        self.user_states[user_id] = state
        if data:
            self.user_data[user_id] = data

    def get_state(self, user_id: int) -> str:
        return self.user_states.get(user_id, DialogState.IDLE)

    def clear_state(self, user_id: int):
        self.user_states.pop(user_id, None)
        self.user_data.pop(user_id, None)