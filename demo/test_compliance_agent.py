import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from state_machine import DebtorInfo, DialogContext
from agents.compliance_agent import ComplianceAgent

async def test_compliance():
    """Тест Compliance Agent с разными сценариями"""
    
    print("\n" + "="*70)
    print("ТЕСТ: Compliance Agent — проверка действий на соответствие 230-ФЗ")
    print("="*70)
    
    # Создаём должника
    debtor = DebtorInfo(
        debtor_id="DEBT-COMPLIANCE-001",
        full_name="Иванов Иван Иванович",
        phone="+79991234567",
        debt_amount=50000.0,
        overdue_days=15
    )
    
    context = DialogContext(
        session_id="SESSION-COMPLIANCE-001",
        debtor=debtor
    )
    
    agent = ComplianceAgent()
    
    # Сценарий 1: Корректное сообщение (должно быть одобрено)
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 1: Корректное сообщение")
    print("-"*70)
    
    message = "Здравствуйте, Иван Иванович! Мы готовы предложить вам рассрочку на 3 месяца. Удобно ли вам обсудить условия?"
    print(f"Сообщение: {message}")
    
    result = await agent.check_action(context, "dialog_reply", message)
    
    print(f"\n📊 Результат проверки:")
    print(f"   Одобрено: {'✅ ДА' if result.is_approved else '❌ НЕТ'}")
    print(f"   Тип нарушения: {result.violation_type}")
    print(f"   Уверенность: {result.confidence}")
    print(f"   Обоснование: {result.reasoning}")
    
    # Сценарий 2: Нарушение — угроза раскрытия информации (должно быть заблокировано)
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 2: Нарушение — угроза раскрытия информации")
    print("-"*70)
    
    message = "Если вы не оплатите долг сегодня, мы расскажем о вашей задолженности вашему работодателю и соседям."
    print(f"Сообщение: {message}")
    
    result = await agent.check_action(context, "dialog_reply", message)
    
    print(f"\n📊 Результат проверки:")
    print(f"   Одобрено: {'✅ ДА' if result.is_approved else '❌ НЕТ'}")
    print(f"   Тип нарушения: {result.violation_type}")
    if result.violation_description:
        print(f"   Описание нарушения: {result.violation_description}")
    if result.blocked_reason:
        print(f"   Причина блокировки: {result.blocked_reason}")
    print(f"   Уверенность: {result.confidence}")
    print(f"   Обоснование: {result.reasoning}")
    
    # Сценарий 3: Нарушение — угроза физической силой (должно быть заблокировано)
    print("\n" + "-"*70)
    print("СЦЕНАРИЙ 3: Нарушение — угроза")
    print("-"*70)
    
    message = "Мы приедем к вам домой и опишем ваше имущество, если вы не заплатите."
    print(f"Сообщение: {message}")
    
    result = await agent.check_action(context, "dialog_reply", message)
    
    print(f"\n📊 Результат проверки:")
    print(f"   Одобрено: {'✅ ДА' if result.is_approved else '❌ НЕТ'}")
    print(f"   Тип нарушения: {result.violation_type}")
    if result.violation_description:
        print(f"   Описание нарушения: {result.violation_description}")
    if result.blocked_reason:
        print(f"   Причина блокировки: {result.blocked_reason}")
    print(f"   Уверенность: {result.confidence}")
    print(f"   Обоснование: {result.reasoning}")

if __name__ == "__main__":
    asyncio.run(test_compliance())