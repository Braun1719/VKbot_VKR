# gigachat_vk_service.py
import json
import logging
import re
from typing import Dict, Optional, List

from gigachat import GigaChat
from config import GIGACHAT_API_KEY

logger = logging.getLogger(__name__)

class GigaChatVKService:
    """Сервис для работы с GigaChat в ВК боте"""

    # Список запрещённых тем (регулярные выражения)
    FORBIDDEN_TOPICS = [
        # порнография, эротика и темы сексуального характера
        r'\bпорн[оа]?\w*', r'\bэротик\w*', r'\bсекс\w*', r'\bинтим\w*',
        r'\bnude\w*', r'\bporn\w*', r'\berotic\w*', r'\bsex\w*',
        # пропаганда употребления алкогольных, наркотических и табачных веществ
        r'\bнаркотик\w*', r'\bнаркот\w*', r'\bалкогол\w*', r'\bспиртн\w*',
        r'\bтабак\w*', r'\bсигарет\w*', r'\bкурени\w*', r'\bdrug\w*',
        # политика, предвыборная агитация и обсуждение представителей власти
        r'\bполитик\w*', r'\bпрезидент\w*', r'\bвыбор\w*', r'\bголосовани\w*',
        r'\bпутин\w*', r'\bнавальн\w*', r'\bкремл\w*', r'\bдум\w*',
        # темы экстремистского и террористического характера
        r'\bэкстремизм\w*', r'\bтерроризм\w*', r'\bвзрыв\w*', r'\bбомб\w*',
        r'\bтеррор\w*', r'\bэкстремист\w*',
        # призывы к насилию, убийствам и самоубийствам
        r'\bубийств\w*', r'\bсамоубийств\w*', r'\bсуицид\w*', r'\bнасили\w*',
        r'\bубит\w*', r'\bсмерт\w*\s+призыв\w*',
        # призывы к жестокому обращению с животными
        r'\bжесток\w*\s+животн\w*', r'\bубит\w*\s+животн\w*', r'\bизби\w*\s+животн\w*',
        # призывы к нарушению законов (разжиганию военных конфликтов, пропаганде криминальных структур)
        r'\bкриминал\w*', r'\bпреступлени\w*', r'\bграб\w*', r'\bкраж\w*', r'\bвор\w*',
        r'\bнарушени\w*\s+закон\w*', r'\bразжигани\w*\s+воен\w*', r'\bразжигани\w*\s+конфликт\w*',
        # изготовление наркотических веществ и их аналогов, взрывчатых веществ и иного оружия
        r'\bизготовлени\w*\s+наркотик\w*', r'\bсинтез\w*\s+наркотик\w*', r'\bвзрывчатк\w*',
        r'\bоружи\w*', r'\bогнестрел\w*', r'\bвзрыв\w*\s+устройств\w*',
    ]

    def __init__(self):
        try:
            self.client = GigaChat(
                credentials=GIGACHAT_API_KEY,
                verify_ssl_certs=False,
                timeout=60,
                model="GigaChat"  # указываем модель
            )
            self.dialog_history = {}
            logger.info("GigaChat сервис успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации GigaChat: {e}")
            self.client = None

    def _is_text_allowed(self, text: str) -> bool:
        """
        Проверяет текст на наличие запрещённых тем.
        Возвращает True, если текст допустим, иначе False.
        """
        if not text:
            return True

        text_lower = text.lower()
        for pattern in self.FORBIDDEN_TOPICS:
            if re.search(pattern, text_lower):
                logger.warning(f"Обнаружена запрещённая тема: pattern={pattern}, text={text[:100]}")
                return False
        return True

    async def analyze_emotional_state(self, user_description: str, user_id: int) -> Dict:
        """
        Анализ эмоционального состояния IT-специалиста
        """
        # Проверка этики
        if not self._is_text_allowed(user_description):
            await self.reset_dialog(user_id)
            return self._get_ethics_violation_response()

        if not self.client:
            return self._get_fallback_analysis()

        prompt = self._create_analysis_prompt(user_description)

        try:
            # Отправляем запрос на генерацию
            response = self.client.chat(prompt)
            content = response.choices[0].message.content

            # Парсим JSON из ответа
            analysis_result = self._parse_analysis_response(content)

            # Сохраняем в историю
            self.dialog_history[user_id] = {
                'analysis': analysis_result,
                'last_analysis': user_description,
                'messages': [
                    {"role": "user", "content": user_description},
                    {"role": "assistant", "content": json.dumps(analysis_result, ensure_ascii=False)}
                ]
            }

            return analysis_result

        except Exception as e:
            logger.error(f"Ошибка при анализе состояния: {e}")
            return self._get_fallback_analysis()

    async def continue_dialog(self, user_message: str, user_id: int) -> str:
        """
        Продолжение диалога в разговорном стиле
        """
        # Проверка этики
        if not self._is_text_allowed(user_message):
            await self.reset_dialog(user_id)
            return self._get_ethics_violation_message()

        if not self.client:
            return "Извините, сервис ИИ временно недоступен. Попробуйте позже."

        history = self.dialog_history.get(user_id, {'messages': []})
        prompt = self._create_dialog_prompt(user_message, history)

        try:
            response = self.client.chat(prompt)
            answer = response.choices[0].message.content

            # Сохраняем в историю
            history['messages'].append({"role": "user", "content": user_message})
            history['messages'].append({"role": "assistant", "content": answer})

            if len(history['messages']) > 10:
                history['messages'] = history['messages'][-10:]

            self.dialog_history[user_id] = history

            return answer

        except Exception as e:
            logger.error(f"Ошибка при диалоге: {e}")
            return "Извините, произошла ошибка. Пожалуйста, попробуйте еще раз."

    async def reset_dialog(self, user_id: int):
        """Сброс истории диалога"""
        if user_id in self.dialog_history:
            del self.dialog_history[user_id]

    def _create_analysis_prompt(self, user_description: str) -> str:
        """Создание промпта для анализа"""
        return f"""
        Ты - профессиональный психолог, специализирующийся на эмоциональном выгорании IT-специалистов.
        
        Проанализируй его описание и дай структурированный ответ.
        
        Описание пользователя:
        {user_description}
        
        Твой ответ должен быть в формате JSON только если он не содержит запрещенные ТЕМЫ или СЛОВА:
        {{
            "general_assessment": "краткая общая оценка состояния (2-3 предложения)",
            "symptoms": ["симптом 1", "симптом 2", "симптом 3", "симптом 4", "симптом 5"],
            "burnout_stages": {{
                "tension": "низкий/средний/высокий",
                "resistance": "низкий/средний/высокий",
                "exhaustion": "низкий/средний/высокий",
                "deformation": "низкий/средний/высокий"
            }},
            "recommendations": ["рекомендация 1", "рекомендация 2", "рекомендация 3", "рекомендация 4"],
            "anxiety_level": "низкий/средний/высокий",
            "next_steps": "конкретный совет по дальнейшим действиям"
        }}
        
        """

    def _create_dialog_prompt(self, user_message: str, history: Dict) -> str:
        """Создание промпта для диалога"""
        context = ""

        if history.get('analysis'):
            context += f"Ранее был проведен анализ состояния пользователя. "
            analysis = history['analysis']
            context += f"Основные симптомы: {', '.join(analysis.get('symptoms', [])[:3])}. "
            context += f"Уровень тревожности: {analysis.get('anxiety_level', 'не указан')}.\n\n"

        if history.get('messages'):
            context += "История диалога:\n"
            for msg in history['messages'][-4:]:
                role = "Пользователь" if msg['role'] == 'user' else "Ты"
                context += f"{role}: {msg['content'][:100]}...\n"
            context += "\n"

        return f"""
        Ты - дружелюбный психолог-консультант для IT-специалистов. Общайся просто и по-человечески.
        
        {context}
        
        Текущее сообщение пользователя:
        {user_message}
        
        Правила общения:
        - Будь дружелюбным и поддерживающим
        - Используй простой разговорный язык
        - Отвечай кратко, но по существу
        - Можешь использовать эмодзи для эмоциональности
        - Задавай уточняющие вопросы, если нужно
        - Избегай запрещенных тем
        
        Твой ответ:
        """

    def _parse_analysis_response(self, content: str) -> Dict:
        """Парсинг JSON из ответа"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа: {e}")
        return self._get_fallback_analysis()

    def _get_fallback_analysis(self) -> Dict:
        """Запасной вариант ответа"""
        return {
            "general_assessment": "На основе вашего описания можно предположить начальные признаки эмоционального выгорания. Рекомендуется обратить внимание на режим работы и отдыха.",
            "symptoms": [
                "Повышенная утомляемость",
                "Снижение интереса к работе",
                "Трудности с концентрацией",
                "Раздражительность",
                "Нарушение сна"
            ],
            "burnout_stages": {
                "tension": "средний",
                "resistance": "низкий",
                "exhaustion": "низкий",
                "deformation": "низкий"
            },
            "recommendations": [
                "Делайте регулярные перерывы в работе",
                "Установите четкие границы рабочего времени",
                "Занимайтесь физической активностью",
                "Обсудите нагрузку с руководителем"
            ],
            "anxiety_level": "средний",
            "next_steps": "Пройдите стандартные тесты для более точной диагностики. При сохранении симптомов обратитесь к психологу."
        }

    def _get_ethics_violation_message(self) -> str:
        """Сообщение при нарушении этических норм (для диалога)"""
        return (
            "❌ **Извините, я не могу ответить на этот запрос.**\n\n"
            "Моя задача — помогать с вопросами, связанными с эмоциональным состоянием, "
            "профессиональным выгоранием и психологическим здоровьем IT-специалистов. "
            "Пожалуйста, задайте вопрос в рамках этих тем.\n\n"
            "Вы можете:\n"
            "• Описать своё самочувствие\n"
            "• Спросить о методах борьбы со стрессом\n"
            "• Поделиться рабочими переживаниями\n\n"
            "Давайте вернёмся к полезному разговору 😊"
        )

    def _get_ethics_violation_response(self) -> Dict:
        """Словарь-ответ при нарушении этических норм (для анализа)"""
        return {
            "ethics_violation": True,  # флаг для обработчика
            "general_assessment": "Запрос содержит недопустимую тему. Пожалуйста, опишите своё эмоциональное состояние без использования запрещённых тем.",
            "symptoms": [],
            "burnout_stages": {},
            "recommendations": ["Пожалуйста, избегайте тем, связанных с насилием, наркотиками, политикой и другими запрещёнными категориями."],
            "anxiety_level": "не определен",
            "next_steps": "Попробуйте описать своё самочувствие в корректной форме."
        }
        
    


# Создаем экземпляр для использования в боте
gigachat_vk = GigaChatVKService()