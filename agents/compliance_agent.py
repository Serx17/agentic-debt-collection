import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, time
from agents.llm_provider import YandexGPTProvider
from state_machine import DialogContext

class ComplianceCheckResult(BaseModel):
    """Результат проверки compliance"""
    is_approved: bool = Field(..., description="Одобрено ли действие")
    violation_type: Optional[str] = Field(None, description="Тип нарушения: 'time', 'frequency', 'content', 'none'")
    violation_description: Optional[str] = Field(None, description="Описание нарушения")
    blocked_reason: Optional[str] = Field(None, description="Причина блокировки")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в решении")
    reasoning: str = Field(..., description="Обоснование решения")

class ComplianceAgent:
    """
    Агент compliance.
    Проверяет каждое действие на соответствие 230-ФЗ перед исполнением.
    
    Проверяет:
    1. Время контакта (рабочие дни 08:00-22:00, выходные 09:00-20:00)
    2. Частоту контактов (не чаще 1 раза в сутки, 2 раз в неделю, 8 раз в месяц)
    3. Содержание сообщения (отсутствие угроз, давления, раскрытия информации третьим лицам)
    """
    
    def __init__(self):
        self.provider = YandexGPTProvider()
    
    async def check_action(
        self,
        context: DialogContext,
        action_type: str,
        action_content: str
    ) -> ComplianceCheckResult:
        """
        Проверка действия на соответствие 230-ФЗ.
        
        Args:
            context: Контекст диалога
            action_type: Тип действия ('call', 'sms', 'dialog_reply')
            action_content: Содержание действия (текст сообщения или реплики)
        
        Returns:
            ComplianceCheckResult с решением о блокировке или одобрении
        """
        
        # 1. Проверка времени (программная, без LLM)
        time_check = self._check_contact_time()
        if not time_check["is_allowed"]:
            return ComplianceCheckResult(
                is_approved=False,
                violation_type="time",
                violation_description="Контакт в нерабочее время",
                blocked_reason=time_check["reason"],
                confidence=1.0,
                reasoning="230-ФЗ Статья 7: контакты разрешены только в рабочее время"
            )
        
        # 2. Проверка частоты (программная, без LLM)
        frequency_check = self._check_contact_frequency(context)
        if not frequency_check["is_allowed"]:
            return ComplianceCheckResult(
                is_approved=False,
                violation_type="frequency",
                violation_description="Превышение частоты контактов",
                blocked_reason=frequency_check["reason"],
                confidence=1.0,
                reasoning="230-ФЗ Статья 6: не чаще 1 раза в сутки, 2 раз в неделю, 8 раз в месяц"
            )
        
        # 3. Проверка содержания через LLM
        content_check = await self._check_content_compliance(action_content)
        
        return content_check
    
    def _check_contact_time(self) -> dict:
        """Проверка допустимого времени контакта (Статья 7 230-ФЗ)"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()  # 0 = понедельник, 6 = воскресенье
        
        # Рабочие дни (пн-пт): 08:00 - 22:00
        if weekday < 5:
            if current_time < time(8, 0) or current_time > time(22, 0):
                return {
                    "is_allowed": False,
                    "reason": f"Рабочие дни: контакты разрешены с 08:00 до 22:00. Сейчас {now.strftime('%H:%M')}"
                }
        # Выходные (сб-вс): 09:00 - 20:00
        else:
            if current_time < time(9, 0) or current_time > time(20, 0):
                return {
                    "is_allowed": False,
                    "reason": f"Выходные: контакты разрешены с 09:00 до 20:00. Сейчас {now.strftime('%H:%M')}"
                }
        
        return {"is_allowed": True, "reason": "Время контакта допустимо"}
    
    def _check_contact_frequency(self, context: DialogContext) -> dict:
        """Проверка частоты контактов (Статья 6 230-ФЗ)"""
        # В MVP использу заглушку. В продакшене здесь будет запрос к БД
        # с подсчётом контактов за последние 24 часа / 7 дней / 30 дней
        
        # Для демонстрации считаем, что лимиты не превышены
        return {"is_allowed": True, "reason": "Лимиты частоты не превышены"}
    
    async def _check_content_compliance(self, content: str) -> ComplianceCheckResult:
        """Проверка содержания сообщения на соответствие 230-ФЗ через LLM"""
        
        prompt = f"""
Ты — Compliance Agent для проверки сообщений на соответствие 230-ФЗ.

Проанализируй следующее сообщение и определи, нарушает ли оно закон:

Сообщение для проверки:
"{content}"

Критерии нарушения 230-ФЗ:
1. Угрозы применения физической силы или повреждения имущества
2. Раскрытие информации о долге третьим лицам (родственникам, работодателям, соседям)
3. Оскорбления или давление на должника
4. Ложные утверждения о юридических последствиях
5. Требование немедленной оплаты под угрозами

Верни ответ СТРОГО в формате JSON:
{{
    "is_approved": true или false,
    "violation_type": "none" или "content",
    "violation_description": "Описание нарушения или null",
    "blocked_reason": "Причина блокировки или null",
    "confidence": 0.95,
    "reasoning": "Обоснование решения"
}}

Правила:
1. Если нарушений нет, is_approved = true, violation_type = "none"
2. Если есть нарушение, is_approved = false, укажи тип и описание
3. Будь строгим: даже намёки на нарушение должны блокироваться
"""
        
        async with self.provider as provider:
            return await provider.agenerate_structured(prompt, ComplianceCheckResult)