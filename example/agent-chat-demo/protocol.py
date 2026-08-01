"""Communication protocol for agent chat."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class ControlSignal(Enum):
    """Control signals for conversation flow."""
    CONCLUDE = "CONCLUDE"
    AGREE_CONCLUDE = "AGREE_CONCLUDE"
    REJECT_CONCLUDE = "REJECT_CONCLUDE"
    YIELD = "YIELD"


class MessageType(Enum):
    """Message types."""
    CHAT = "chat"
    SYSTEM = "system"
    CONTROL = "control"


@dataclass
class Message:
    """A single message in the conversation."""
    sender: str
    receiver: str  # agent name, "ALL", or "HUMAN"
    content: str
    msg_type: MessageType = MessageType.CHAT
    control_signal: Optional[ControlSignal] = None
    token_count: int = 0
    turn_number: int = 0
    timestamp: float = field(default_factory=time.time)

    def has_signal(self, signal: ControlSignal) -> bool:
        """Check if message contains a control signal (in content or field)."""
        if self.control_signal == signal:
            return True
        return f"[{signal.value}]" in self.content

    def extract_signal(self) -> Optional[ControlSignal]:
        """Extract control signal from message content."""
        for signal in ControlSignal:
            if f"[{signal.value}]" in self.content:
                self.control_signal = signal
                return signal
        return self.control_signal

    def __str__(self) -> str:
        sig = f" ({self.control_signal.value})" if self.control_signal else ""
        return f"[{self.sender} → {self.receiver}]{sig}: {self.content[:100]}..."


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for English."""
    return max(1, len(text) // 4)
