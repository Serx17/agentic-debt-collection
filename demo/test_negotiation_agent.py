import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()  # Загружаем переменные из .env

from state_machine import (
    DialogState,
    TransitionTrigger,
    DebtorInfo,
    DialogContext,
    StateMachine
)
from agents.negotiation_agent import NegotiationAgent

async def test_negotiation():
    """Тест Negotiation Agent в разных состояниях диалога"""
    
    print("\n" + "="*70)
    print("ТЕСТ: Negotiation Agent в различных состояниях диалога")
    print("="*70)
    
    # Создаём должника
    debtor = DebtorInfo(
        debtor_id="DEBT-TEST-001",
        full_name="Иванов Иван Иванович",
        phone="+79991234567",
        debt_amount=50000.0,
        overdue_days=15
    )
    
    # Создаём контекст
    context = DialogContext(
        session_id="SESSION-TEST-001",
        debtor=debtor
    )
    
    agent = NegotiationAgent()
    
    # Сценарий 1: Проверка личности
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 1: Проверка личности")
    print("-"*70)
    
    context = StateMachine.transition(context, TransitionTrigger.CALL_ANSWERED)
    print(f"Состояние: {context.current_state.value}")
    
    debtor_msg = "Да, слушаю. Кто звонит?"
    print(f"Должник: {debtor_msg}")
    
    response = await agent.generate_reply(context, debtor_msg)
    print(f"\n🤖 Агент ответил:")
    print(f"   Реплика: {response.reply_text}")
    print(f"   Действие: {response.suggested_action}")
    print(f"   Уверенность: {response.confidence}")
    print(f"   Обоснование: {response.reasoning}")
    
    # Сценарий 2: Информирование о долге
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 2: Информирование о долге")
    print("-"*70)
    
    context.identity_verified = True
    context = StateMachine.transition(context, TransitionTrigger.IDENTITY_CONFIRMED)
    context = StateMachine.transition(context, TransitionTrigger.DEBT_ACKNOWLEDGED)
    print(f"Состояние: {context.current_state.value}")
    
    debtor_msg = "Да, я знаю про долг. Но у меня сейчас нет денег."
    print(f"Должник: {debtor_msg}")
    
    response = await agent.generate_reply(context, debtor_msg)
    print(f"\n🤖 Агент ответил:")
    print(f"   Реплика: {response.reply_text}")
    print(f"   Действие: {response.suggested_action}")
    print(f"   Уверенность: {response.confidence}")
    print(f"   Обоснование: {response.reasoning}")
    
    # Сценарий 3: Переговоры о рассрочке
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 3: Переговоры о рассрочке")
    print("-"*70)
    
    debtor_msg = "А можно как-то частями платить? У меня зарплата через неделю."
    print(f"Должник: {debtor_msg}")
    
    response = await agent.generate_reply(context, debtor_msg)
    print(f"\n🤖 Агент ответил:")
    print(f"   Реплика: {response.reply_text}")
    print(f"   Действие: {response.suggested_action}")
    print(f"   Уверенность: {response.confidence}")
    print(f"   Обоснование: {response.reasoning}")

if __name__ == "__main__":
    asyncio.run(test_negotiation())