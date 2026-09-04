import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from state_machine import (
    DialogState,
    DebtorInfo,
    DialogContext
)
from agents.orchestrator_agent import OrchestratorAgent

async def simulate_dialog():
    """Симуляция полного диалога с должником"""
    
    print("\n" + "="*80)
    print("🎬 СИМУЛЯЦИЯ ПОЛНОГО ДИАЛОГА С ДОЛЖНИКОМ")
    print("="*80)
    
    # Создаём должника
    debtor = DebtorInfo(
        debtor_id="DEBT-FINAL-001",
        full_name="Иванов Иван Иванович",
        phone="+79991234567",
        debt_amount=50000.0,
        overdue_days=15
    )
    
    # Создаём контекст диалога
    context = DialogContext(
        session_id="SESSION-FINAL-001",
        debtor=debtor
    )
    
    orchestrator = OrchestratorAgent()
    
    print(f"\n📋 Информация о должнике:")
    print(f"   Имя: {debtor.full_name}")
    print(f"   Долг: {debtor.debt_amount:.2f} {debtor.debt_currency}")
    print(f"   Просрочка: {debtor.overdue_days} дней")
    print(f"\n🔔 Начало диалога...")
    print(f"   Текущее состояние: {context.current_state.value}")
    
    # Сценарий 1: Должник отвечает на звонок
    print("\n" + "-"*80)
    print("ЭТАП 1: Должник отвечает на звонок")
    print("-"*80)
    
    debtor_msg = "Да, слушаю. Кто звонит?"
    print(f"💬 Должник: {debtor_msg}")
    
    decision = await orchestrator.process_message(context, debtor_msg)
    
    print(f"\n🎯 Решение Orchestrator:")
    print(f"   Действие: {decision.action}")
    if decision.reply_text:
        print(f"   Реплика: {decision.reply_text}")
    print(f"   Уверенность: {decision.confidence}")
    print(f"   Обоснование: {decision.reasoning}")
    
    # Сценарий 2: Должник подтверждает личность
    print("\n" + "-"*80)
    print("ЭТАП 2: Должник подтверждает личность")
    print("-"*80)
    
    debtor_msg = "Моё кодовое слово: Солнце"
    print(f"💬 Должник: {debtor_msg}")
    
    decision = await orchestrator.process_message(context, debtor_msg)
    context.identity_verified = True
    
    print(f"\n🎯 Решение Orchestrator:")
    print(f"   Действие: {decision.action}")
    if decision.reply_text:
        print(f"   Реплика: {decision.reply_text}")
    print(f"   Уверенность: {decision.confidence}")
    print(f"   Обоснование: {decision.reasoning}")
    
    # Сценарий 3: Должник признаёт долг
    print("\n" + "-"*80)
    print("ЭТАП 3: Должник признаёт долг")
    print("-"*80)
    
    debtor_msg = "Да, я знаю про долг. Но у меня сейчас нет денег."
    print(f"💬 Должник: {debtor_msg}")
    
    decision = await orchestrator.process_message(context, debtor_msg)
    context.debt_acknowledged = True
    
    print(f"\n🎯 Решение Orchestrator:")
    print(f"   Действие: {decision.action}")
    if decision.reply_text:
        print(f"   Реплика: {decision.reply_text}")
    print(f"   Уверенность: {decision.confidence}")
    print(f"   Обоснование: {decision.reasoning}")
    
    # Сценарий 4: Должник соглашается на рассрочку
    print("\n" + "-"*80)
    print("ЭТАП 4: Должник соглашается на рассрочку")
    print("-"*80)
    
    debtor_msg = "Хорошо, давайте попробуем рассрочку на 3 месяца. Это подходит."
    print(f"💬 Должник: {debtor_msg}")
    
    decision = await orchestrator.process_message(context, debtor_msg)
    
    print(f"\n🎯 Решение Orchestrator:")
    print(f"   Действие: {decision.action}")
    if decision.reply_text:
        print(f"   Реплика: {decision.reply_text}")
    print(f"   Уверенность: {decision.confidence}")
    print(f"   Обоснование: {decision.reasoning}")
    
    # Финальная статистика
    print("\n" + "="*80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА ДИАЛОГА")
    print("="*80)
    print(f"   Всего переходов: {len(context.transitions)}")
    print(f"   Финальное состояние: {context.current_state.value}")
    print(f"   Личность подтверждена: {'✅' if context.identity_verified else '❌'}")
    print(f"   Долг признан: {'✅' if context.debt_acknowledged else '❌'}")
    
    print("\n📜 История переходов:")
    for i, t in enumerate(context.transitions, 1):
        print(f"   {i}. {t['from_state']} → {t['to_state']} (триггер: {t['trigger']})")
    
    print("\n" + "="*80)
    print("✅ СИМУЛЯЦИЯ ЗАВЕРШЕНА УСПЕШНО")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(simulate_dialog())