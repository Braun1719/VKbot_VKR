import asyncio
import logging
import re
import json
import os
from typing import Dict, List
from datetime import datetime
from collections import defaultdict

from vkbottle import Bot
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import BotLabeler, Message
from config import VK_token


from gigachat_vk_service import gigachat_vk


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = VK_token


labeler = BotLabeler()
labeler.vbml_ignore_case = True


bot = Bot(token=TOKEN, labeler=labeler)

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
user_data = {}
user_statistics = {}  # Хранилище статистики пользователей

# Файл для сохранения статистики
STATS_FILE = "user_statistics.json"

# Загрузка статистики из файла
def load_statistics():
    """Загружает статистику из файла"""
    global user_statistics
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                user_statistics = json.load(f)
            logger.info(f"Статистика загружена для {len(user_statistics)} пользователей")
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            user_statistics = {}
    else:
        user_statistics = {}

# Сохранение статистики в файл
def save_statistics():
    """Сохраняет статистику в файл"""
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_statistics, f, ensure_ascii=False, indent=2)
        logger.info("Статистика сохранена")
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")

# Состояния для ИИ-теста
class AITestStates:
    WAITING_DESCRIPTION = "ai_waiting_description"
    IN_CONVERSATION = "ai_in_conversation"

# Функция для очистки текста от префикса сообщества
def clean_text(text: str) -> str:
    """Очищает текст от префикса [club...|@...]"""
    if not text:
        return text
    cleaned = re.sub(r'^\[club\d+\|@club\d+\]\s*', '', text)
    return cleaned 

# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard():
    """Главное меню бота"""
    keyboard = Keyboard(one_time=False)
    # Быстрый тест - зеленый
    keyboard.add(Text("⚡ Быстрый тест"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # Опросник Маслач - синий
    keyboard.add(Text("📊 Опросник Маслач"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # Тест Бойко - синий
    keyboard.add(Text("🧠 Тест Бойко"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # Тест Хека-Хесса - синий
    keyboard.add(Text("🏥 Тест Хека-Хесса"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # ИИ-диагностика - зеленый
    keyboard.add(Text("🤖 ИИ-диагностика"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    # Статистика - фиолетовый (используем PRIMARY, но можно выделить)
    keyboard.add(Text("📊 Моя статистика"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    # Помощь - серый
    keyboard.add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
    return keyboard

def get_answer_keyboard():
    """Клавиатура для ответов (оценки от 0 до 5)"""
    keyboard = Keyboard(one_time=True)
    keyboard.add(Text("0"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("1"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("2"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("3"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("4"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("5"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("◀ На главную"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_back_keyboard():
    """Клавиатура с кнопкой возврата"""
    keyboard = Keyboard(one_time=False)
    keyboard.add(Text("◀ На главную"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_ai_cancel_keyboard():
    """Клавиатура для отмены ИИ-теста"""
    keyboard = Keyboard(one_time=True)
    keyboard.add(Text("❌ Отменить ИИ-тест"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_ai_dialog_keyboard():
    """Клавиатура для режима ИИ-диалога"""
    keyboard = Keyboard(one_time=False)
    keyboard.add(Text("🏠 Главное меню"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

# ==================== ФУНКЦИИ СТАТИСТИКИ ====================

def update_statistics(user_id: int, test_type: str, result_data: Dict):
    """Обновляет статистику пользователя"""
    user_id_str = str(user_id)
    
    if user_id_str not in user_statistics:
        user_statistics[user_id_str] = {
            "first_test_date": datetime.now().isoformat(),
            "tests": [],
            "total_tests": 0,
            "last_test_date": None
        }
    
    # Добавляем результат теста
    test_record = {
        "test_type": test_type,
        "date": datetime.now().isoformat(),
        "result": result_data
    }
    
    user_statistics[user_id_str]["tests"].append(test_record)
    user_statistics[user_id_str]["total_tests"] += 1
    user_statistics[user_id_str]["last_test_date"] = datetime.now().isoformat()
    
    # Ограничиваем историю последними 20 тестами
    if len(user_statistics[user_id_str]["tests"]) > 20:
        user_statistics[user_id_str]["tests"] = user_statistics[user_id_str]["tests"][-20:]
    
    save_statistics()

def get_statistics_text(user_id: int) -> str:
    """Формирует текст статистики для пользователя"""
    user_id_str = str(user_id)
    
    if user_id_str not in user_statistics or not user_statistics[user_id_str]["tests"]:
        return (
            "📊 **Ваша статистика**\n\n"
            "У вас пока нет пройденных тестов.\n\n"
            "Пройдите любой тест из главного меню, "
            "чтобы начать отслеживать свою статистику!"
        )
    
    stats = user_statistics[user_id_str]
    tests = stats["tests"]
    total_tests = stats["total_tests"]
    
    # Подсчет количества тестов по типам
    test_counts = defaultdict(int)
    for test in tests:
        test_counts[test["test_type"]] += 1
    
    # Получаем последний тест
    last_test = tests[-1]
    last_test_date = datetime.fromisoformat(last_test["date"]).strftime("%d.%m.%Y %H:%M")
    
    # Получаем первый тест
    first_test_date = datetime.fromisoformat(stats["first_test_date"]).strftime("%d.%m.%Y")
    
    # Анализ динамики (если есть больше одного теста одного типа)
    dynamics_text = ""
    for test_type, count in test_counts.items():
        if count > 1:
            # Находим результаты этого типа тестов
            type_results = [t for t in tests if t["test_type"] == test_type]
            if len(type_results) >= 2:
                dynamics_text += f"\n**{get_test_type_name(test_type)}:** {len(type_results)} раза"
    
    # Формируем текст статистики
    result = (
        f"📊 **Ваша статистика**\n\n"
        f"📅 **Первый тест:** {first_test_date}\n"
        f"📝 **Всего пройдено:** {total_tests} тестов\n"
        f"🕐 **Последний тест:** {last_test_date}\n\n"
        f"**📈 Распределение по типам:**\n"
    )
    
    # Добавляем распределение тестов
    test_names = {
        "quick": "⚡ Быстрый тест",
        "maslach": "📊 Опросник Маслач",
        "boyko": "🧠 Тест Бойко",
        "heck_hess": "🏥 Тест Хека-Хесса",
        "ai_experimental": "🤖 ИИ-диагностика"
    }
    
    for test_type, count in test_counts.items():
        name = test_names.get(test_type, test_type)
        result += f"• {name}: {count} раз(а)\n"
    
    if dynamics_text:
        result += f"\n**📊 Динамика:**{dynamics_text}\n"
    
    result += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Совет:** Регулярно проходите тесты, "
        "чтобы отслеживать изменения своего состояния!"
    )
    
    return result

def get_test_type_name(test_type: str) -> str:
    """Возвращает название теста по его типу"""
    names = {
        "quick": "Быстрый тест",
        "maslach": "Опросник Маслач",
        "boyko": "Тест Бойко",
        "heck_hess": "Тест Хека-Хесса",
        "ai_experimental": "ИИ-диагностика"
    }
    return names.get(test_type, test_type)

def extract_result_summary(test_type: str, answers: List[int]) -> Dict:
    """Извлекает краткую информацию о результате теста"""
    if test_type == "quick":
        total = sum(answers)
        max_score = len(answers) * 5
        percent = (total / max_score) * 100
        
        if percent < 30:
            level = "низкий"
        elif percent < 60:
            level = "средний"
        else:
            level = "высокий"
        
        return {
            "level": level,
            "percent": round(percent, 1),
            "score": total
        }
    
    elif test_type == "maslach":
        ee_questions = [0,1,2,5,7,12,13,15,19]
        ee_score = sum(answers[i] for i in ee_questions)
        
        if ee_score > 27:
            level = "высокий"
        elif ee_score > 20:
            level = "средний"
        else:
            level = "низкий"
        
        return {
            "level": level,
            "ee_score": ee_score,
            "key_metric": "Эмоциональное истощение"
        }
    
    elif test_type == "boyko":
        phase1 = sum(answers[0:3])
        phase2 = sum(answers[3:6])
        phase3 = sum(answers[6:9])
        phase4 = sum(answers[9:12])
        
        max_phase = max(phase1, phase2, phase3, phase4)
        if max_phase > 10:
            level = "высокий"
        elif max_phase > 7:
            level = "средний"
        else:
            level = "низкий"
        
        return {
            "level": level,
            "max_phase": max_phase
        }
    
    elif test_type == "heck_hess":
        total = sum(answers)
        
        if total <= 15:
            level = "низкий"
        elif total <= 25:
            level = "средний"
        else:
            level = "высокий"
        
        return {
            "level": level,
            "score": total
        }
    
    return {"level": "не определен"}

# ==================== ВОПРОСЫ ТЕСТОВ ====================

# 1. Быстрый тест (10 вопросов) - экспресс-оценка
QUICK_TEST = [
    "Я чувствую себя эмоционально опустошённым после рабочего дня.",
    "Мне сложно найти в себе силы для общения с коллегами и пользователями.",
    "Я стал более раздражительным и нетерпеливым на работе.",
    "Мне кажется, что моя работа не приносит пользы и не ценится.",
    "Я испытываю трудности с концентрацией внимания на задачах.",
    "Я часто задерживаюсь на работе, чтобы доделать незавершённые дела.",
    "Мне снятся рабочие проблемы или я думаю о работе в выходные.",
    "Я потерял интерес к профессиональному развитию и новым технологиям.",
    "Физическая усталость стала моим постоянным спутником.",
    "Я замечаю, что стал хуже справляться с задачами, которые раньше делал легко."
]

# 2. Опросник Маслач (классическая методика, 22 вопроса)
MASLACH_TEST = [
    "Я чувствую себя эмоционально опустошённым из-за своей работы.",
    "К концу рабочего дня я чувствую себя как выжатый лимон.",
    "Каждое утро я испытываю усталость перед тем, как идти на работу.",
    "Я легко понимаю, что чувствуют мои коллеги и пользователи.",
    "Я чувствую, что отношусь к некоторым людям на работе бездушно, как к объектам.",
    "Работа с людьми целый день действительно утомляет меня.",
    "Я успешно справляюсь с задачами, которые ставят передо мной пользователи.",
    "Я чувствую себя 'выгоревшим' от своей работы.",
    "Я чувствую, что моя работа положительно влияет на окружающих.",
    "Я стал более бесчувственным к людям с момента начала работы.",
    "Я беспокоюсь, что моя работа ожесточает меня.",
    "У меня много сил и энергии для работы.",
    "Я чувствую разочарование в своей работе.",
    "Я работаю слишком много и интенсивно.",
    "Меня не особо волнует то, что происходит с некоторыми людьми на работе.",
    "Работа в прямом контакте с людьми вызывает у меня стресс.",
    "Я легко могу создать спокойную и доброжелательную атмосферу.",
    "Я чувствую воодушевление после близкой работы с коллегами или пользователями.",
    "Благодаря своей работе я сделал много полезного и важного.",
    "Я чувствую себя в тупике на своей работе.",
    "Я хорошо справляюсь с эмоциональными проблемами на работе.",
    "Я чувствую, что на работе я нахожусь на пределе своих возможностей."
]

# 3. Тест Бойко (анализ 4 фаз выгорания, 12 вопросов)
BOYKO_TEST = [
    "Организационные неурядицы на работе постоянно заставляют нервничать.",
    "Я допускаю ошибки в работе, которых раньше не было.",
    "Мне трудно сосредоточиться на выполнении рабочей задачи.",
    "Меня раздражают пользователи, которые задают одни и те же вопросы.",
    "Коллеги выводят меня из себя своим поведением.",
    "Я чувствую себя некомпетентным в некоторых рабочих вопросах.",
    "Мне не хочется общаться ни с коллегами, ни с пользователями.",
    "Я испытываю физический дискомфорт (головная боль, напряжение в спине).",
    "Моя работа перестала приносить мне удовлетворение.",
    "Я стал цинично относиться к результатам своего труда.",
    "Я чувствую, что мои профессиональные навыки устаревают.",
    "Мне кажется, что руководство не ценит мой вклад в работу."
]

# 4. Тест Хека-Хесса (оценка депрессивных симптомов, 10 вопросов)
HECK_HESS_TEST = [
    "У меня снизился аппетит или, наоборот, я начал больше есть.",
    "Мне трудно заснуть или я просыпаюсь ночью и не могу уснуть.",
    "Я потерял интерес к хобби и занятиям, которые раньше приносили удовольствие.",
    "Я чувствую постоянную усталость и нехватку энергии.",
    "Я испытываю чувство вины или бесполезности своей работы.",
    "Мне трудно принимать решения даже в простых рабочих вопросах.",
    "Я замечаю, что стал медленнее соображать и реагировать.",
    "Я чувствую тревогу и беспокойство без видимой причины.",
    "Мои мысли часто возвращаются к работе, и я не могу переключиться.",
    "У меня появляются мысли о том, чтобы сменить профессию или уволиться."
]

# ==================== МЕТОДЫ РАСЧЁТА РЕЗУЛЬТАТОВ ====================

def calculate_quick_result(answers: List[int]) -> str:
    """Расчёт результата быстрого теста"""
    total = sum(answers)
    max_score = len(answers) * 5
    percent = (total / max_score) * 100
    
    if percent < 30:
        return (
            "🌟 **Результат быстрого теста: низкий уровень выгорания**\n\n"
            f"Ваш показатель: {percent:.0f}%\n\n"
            "Вы хорошо справляетесь с профессиональными нагрузками. "
            "Продолжайте следить за своим состоянием и не забывайте о регулярном отдыхе.\n\n"
            "✅ **Рекомендация:** Поддерживайте текущий баланс между работой и личной жизнью."
        )
    elif percent < 60:
        return (
            "⚠️ **Результат быстрого теста: средний уровень выгорания**\n\n"
            f"Ваш показатель: {percent:.0f}%\n\n"
            "У вас есть признаки профессионального выгорания. "
            "Важно обратить внимание на режим работы и отдыха.\n\n"
            "✅ **Рекомендация:**\n"
            "• Делайте регулярные перерывы в работе\n"
            "• Установите чёткие границы рабочего времени\n"
            "• Найдите хобби, не связанное с IT"
        )
    else:
        return (
            "🔥 **Результат быстрого теста: высокий уровень выгорания**\n\n"
            f"Ваш показатель: {percent:.0f}%\n\n"
            "Вы находитесь в зоне риска профессионального выгорания. "
            "Рекомендуется обратиться к психологу или сделать паузу в работе.\n\n"
            "✅ **Рекомендация:**\n"
            "• Рассмотрите возможность отпуска\n"
            "• Обратитесь к специалисту по профессиональному выгоранию\n"
            "• Пересмотрите рабочую нагрузку с руководителем"
        )

def calculate_maslach_result(answers: List[int]) -> str:
    """Расчёт результата опросника Маслач"""
    ee_questions = [0,1,2,5,7,12,13,15,19]
    ee_score = sum(answers[i] for i in ee_questions)
    
    dp_questions = [4,9,10,14,21]
    dp_score = sum(answers[i] for i in dp_questions)
    
    pa_questions = [3,6,8,11,16,17,18,20]
    pa_score = sum(answers[i] for i in pa_questions)
    pa_score_reversed = (len(pa_questions) * 5) - pa_score
    
    result_text = (
        "📋 **Результаты опросника Маслач:**\n\n"
        f"**Эмоциональное истощение:** {ee_score} из 45\n"
        f"**Деперсонализация (цинизм):** {dp_score} из 35\n"
        f"**Редукция достижений:** {pa_score_reversed} из 40\n\n"
    )
    
    if ee_score > 27 or dp_score > 13 or pa_score_reversed > 30:
        result_text += (
            "⚠️ **Зона риска выгорания обнаружена!**\n\n"
            "Рекомендуется:\n"
            "• Снизить рабочую нагрузку\n"
            "• Внедрить практики осознанности и релаксации\n"
            "• Обсудить ситуацию с руководителем или психологом"
        )
    else:
        result_text += (
            "✅ **Значения в норме.**\n\n"
            "Продолжайте следить за своим состоянием и поддерживать "
            "здоровый баланс между работой и отдыхом."
        )
    
    return result_text

def calculate_boyko_result(answers: List[int]) -> str:
    """Расчёт результата теста Бойко (4 фазы выгорания)"""
    phase1 = sum(answers[0:3])
    phase2 = sum(answers[3:6])
    phase3 = sum(answers[6:9])
    phase4 = sum(answers[9:12])
    
    result_text = (
        "🧠 **Результаты теста Бойко (4 фазы выгорания):**\n\n"
        f"🔸 **Фаза напряжения:** {phase1} из 15\n"
        f"🔸 **Фаза резистенции:** {phase2} из 15\n"
        f"🔸 **Фаза истощения:** {phase3} из 15\n"
        f"🔸 **Психосоматическая фаза:** {phase4} из 15\n\n"
    )
    
    warnings = []
    if phase1 > 10:
        warnings.append("• Высокий уровень напряжения — необходима разгрузка")
    if phase2 > 10:
        warnings.append("• Развивается защитная реакция — вы стали более циничны")
    if phase3 > 10:
        warnings.append("• Эмоциональное истощение — срочно нужен отдых")
    if phase4 > 10:
        warnings.append("• Психосоматические проявления — рекомендуется обратиться к врачу")
    
    if warnings:
        result_text += "⚠️ **Выявленные проблемы:**\n" + "\n".join(warnings) + "\n\n"
        result_text += "✅ **Рекомендация:** Рассмотрите возможность отпуска и обратитесь к специалисту."
    else:
        result_text += "✅ **Показатели в норме.** Продолжайте следить за балансом работы и отдыха."
    
    return result_text

def calculate_heck_hess_result(answers: List[int]) -> str:
    """Расчёт результата теста Хека-Хесса"""
    total = sum(answers)
    
    result_text = "🏥 **Результаты теста Хека-Хесса:**\n\n"
    
    if total <= 15:
        result_text += f"**Суммарный балл: {total}** (низкий уровень)\n\n"
        result_text += "✅ Депрессивные симптомы не выражены. Состояние стабильное."
    elif total <= 25:
        result_text += f"**Суммарный балл: {total}** (средний уровень)\n\n"
        result_text += (
            "⚠️ Обнаружены отдельные депрессивные симптомы.\n\n"
            "✅ **Рекомендация:**\n"
            "• Увеличьте физическую активность\n"
            "• Общайтесь с близкими людьми\n"
            "• При ухудшении обратитесь к психологу"
        )
    else:
        result_text += f"**Суммарный балл: {total}** (высокий уровень)\n\n"
        result_text += (
            "🔥 Высокий уровень депрессивных симптомов!\n\n"
            "✅ **Рекомендация:**\n"
            "• **Срочно обратитесь к психологу или психотерапевту**\n"
            "• Не оставайтесь в одиночестве, обратитесь за поддержкой\n"
            "• Рассмотрите возможность временного снижения нагрузки"
        )
    
    return result_text

# ==================== ФУНКЦИИ ДЛЯ ИИ-ТЕСТИРОВАНИЯ ====================

def format_ai_analysis(analysis: Dict) -> str:
    """Форматирование результата ИИ-анализа"""
    level_emojis = {
        "низкий": "🟢",
        "средний": "🟡", 
        "высокий": "🔴",
        "низкая": "🟢",
        "средняя": "🟡",
        "высокая": "🔴"
    }
    
    general = analysis.get('general_assessment', 'Анализ выполнен')
    symptoms = analysis.get('symptoms', [])
    burnout_stages = analysis.get('burnout_stages', {})
    recommendations = analysis.get('recommendations', [])
    anxiety = analysis.get('anxiety_level', 'средний')
    next_steps = analysis.get('next_steps', 'Рекомендуется пройти стандартные тесты для более точной диагностики.')
    
    response = f"""🧠 **ИИ-АНАЛИЗ ЭМОЦИОНАЛЬНОГО СОСТОЯНИЯ**

📋 **Общая оценка:**
{general}

🔍 **Выявленные симптомы:**
"""
    
    if symptoms:
        for symptom in symptoms[:5]:
            response += f"• {symptom}\n"
    else:
        response += "• Не выявлено\n"
    
    if burnout_stages and any(burnout_stages.values()):
        response += "\n**📊 Стадии выгорания (по Бойко):**\n"
        
        stage_names = {
            'tension': 'Напряжение',
            'resistance': 'Резистенция',
            'exhaustion': 'Истощение',
            'deformation': 'Деформация'
        }
        
        for stage_key, stage_name in stage_names.items():
            level = burnout_stages.get(stage_key, 'средний')
            emoji = level_emojis.get(level.lower(), '⚪')
            response += f"{emoji} **{stage_name}:** {level}\n"
    
    response += f"\n**😰 Уровень тревожности:** {level_emojis.get(anxiety.lower(), '🟡')} {anxiety}\n"
    
    if recommendations:
        response += "\n**💡 Рекомендации:**\n"
        for i, rec in enumerate(recommendations[:5], 1):
            response += f"{i}. {rec}\n"
    
    response += f"\n**🚀 Рекомендуемые действия:**\n{next_steps}\n"
    
    response += """
---
⚠️ **Важно:** Это экспериментальная диагностика на основе ИИ. 
Она не заменяет профессиональную консультацию психолога 
или медицинскую диагностику. При серьезных симптомах 
обратитесь к специалисту.
"""
    return response

async def start_ai_test(message: Message, user_id: int):
    """Начало ИИ-диагностики"""
    user_data[user_id] = {
        "state": AITestStates.WAITING_DESCRIPTION,
        "test_started": True
    }
    
    welcome_text = (
        "🤖 **Экспериментальная ИИ-диагностика выгорания для IT-специалистов**\n\n"
        "Это инновационный формат тестирования, где искусственный интеллект "
        "проанализирует ваше состояние на основе свободного описания.\n\n"
        "📝 **Опишите подробно:**\n"
        "• Ваше эмоциональное состояние (что чувствуете, настроение)\n"
        "• Физическое самочувствие (усталость, напряжение, сон, аппетит)\n"
        "• Отношение к работе (интерес, мотивация, продуктивность)\n"
        "• Взаимодействие с коллегами и командой\n"
        "• Мысли о карьере и будущем в IT\n"
        "• Любые другие важные для вас аспекты\n\n"
        "💡 **Чем подробнее опишете, тем точнее будет анализ!**\n\n"
        "Нажмите **❌ Отменить ИИ-тест**, чтобы прервать."
    )
    
    await message.answer(welcome_text, keyboard=get_ai_cancel_keyboard())

async def process_ai_description(message: Message, user_id: int):
    """Обработка описания для ИИ-анализа"""
    text = clean_text(message.text)
    
    if text == "❌ Отменить ИИ-тест":
        if user_id in user_data:
            del user_data[user_id]
        await message.answer("Тест отменен. Возвращаю в главное меню:", keyboard=get_main_keyboard())
        return
    
    # Показываем индикатор загрузки
    loading_msg = await message.answer("🔄 ИИ анализирует ваше состояние... Это может занять до 30 секунд.")
    
    try:
        # Получаем анализ от GigaChat
        analysis = await gigachat_vk.analyze_emotional_state(text, user_id)
        
        # Проверяем, не является ли ответ нарушением этики
        if analysis.get("ethics_violation"):
            # Отправляем простое сообщение об ошибке (без шаблона)
            await message.answer(
                "❌ **Извините, я не могу обработать этот запрос.**\n\n"
                "Пожалуйста, опишите своё эмоциональное состояние без использования запрещённых тем.\n\n"
                "Вы можете:\n"
                "• Описать своё самочувствие\n"
                "• Спросить о методах борьбы со стрессом\n"
                "• Поделиться рабочими переживаниями",
                keyboard=get_main_keyboard()
            )
            # Удаляем пользователя из активного теста
            if user_id in user_data:
                del user_data[user_id]
            return
        
        # Сохраняем результат в статистику (только если не нарушение)
        result_summary = {
            "general_assessment": analysis.get('general_assessment', ''),
            "anxiety_level": analysis.get('anxiety_level', 'средний')
        }
        update_statistics(user_id, "ai_experimental", result_summary)
        
        # Сохраняем результат
        user_data[user_id] = {
            "state": AITestStates.IN_CONVERSATION,
            "analysis": analysis
        }
        
        # Форматируем и отправляем результат
        result_text = format_ai_analysis(analysis)
        await message.answer(result_text)
        
        # Переходим в режим диалога
        dialog_message = (
            "💬 **Отлично! Теперь можем просто поговорить!** 😊\n\n"
            "Ты можешь спрашивать меня о чем угодно:\n"
            "• Как справиться с усталостью?\n"
            "• Что делать, если нет мотивации?\n"
            "• Как наладить режим сна?\n"
            "• Как улучшить отношения с коллегами?\n"
            "• Или просто поделиться тем, что на душе\n\n"
            "Я отвечу просто, по-человечески и с пониманием!\n\n"
            "Нажмите **🏠 Главное меню**, чтобы выйти из режима диалога."
        )
        await message.answer(dialog_message, keyboard=get_ai_dialog_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при ИИ-анализе: {e}")
        await message.answer(
            "❌ Произошла ошибка при обращении к ИИ. Пожалуйста, попробуйте позже.\n\n"
            "Вы можете воспользоваться стандартными тестами для диагностики.",
            keyboard=get_main_keyboard()
        )
        if user_id in user_data:
            del user_data[user_id]

async def continue_ai_dialog(message: Message, user_id: int):
    """Продолжение диалога с ИИ"""
    text = clean_text(message.text)
    
    if text == "🏠 Главное меню" or text == "◀ На главную":
        await gigachat_vk.reset_dialog(user_id)
        if user_id in user_data:
            del user_data[user_id]
        await message.answer("Возвращаю в главное меню:", keyboard=get_main_keyboard())
        return
    
    # Показываем индикатор
    thinking_msg = await message.answer("✍️ Печатаю...")
    
    try:
        response = await gigachat_vk.continue_dialog(text, user_id)
        await message.answer(response, keyboard=get_ai_dialog_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при диалоге с ИИ: {e}")
        await message.answer(
            "😕 Что-то пошло не так. Попробуй еще раз или нажми **🏠 Главное меню** для выхода.",
            keyboard=get_ai_dialog_keyboard()
        )

# ==================== ФУНКЦИИ ОТПРАВКИ ТЕСТОВ ====================

async def send_question(message: Message, user_id: int):
    """Отправка текущего вопроса пользователю"""
    data = user_data[user_id]
    step = data["step"]
    questions = data["questions"]
    
    if step < len(questions):
        question_text = f"📝 **Вопрос {step + 1} из {len(questions)}**\n\n{questions[step]}"
        await message.answer(
            question_text,
            keyboard=get_answer_keyboard()
        )
    else:
        await show_result(message, user_id)

async def show_result(message: Message, user_id: int):
    """Показ результата теста"""
    data = user_data.pop(user_id)
    test_name = data["test"]
    answers = data["answers"]
    
    if test_name == "quick":
        result = calculate_quick_result(answers)
        # Сохраняем в статистику
        result_summary = extract_result_summary("quick", answers)
        update_statistics(user_id, "quick", result_summary)
        
    elif test_name == "maslach":
        result = calculate_maslach_result(answers)
        result_summary = extract_result_summary("maslach", answers)
        update_statistics(user_id, "maslach", result_summary)
        
    elif test_name == "boyko":
        result = calculate_boyko_result(answers)
        result_summary = extract_result_summary("boyko", answers)
        update_statistics(user_id, "boyko", result_summary)
        
    elif test_name == "heck_hess":
        result = calculate_heck_hess_result(answers)
        result_summary = extract_result_summary("heck_hess", answers)
        update_statistics(user_id, "heck_hess", result_summary)
        
    else:
        result = "Ошибка при расчёте результата."
    
    await message.answer(
        f"{result}\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Выберите другой тест в главном меню:",
        keyboard=get_main_keyboard()
    )

async def start_test(message: Message, user_id: int, test_type: str):
    """Начало прохождения теста"""
    test_configs = {
        "quick": ("⚡ Быстрый тест (экспресс-оценка выгорания)", QUICK_TEST),
        "maslach": ("📊 Опросник Маслач (классическая методика)", MASLACH_TEST),
        "boyko": ("🧠 Тест Бойко (анализ 4 фаз выгорания)", BOYKO_TEST),
        "heck_hess": ("🏥 Тест Хека-Хесса (оценка депрессивных симптомов)", HECK_HESS_TEST)
    }
    
    test_name, questions = test_configs[test_type]
    
    user_data[user_id] = {
        "test": test_type,
        "step": 0,
        "answers": [],
        "questions": questions
    }
    
    await message.answer(
        f"🎯 **{test_name}**\n\n"
        f"Тест содержит {len(questions)} вопросов.\n"
        f"Оценивайте каждое утверждение от **0** (никогда/нет) до **5** (всегда/да).\n\n"
        f"Нажмите **◀ На главную**, чтобы прервать тест.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Поехали! 👇",
        keyboard=get_answer_keyboard()
    )
    await send_question(message, user_id)

async def show_statistics(message: Message, user_id: int):
    """Показывает статистику пользователя"""
    stats_text = get_statistics_text(user_id)
    await message.answer(stats_text, keyboard=get_back_keyboard())

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================

@labeler.message()
async def message_handler(message: Message):
    """Главный обработчик сообщений"""
    user_id = message.from_id
    raw_text = message.text
    text = clean_text(raw_text)
    
    print(f"🔍 Получено: '{raw_text}' -> Очищено: '{text}'")
    
    # Проверяем, есть ли пользователь в активном тесте или ИИ-диалоге
    if user_id in user_data:
        state = user_data[user_id].get("state")
        
        if state == AITestStates.WAITING_DESCRIPTION:
            await process_ai_description(message, user_id)
            return
        
        elif state == AITestStates.IN_CONVERSATION:
            await continue_ai_dialog(message, user_id)
            return
        
        else:
            if text and text.isdigit() and 0 <= int(text) <= 5:
                answer = int(text)
                data = user_data[user_id]
                data["answers"].append(answer)
                data["step"] += 1
                await send_question(message, user_id)
            elif text == "◀ На главную":
                del user_data[user_id]
                await message.answer(
                    "✅ Тест прерван. Возвращаю в главное меню.",
                    keyboard=get_main_keyboard()
                )
            else:
                await message.answer(
                    "Пожалуйста, выберите оценку от 0 до 5 с помощью кнопок клавиатуры.\n"
                    "Или нажмите ◀ На главную для выхода.",
                    keyboard=get_answer_keyboard()
                )
            return
    
    # Если пользователь не в тесте, обрабатываем команды
    if text in ["Начать", "/start", "Привет", "старт"]:
        greeting = (
            "🌟 **Приветствую, IT-специалист!** 🌟\n\n"
            "Я бот диагностики профессионального выгорания.\n"
            "Я помогу оценить ваше эмоциональное состояние и дам рекомендации.\n\n"
            "**Доступные тесты:**\n"
            "• ⚡ Быстрый тест (10 вопросов) — экспресс-оценка\n"
            "• 📊 Опросник Маслач — классическая методика\n"
            "• 🧠 Тест Бойко — анализ 4 фаз выгорания\n"
            "• 🏥 Тест Хека-Хесса — оценка депрессивных симптомов\n"
            "• 🤖 ИИ-диагностика — анализ на основе свободного описания\n"
            "• 📊 Моя статистика — отслеживание прогресса\n\n"
            "Выберите тест из меню ниже 👇"
        )
        await message.answer(greeting, keyboard=get_main_keyboard())
    
    elif text in ["Помощь", "❓ Помощь"]:
        help_text = (
            "❓ **Справка по использованию**\n\n"
            "**Как пройти тест:**\n"
            "1. Выберите тест из главного меню\n"
            "2. Отвечайте на вопросы, выбирая цифру от 0 до 5\n"
            "3. После завершения вы получите результат и рекомендации\n\n"
            "**ИИ-диагностика:**\n"
            "• Опишите свое состояние свободным текстом\n"
            "• ИИ проанализирует ответ и даст рекомендации\n"
            "• После анализа можно продолжить диалог\n"
            "• Нажмите **🏠 Главное меню** для выхода из диалога\n\n"
            "**Статистика:**\n"
            "• Все ваши результаты сохраняются\n"
            "• Вы можете отслеживать динамику изменений\n"
            "• Данные хранятся локально и не передаются третьим лицам\n\n"
            "**Шкала оценок:**\n"
            "0 — никогда / полностью не согласен\n"
            "1 — очень редко\n"
            "2 — иногда\n"
            "3 — часто\n"
            "4 — очень часто\n"
            "5 — всегда / полностью согласен\n\n"
            "Все данные анонимны и не сохраняются.\n"
            "Бот не заменяет консультацию специалиста."
        )
        await message.answer(help_text, keyboard=get_back_keyboard())
    
    elif text in ["Быстрый тест", "⚡ Быстрый тест"]:
        await start_test(message, user_id, "quick")
    
    elif text in ["Опросник Маслач", "📊 Опросник Маслач"]:
        await start_test(message, user_id, "maslach")
    
    elif text in ["Тест Бойко", "🧠 Тест Бойко"]:
        await start_test(message, user_id, "boyko")
    
    elif text in ["Тест Хека-Хесса", "🏥 Тест Хека-Хесса"]:
        await start_test(message, user_id, "heck_hess")
    
    elif text in ["ИИ-диагностика", "🤖 ИИ-диагностика"]:
        await start_ai_test(message, user_id)
    
    elif text in ["Моя статистика", "📊 Моя статистика"]:
        await show_statistics(message, user_id)
    
    elif text == "◀ На главную":
        await message.answer(
            "Главное меню:",
            keyboard=get_main_keyboard()
        )
    
    elif text and text.isdigit() and int(text) <= 5:
        await message.answer(
            "Сначала выберите тест из главного меню!",
            keyboard=get_main_keyboard()
        )
    
    else:
        await message.answer(
            "Выберите тест из меню ниже:",
            keyboard=get_main_keyboard()
        )

# ==================== ЗАПУСК БОТА ====================
if __name__ == "__main__":
    # Загружаем статистику при запуске
    load_statistics()
    
    print("🤖 Бот диагностики выгорания запущен!")
    print("📊 Статистика будет сохраняться в файл user_statistics.json")
    print("Используйте LongPoll для получения сообщений...")
    print("Бот готов к работе!")
    
    bot.run_forever()