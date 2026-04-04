from datetime import date, timedelta
from typing import Tuple

def calculate_sm2_interval(
    quality: int,
    repetitions: int,
    interval: int
) -> Tuple[int, int]:
    """
    Рассчитывает новый интервал и количество повторений по алгоритму SM-2
    
    Args:
        quality: Оценка пользователя (0-5), где:
            0-2: неверно/трудно (перезапуск)
            3: трудно (интервал 1 день)
            4: хорошо
            5: отлично
        repetitions: Текущее количетво успешных повторений подряд.
        interval: Текущий интервал в днях.
        
    Returns:
        (new_interval, new_repetitions)
    """
    
    if quality <3:
        # Неудачное повторение сброс
        return 0, 0
    
    # Успешное повторение
    new_repetitions = repetitions + 1
    
    if new_repetitions == 1:
        new_interval = 1
    elif new_repetitions == 2:
        new_interval = 6
    else:
        # Формула I(n) = I(n-1) * EF
        # Для упрощения используется фиксированный множитель ~2.5,
        # так как полноценный расчет коэффициента легкости (EF) требует хранения EF для каждой карточки.
        # в нашей системе заметок мы используем упрощенную версию.
        new_interval = int(interval * 2.5)
    
    return new_interval, new_repetitions

def get_next_review_date(quality: int, last_interval: int, last_reps: int) -> Tuple[date, int, int]:
    """
    Возвращает дату следующего повторения, новый интервал и новое кол-во повторений.
    """
    today = date.today()
    
    new_interval, new_reps = calculate_sm2_interval(quality, last_reps, last_interval)
    
    next_date = today + timedelta(days=new_interval)
    
    return next_date, new_interval, new_reps
    
    