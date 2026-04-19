
import os
from dotenv import load_dotenv


load_dotenv()


GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
VK_token = os.getenv ("VK_group_token")


if not GIGACHAT_API_KEY:
    raise ValueError("GIGACHAT_API_KEY не найден в .env файле или переменных окружения")