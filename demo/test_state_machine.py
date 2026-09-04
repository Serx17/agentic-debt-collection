import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_machine import (
    DialogState,
    TransitionTrigger,
    DebtorInfo,
    DialogContext,
    StateMachine
)

def test_happy_path():
    """Тест успешного сценария: ответ -> идентификация -> признание долга -> согласие на оплату"""
    print("\n" + "="*70)
    print("ТЕСТ 1: Успешный сценарий (Happy Path)")
    print("="*70)
    
    # Создаём должника
    debtor = DebtorInfo(
        debtor_id="DEBT-001",
        full_name="Иванов Иван Иванович",
        phone="+79991234567",
        debt_amount=50000.0,
        overdue_days=15
    )
    
    # Создаём контекст диалога
    context = DialogContext(
        session_id="SESSION-001",
        debtor=debtor
    )
    
    print(f"Начальное состояние: {context.current_state.value}")
    
    # Шаг 1: Должник ответил
    print("\n📞 Должник ответил на звонок...")
    context = StateMachine.transition(context, TransitionTrigger.CALL_ANSWERED)
    print(f"✅ Новое состояние: {context.current_state.value}")
    
    # Шаг 2: Личность подтверждена
    print("\n🔐 Личность подтверждена (кодовое слово совпало)...")
    context = StateMachine.transition(context, TransitionTrigger.IDENTITY_CONFIRMED)
    print(f"✅ Новое состояние: {context.current_state.value}")
    context.identity_verified = True
    
    # Шаг 3: Должник признал долг
    print("\n💰 Должник признал долг...")
    context = StateMachine.transition(context, TransitionTrigger.DEBT_ACKNOWLEDGED)
    print(f"✅ Новое состояние: {context.current_state.value}")
    context.debt_acknowledged = True
    
    # Шаг 4: Согласился на оплату
    print("\n💳 Должник согласился оплатить долг в рассрочку...")
    context = StateMachine.transition(context, TransitionTrigger.PAYMENT_AGREED)
    print(f"✅ Новое состояние: {context.current_state.value}")
    context.promised_amount = 10000.0
    
    # Шаг 5: Завершение
    print("\n✔️ Обещание платежа получено, диалог завершён...")
    context = StateMachine.transition(context, TransitionTrigger.PAYMENT_AGREED)
    print(f"✅ Финальное состояние: {context.current_state.value}")
    
    print(f"\n📊 Итого переходов: {len(context.transitions)}")
    for i, t in enumerate(context.transitions, 1):
        print(f"  {i}. {t['from_state']} → {t['to_state']} (триггер: {t['trigger']})")

def test_human_handoff():
    """Тест сценария с передачей оператору"""
    print("\n" + "="*70)
    print("ТЕСТ 2: Сценарий с передачей оператору")
    print("="*70)
    
    debtor = DebtorInfo(
        debtor_id="DEBT-002",
        full_name="Петров Петр Петрович",
        phone="+79997654321",
        debt_amount=75000.0,
        overdue_days=30
    )
    
    context = DialogContext(
        session_id="SESSION-002",
        debtor=debtor
    )
    
    print(f"Начальное состояние: {context.current_state.value}")
    
    # Должник ответил
    context = StateMachine.transition(context, TransitionTrigger.CALL_ANSWERED)
    print(f"📞 Ответил → {context.current_state.value}")
    
    # Личность подтверждена
    context = StateMachine.transition(context, TransitionTrigger.IDENTITY_CONFIRMED)
    print(f"🔐 Личность подтверждена → {context.current_state.value}")
    
    # Должник оспаривает долг
    print("\n⚠️ Должник оспаривает сумму долга...")
    context = StateMachine.transition(context, TransitionTrigger.DEBT_DISPUTED)
    print(f"👨‍💼 Передача оператору → {context.current_state.value}")
    
    print(f"\n📊 Итого переходов: {len(context.transitions)}")
    for i, t in enumerate(context.transitions, 1):
        print(f"  {i}. {t['from_state']} → {t['to_state']} (триггер: {t['trigger']})")

def test_invalid_transition():
    """Тест невозможного перехода"""
    print("\n" + "="*70)
    print("ТЕСТ 3: Попытка невозможного перехода")
    print("="*70)
    
    debtor = DebtorInfo(
        debtor_id="DEBT-003",
        full_name="Сидоров Сидор Сидорович",
        phone="+79991112233",
        debt_amount=30000.0,
        overdue_days=10
    )
    
    context = DialogContext(
        session_id="SESSION-003",
        debtor=debtor
    )
    
    print(f"Начальное состояние: {context.current_state.value}")
    
    # Пытаемся перейти к переговорам без подтверждения личности
    print("\n❌ Пытаемся перейти к переговорам без подтверждения личности...")
    try:
        context = StateMachine.transition(context, TransitionTrigger.DEBT_ACKNOWLEDGED)
        print("⚠️ ОШИБКА: Переход должен был быть заблокирован!")
    except ValueError as e:
        print(f"✅ Ожидаемая ошибка: {e}")

if __name__ == "__main__":
    test_happy_path()
    test_human_handoff()
    test_invalid_transition()
    
    print("\n" + "="*70)
    print("✅ Все тесты State Machine пройдены!")
    print("="*70)