import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from state_machine import (
    DialogState,
    TransitionTrigger,
    DialogContext,
    StateMachine
)
from agents.negotiation_agent import NegotiationAgent
from agents.compliance_agent import ComplianceAgent

class OrchestratorDecision(BaseModel):
    """Решение Orchestrator Agent"""
    action: str = Field(..., description="Действие: 'send_reply', 'transition_state', 'handoff_to_human', 'end_dialog'")
    reply_text: Optional[str] = Field(None, description="Текст реплики для должника (если action = 'send_reply')")
    next_trigger: Optional[str] = Field(None, description="Триггер для перехода в следующее состояние")
    handoff_reason: Optional[str] = Field(None, description="Причина передачи оператору")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в решении")
    reasoning: str = Field(..., description="Обоснование решения")

class OrchestratorAgent:
    """
    Оркестратор диалога.
    Координирует работу всех агентов и управляет состоянием диалога.
    
    Архитектурные принципы:
    1. Negotiation Agent генерирует реплики, но НЕ имеет доступа к каналам связи
    2. Compliance Agent проверяет каждое действие перед исполнением
    3. Orchestrator принимает финальные решения на основе состояния и контекста
    """
    
    def __init__(self):
        self.negotiation_agent = NegotiationAgent()
        self.compliance_agent = ComplianceAgent()
    
    async def process_message(
        self,
        context: DialogContext,
        debtor_message: str
    ) -> OrchestratorDecision:
        """
        Обработка сообщения от должника.
        
        Args:
            context: Текущий контекст диалога
            debtor_message: Сообщение от должника
        
        Returns:
            OrchestratorDecision с решением о следующем действии
        """
        
        print(f"\n🎯 Orchestrator: Обработка сообщения в состоянии '{context.current_state.value}'")
        
        # 1. Анализируем сообщение должника и определяем триггер
        trigger = self._determine_trigger(context, debtor_message)
        print(f"   Определён триггер: {trigger.value if trigger else 'None'}")
        
        # 2. Проверяем, возможен ли переход
        if trigger and StateMachine.can_transition(context.current_state, trigger):
            transition = StateMachine.get_transition(context.current_state, trigger)
            
            # Если переход требует передачи оператору
            if transition.requires_human_handoff:
                print(f"   🚨 Требуется передача оператору: {transition.description}")
                return OrchestratorDecision(
                    action="handoff_to_human",
                    handoff_reason=transition.description,
                    confidence=1.0,
                    reasoning=f"Состояние требует передачи оператору: {transition.description}"
                )
            
            # Выполняем переход
            context = StateMachine.transition(context, trigger)
            print(f"   ✅ Переход в состояние: {context.current_state.value}")
        
        # 3. Генерируем реплику через Negotiation Agent
        print(f"   🤖 Запрос к Negotiation Agent...")
        negotiation_response = await self.negotiation_agent.generate_reply(context, debtor_message)
        print(f"   📝 Сгенерирована реплика: {negotiation_response.reply_text[:50]}...")
        
        # 4. Проверяем реплику через Compliance Agent
        print(f"   🔒 Проверка compliance...")
        compliance_result = await self.compliance_agent.check_action(
            context,
            "dialog_reply",
            negotiation_response.reply_text
        )
        
        # 5. Если compliance заблокировал — передаём оператору
        if not compliance_result.is_approved:
            print(f"   ❌ Compliance заблокировал: {compliance_result.violation_description}")
            return OrchestratorDecision(
                action="handoff_to_human",
                handoff_reason=f"Compliance заблокировал реплику: {compliance_result.violation_description}",
                confidence=compliance_result.confidence,
                reasoning=compliance_result.reasoning
            )
        
        # 6. Если всё ок — отправляем реплику
        print(f"   ✅ Compliance одобрил реплику")
        return OrchestratorDecision(
            action="send_reply",
            reply_text=negotiation_response.reply_text,
            confidence=negotiation_response.confidence,
            reasoning=negotiation_response.reasoning
        )
    
    def _determine_trigger(
        self,
        context: DialogContext,
        debtor_message: str
    ) -> Optional[TransitionTrigger]:
        """
        Определение триггера на основе сообщения должника.
        В продакшене здесь будет вызов LLM для классификации намерения.
        Для MVP используем простые правила.
        """
        message_lower = debtor_message.lower()
        
        # ИНИЦИАЦИЯ: Должник ответил на звонок
        if context.current_state == DialogState.INITIATION:
            # Любая реплика должника означает, что он ответил
            if len(debtor_message.strip()) > 0:
                return TransitionTrigger.CALL_ANSWERED
        
        # ПРОВЕРКА ЛИЧНОСТИ
        elif context.current_state == DialogState.IDENTITY_VERIFICATION:
            if any(word in message_lower for word in ["кодовое слово", "дата рождения", "подтверждаю", "верно", "солнце"]):
                return TransitionTrigger.IDENTITY_CONFIRMED
            elif any(word in message_lower for word in ["не знаю", "отказываюсь", "кто вы", "не скажу"]):
                return TransitionTrigger.IDENTITY_FAILED
        
        # ИНФОРМИРОВАНИЕ О ДОЛГЕ
        elif context.current_state == DialogState.DEBT_PRESENTATION:
            if any(word in message_lower for word in ["знаю", "понимаю", "согласен", "да", "верно"]):
                return TransitionTrigger.DEBT_ACKNOWLEDGED
            elif any(word in message_lower for word in ["не согласен", "оспариваю", "ошибка", "нет"]):
                return TransitionTrigger.DEBT_DISPUTED
        
        # ПЕРЕГОВОРЫ
        elif context.current_state == DialogState.NEGOTIATION:
            if any(word in message_lower for word in ["согласен", "оплачу", "договорились", "подходит", "давайте"]):
                return TransitionTrigger.PAYMENT_AGREED
            elif any(word in message_lower for word in ["отказываюсь", "не буду", "оператор", "адвокат"]):
                return TransitionTrigger.REQUESTED_OPERATOR
            elif any(word in message_lower for word in ["нет денег", "не могу", "позже"]):
                return TransitionTrigger.PAYMENT_REFUSED
        
        return None