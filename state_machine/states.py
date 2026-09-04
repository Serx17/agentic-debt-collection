from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class DialogState(str, Enum):
    """Состояния диалога с должником"""
    INITIATION = "initiation"  # Инициация контакта
    IDENTITY_VERIFICATION = "identity_verification"  # Проверка личности
    DEBT_PRESENTATION = "debt_presentation"  # Информирование о долге
    NEGOTIATION = "negotiation"  # Переговоры о погашении
    PROMISE_TO_PAY = "promise_to_pay"  # Получение обещания платежа
    HUMAN_HANDOFF = "human_handoff"  # Передача оператору
    COMPLETED = "completed"  # Диалог завершён успешно
    FAILED = "failed"  # Диалог не удался

class TransitionTrigger(str, Enum):
    """Триггеры перехода между состояниями"""
    CALL_ANSWERED = "call_answered"  # Должник ответил
    IDENTITY_CONFIRMED = "identity_confirmed"  # Личность подтверждена
    IDENTITY_FAILED = "identity_failed"  # Не удалось подтвердить личность
    DEBT_ACKNOWLEDGED = "debt_acknowledged"  # Должник признал долг
    DEBT_DISPUTED = "debt_disputed"  # Должник оспаривает долг
    PAYMENT_AGREED = "payment_agreed"  # Согласился на условия оплаты
    PAYMENT_REFUSED = "payment_refused"  # Отказался от оплаты
    REQUESTED_OPERATOR = "requested_operator"  # Запросил оператора
    CALL_NOT_ANSWERED = "call_not_answered"  # Не ответил на звонок
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"  # Достигнут лимит попыток

class DebtorInfo(BaseModel):
    """Информация о должнике"""
    debtor_id: str
    full_name: str
    phone: str
    debt_amount: float
    debt_currency: str = "RUB"
    overdue_days: int
    last_contact_date: Optional[datetime] = None
    contact_attempts: int = 0
    consent_to_contact: bool = True  # Согласие на взаимодействие

class DialogContext(BaseModel):
    """Контекст текущего диалога"""
    session_id: str
    debtor: DebtorInfo
    current_state: DialogState = DialogState.INITIATION
    previous_state: Optional[DialogState] = None
    state_entered_at: datetime = Field(default_factory=datetime.now)
    
    # Данные, собранные в ходе диалога
    identity_verified: bool = False
    debt_acknowledged: bool = False
    promised_amount: Optional[float] = None
    promised_date: Optional[datetime] = None
    
    # Метаданные
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # История переходов
    transitions: List[dict] = Field(default_factory=list)

class StateTransition(BaseModel):
    """Описание перехода между состояниями"""
    from_state: DialogState
    to_state: DialogState
    trigger: TransitionTrigger
    requires_compliance_check: bool = True  # Нужно ли проверять compliance
    requires_human_handoff: bool = False  # Нужно ли передать оператору
    description: str = ""

# Определяем все возможные переходы
TRANSITIONS = {
    # INITIATION -> IDENTITY_VERIFICATION (должник ответил)
    (DialogState.INITIATION, TransitionTrigger.CALL_ANSWERED): StateTransition(
        from_state=DialogState.INITIATION,
        to_state=DialogState.IDENTITY_VERIFICATION,
        trigger=TransitionTrigger.CALL_ANSWERED,
        requires_compliance_check=True,
        description="Должник ответил на звонок, переходим к проверке личности"
    ),
    
    # IDENTITY_VERIFICATION -> DEBT_PRESENTATION (личность подтверждена)
    (DialogState.IDENTITY_VERIFICATION, TransitionTrigger.IDENTITY_CONFIRMED): StateTransition(
        from_state=DialogState.IDENTITY_VERIFICATION,
        to_state=DialogState.DEBT_PRESENTATION,
        trigger=TransitionTrigger.IDENTITY_CONFIRMED,
        requires_compliance_check=True,
        description="Личность подтверждена, информируем о долге"
    ),
    
    # IDENTITY_VERIFICATION -> HUMAN_HANDOFF (не удалось подтвердить)
    (DialogState.IDENTITY_VERIFICATION, TransitionTrigger.IDENTITY_FAILED): StateTransition(
        from_state=DialogState.IDENTITY_VERIFICATION,
        to_state=DialogState.HUMAN_HANDOFF,
        trigger=TransitionTrigger.IDENTITY_FAILED,
        requires_compliance_check=False,
        requires_human_handoff=True,
        description="Не удалось подтвердить личность, передаём оператору"
    ),
    
    # DEBT_PRESENTATION -> NEGOTIATION (должник признал долг)
    (DialogState.DEBT_PRESENTATION, TransitionTrigger.DEBT_ACKNOWLEDGED): StateTransition(
        from_state=DialogState.DEBT_PRESENTATION,
        to_state=DialogState.NEGOTIATION,
        trigger=TransitionTrigger.DEBT_ACKNOWLEDGED,
        requires_compliance_check=True,
        description="Должник признал долг, переходим к переговорам"
    ),
    
    # DEBT_PRESENTATION -> HUMAN_HANDOFF (должник оспаривает)
    (DialogState.DEBT_PRESENTATION, TransitionTrigger.DEBT_DISPUTED): StateTransition(
        from_state=DialogState.DEBT_PRESENTATION,
        to_state=DialogState.HUMAN_HANDOFF,
        trigger=TransitionTrigger.DEBT_DISPUTED,
        requires_compliance_check=False,
        requires_human_handoff=True,
        description="Должник оспаривает долг, передаём оператору"
    ),
    
    # NEGOTIATION -> PROMISE_TO_PAY (согласился на оплату)
    (DialogState.NEGOTIATION, TransitionTrigger.PAYMENT_AGREED): StateTransition(
        from_state=DialogState.NEGOTIATION,
        to_state=DialogState.PROMISE_TO_PAY,
        trigger=TransitionTrigger.PAYMENT_AGREED,
        requires_compliance_check=True,
        description="Должник согласился на условия оплаты"
    ),
    
    # NEGOTIATION -> HUMAN_HANDOFF (отказался или запросил оператора)
    (DialogState.NEGOTIATION, TransitionTrigger.PAYMENT_REFUSED): StateTransition(
        from_state=DialogState.NEGOTIATION,
        to_state=DialogState.HUMAN_HANDOFF,
        trigger=TransitionTrigger.PAYMENT_REFUSED,
        requires_compliance_check=False,
        requires_human_handoff=True,
        description="Должник отказался, передаём оператору"
    ),
    
    (DialogState.NEGOTIATION, TransitionTrigger.REQUESTED_OPERATOR): StateTransition(
        from_state=DialogState.NEGOTIATION,
        to_state=DialogState.HUMAN_HANDOFF,
        trigger=TransitionTrigger.REQUESTED_OPERATOR,
        requires_compliance_check=False,
        requires_human_handoff=True,
        description="Должник запросил оператора"
    ),
    
    # PROMISE_TO_PAY -> COMPLETED
    (DialogState.PROMISE_TO_PAY, TransitionTrigger.PAYMENT_AGREED): StateTransition(
        from_state=DialogState.PROMISE_TO_PAY,
        to_state=DialogState.COMPLETED,
        trigger=TransitionTrigger.PAYMENT_AGREED,
        requires_compliance_check=True,
        description="Обещание платежа получено, диалог завершён успешно"
    ),
    
    # HUMAN_HANDOFF -> COMPLETED
    (DialogState.HUMAN_HANDOFF, TransitionTrigger.PAYMENT_AGREED): StateTransition(
        from_state=DialogState.HUMAN_HANDOFF,
        to_state=DialogState.COMPLETED,
        trigger=TransitionTrigger.PAYMENT_AGREED,
        requires_compliance_check=False,
        description="Оператор завершил диалог"
    ),
    
    # Любое состояние -> FAILED (не ответил или лимит попыток)
    (DialogState.INITIATION, TransitionTrigger.CALL_NOT_ANSWERED): StateTransition(
        from_state=DialogState.INITIATION,
        to_state=DialogState.FAILED,
        trigger=TransitionTrigger.CALL_NOT_ANSWERED,
        requires_compliance_check=False,
        description="Должник не ответил на звонок"
    ),
    
    (DialogState.INITIATION, TransitionTrigger.MAX_ATTEMPTS_REACHED): StateTransition(
        from_state=DialogState.INITIATION,
        to_state=DialogState.FAILED,
        trigger=TransitionTrigger.MAX_ATTEMPTS_REACHED,
        requires_compliance_check=False,
        description="Достигнут лимит попыток дозвона"
    ),
}

class StateMachine:
    """Управление переходами между состояниями диалога"""
    
    @staticmethod
    def can_transition(current_state: DialogState, trigger: TransitionTrigger) -> bool:
        """Проверяет, возможен ли переход из текущего состояния по триггеру"""
        return (current_state, trigger) in TRANSITIONS
    
    @staticmethod
    def get_transition(current_state: DialogState, trigger: TransitionTrigger) -> Optional[StateTransition]:
        """Возвращает описание перехода, если он возможен"""
        return TRANSITIONS.get((current_state, trigger))
    
    @staticmethod
    def transition(context: DialogContext, trigger: TransitionTrigger) -> DialogContext:
        """
        Выполняет переход в новое состояние.
        Возвращает обновлённый контекст или выбрасывает исключение, если переход невозможен.
        """
        transition = StateMachine.get_transition(context.current_state, trigger)
        
        if not transition:
            raise ValueError(
                f"Невозможный переход: из состояния {context.current_state.value} "
                f"по триггеру {trigger.value}"
            )
        
        # Сохраняем историю
        context.transitions.append({
            "from_state": context.current_state.value,
            "to_state": transition.to_state.value,
            "trigger": trigger.value,
            "timestamp": datetime.now().isoformat()
        })
        
        # Обновляем состояние
        context.previous_state = context.current_state
        context.current_state = transition.to_state
        context.state_entered_at = datetime.now()
        context.updated_at = datetime.now()
        
        return context