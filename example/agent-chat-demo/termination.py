"""Termination detection for agent conversations.

Implements 7 layers of protection against infinite loops:
1. Protocol: CONCLUDE + AGREE_CONCLUDE handshake
2. Turn limit
3. Token budget
4. Repetition detection
5. YIELD signal
6. Consecutive agent message limit
7. Timeout
"""

import time
from difflib import SequenceMatcher
from typing import List, Tuple

import config
from protocol import ControlSignal, Message


class TerminationDetector:
    """Detects when a conversation should stop."""

    def __init__(self):
        self.start_time = time.time()

    def should_stop(self, messages: List[Message], total_tokens: int) -> Tuple[bool, str]:
        """Check all termination conditions. Returns (should_stop, reason)."""

        # Layer 1: Protocol consensus — CONCLUDE + AGREE_CONCLUDE
        if self._check_consensus(messages):
            return True, "consensus_reached"

        # Layer 2: Turn limit
        turn_count = len([m for m in messages if m.sender != "SYSTEM"])
        if turn_count >= config.MAX_TOTAL_TURNS:
            return True, f"max_turns_reached ({config.MAX_TOTAL_TURNS})"

        # Layer 3: Token budget
        if total_tokens >= config.TOKEN_BUDGET:
            return True, f"token_budget_exceeded ({total_tokens}/{config.TOKEN_BUDGET})"

        # Layer 4: Repetition detection
        if self._check_repetition(messages):
            return True, "repetition_detected"

        # Layer 5: YIELD signal
        if self._check_yield(messages):
            return True, "agent_yielded"

        # Layer 6: Consecutive agent messages without human
        if self._check_consecutive(messages):
            return True, f"max_consecutive_agent_msgs ({config.MAX_CONSECUTIVE_AGENT_MSGS})"

        # Layer 7: Timeout
        elapsed = time.time() - self.start_time
        if elapsed >= config.TIMEOUT_SECONDS:
            return True, f"timeout ({config.TIMEOUT_SECONDS}s)"

        return False, ""

    def _check_consensus(self, messages: List[Message]) -> bool:
        """Check if CONCLUDE was followed by AGREE_CONCLUDE."""
        conclude_seen = False
        for msg in messages:
            msg.extract_signal()
            if msg.has_signal(ControlSignal.CONCLUDE):
                conclude_seen = True
            if conclude_seen and msg.has_signal(ControlSignal.AGREE_CONCLUDE):
                return True
            # Reset if conclusion was rejected
            if msg.has_signal(ControlSignal.REJECT_CONCLUDE):
                conclude_seen = False
        return False

    def _check_repetition(self, messages: List[Message]) -> bool:
        """Detect if recent messages are too similar."""
        chat_msgs = [m for m in messages if m.sender != "SYSTEM"]
        if len(chat_msgs) < 4:
            return False

        recent = chat_msgs[-4:]
        for i in range(len(recent)):
            for j in range(i + 1, len(recent)):
                ratio = SequenceMatcher(
                    None,
                    recent[i].content.lower(),
                    recent[j].content.lower(),
                ).ratio()
                if ratio > config.SIMILARITY_THRESHOLD:
                    return True
        return False

    def _check_yield(self, messages: List[Message]) -> bool:
        """Check if any agent yielded."""
        if not messages:
            return False
        last = messages[-1]
        last.extract_signal()
        return last.has_signal(ControlSignal.YIELD)

    def _check_consecutive(self, messages: List[Message]) -> bool:
        """Check if too many consecutive agent messages without human input."""
        agent_streak = 0
        for msg in reversed(messages):
            if msg.sender == "HUMAN" or msg.sender == "SYSTEM":
                break
            agent_streak += 1
        return agent_streak >= config.MAX_CONSECUTIVE_AGENT_MSGS
