import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from pydantic import BaseModel, Field
from agents.llm_provider import YandexGPTProvider
from state_machine import DialogState, DialogContext

class NegotiationResponse(BaseModel):
    """Структурированный ответ Negotiation Agent"""
    reply_text: str = Field(..., description="Текст реплики для должника")
    suggested_action: str = Field(
        ..., 
        description="Предлагаемое действие: 'continue_dialog', 'request_payment', 'offer_restructuring', 'end_call'"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность агента в ответе")
    reasoning: str = Field(..., description="Краткое обоснование выбора реплики")

class NegotiationAgent:
    """
    Агент переговоров.
    Генерирует реплики для должника на основе текущего состояния диалога.
    
    ВАЖНО: Этот агент НЕ имеет доступа к каналам связи (SMS, звонки).
    Он только генерирует текст и предлагает действия.
    """
    
    def __init__(self):
        self.provider = YandexGPTProvider()
    
    async def generate_reply(self, context: DialogContext, debtor_message: str) -> NegotiationResponse:
        """
        Генерация реплики для должника.
        
        Args:
            context: Текущий контекст диалога (состояние, информация о должнике)
            debtor_message: Последнее сообщение от должника
        
        Returns:
            NegotiationResponse с текстом реплики и предлагаемым действием
        """
        
        # Формируем системный промпт на основе состояния диалога
        system_prompt = self._build_system_prompt(context.current_state)
        
        # Формируем контекст должника
        debtor_context = self._build_debtor_context(context)
        
        # Собираем полный промпт
        prompt = f"""
{system_prompt}

{debtor_context}

Последнее сообщение должника:
"{debtor_message}"

Сгенерируй ответ строго в формате JSON:
{{
    "reply_text": "Текст твоей реплики для должника",
    "suggested_action": "continue_dialog" или "request_payment" или "offer_restructuring" или "end_call",
    "confidence": 0.95,
    "reasoning": "Почему ты выбрал именно такую реплику"
}}

Правила:
1. Будь вежливым, но настойчивым.
2. НЕ угрожай и НЕ дави на должника.
3. Если должник согласен оплатить, предложи конкретные варианты (полная оплата, рассрочка).
4. Если должник отказывается или агрессивен, заверши диалог и передай оператору.
5. Поле "suggested_action" должно отражать твоё следующее действие:
   - "continue_dialog": продолжить разговор
   - "request_payment": запросить оплату
   - "offer_restructuring": предложить рассрочку
   - "end_call": завершить звонок
"""
        
        async with self.provider as provider:
            return await provider.agenerate_structured(prompt, NegotiationResponse)
    
    def _build_system_prompt(self, state: DialogState) -> str:
        """Формирует системный промпт на основе состояния диалога"""
        
        prompts = {
            DialogState.IDENTITY_VERIFICATION: """
Ты — оператор контакт-центра банка. Сейчас ты должен подтвердить личность должника.
Попроси его назвать кодовое слово или дату рождения для подтверждения личности.
Будь вежливым и профессиональным.
""",
            DialogState.DEBT_PRESENTATION: """
Ты — оператор контакт-центра банка. Личность должника подтверждена.
Информируй его о наличии задолженности: сумма, срок просрочки.
Говори спокойно, без давления. Предложи обсудить варианты погашения.
""",
            DialogState.NEGOTIATION: """
Ты — оператор контакт-центра банка. Должник знает о своем долге.
Твоя задача — помочь ему найти удобный способ погашения:
- Полная оплата сразу
- Рассрочка на 3-6 месяцев
- Реструктуризация с уменьшением платежей

Будь empathetic, но настойчивым. Предложи конкретные варианты.
""",
            DialogState.PROMISE_TO_PAY: """
Ты — оператор контакт-центра банка. Должник согласился на условия оплаты.
Подтверди договоренности: сумма, дата платежа.
Поблагодари за сотрудничество и уточни, есть ли дополнительные вопросы.
"""
        }
        
        return prompts.get(state, "Ты — вежливый оператор контакт-центра. Веди диалог профессионально.")
    
    def _build_debtor_context(self, context: DialogContext) -> str:
        """Формирует контекст должника для промпта"""
        
        debtor = context.debtor
        lines = [
            f"Информация о должнике:",
            f"- Имя: {debtor.full_name}",
            f"- Сумма долга: {debtor.debt_amount:.2f} {debtor.debt_currency}",
            f"- Просрочка: {debtor.overdue_days} дней",
        ]
        
        if context.identity_verified:
            lines.append("- Личность подтверждена: ДА")
        
        if context.debt_acknowledged:
            lines.append("- Долг признан: ДА")
        
        if context.promised_amount:
            lines.append(f"- Обещанная сумма: {context.promised_amount:.2f} {debtor.debt_currency}")
        
        return "\n".join(lines)