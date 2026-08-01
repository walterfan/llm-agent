"""
MUC Room — inspired by XMPP XEP-0045 Multi-User Chat.

Core concepts borrowed from MUC:
  - Room JID        → room_id
  - Occupant JID    → agent_name within room
  - Affiliation     → long-term relationship (owner/admin/member/outcast)
  - Role            → session-level capability (moderator/participant/observer)
  - Voice           → permission to speak in a moderated room
  - Presence        → agent availability status
  - Room Subject    → current discussion topic
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

from protocol import (
    AgentAffiliation,
    AgentPresence,
    AgentRole,
    ControlSignal,
    Message,
    MessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class RoomMember:
    """An occupant inside a MUC room."""
    name: str
    affiliation: AgentAffiliation = AgentAffiliation.MEMBER
    role: AgentRole = AgentRole.PARTICIPANT
    presence: AgentPresence = AgentPresence.AVAILABLE
    has_voice: bool = True
    joined_at: datetime = field(default_factory=datetime.now)
    consecutive_turns: int = 0

    @property
    def can_speak(self) -> bool:
        return (
            self.has_voice
            and self.presence == AgentPresence.AVAILABLE
            and self.role != AgentRole.OBSERVER
        )

    @property
    def is_moderator(self) -> bool:
        return self.role == AgentRole.MODERATOR


class MUCRoom:
    """
    A multi-user chat room that manages members, voice, presence,
    topic, and message history.
    """

    def __init__(self, room_id: str, topic: str = ""):
        self.room_id = room_id
        self.topic = topic
        self.members: Dict[str, RoomMember] = {}
        self.ban_list: Set[str] = set()
        self.messages: List[Message] = []
        self.created_at = datetime.now()
        self._turn_counter = 0

    # ── Join / Leave ─────────────────────────────────────────────

    def join(
        self,
        name: str,
        affiliation: AgentAffiliation = AgentAffiliation.MEMBER,
        role: Optional[AgentRole] = None,
    ) -> List[Message]:
        """
        Agent joins the room.  Returns the ordered join-sequence events
        (occupant list, self-presence, history summary, topic).
        """
        if name in self.ban_list:
            raise PermissionError(f"{name} is banned from room {self.room_id}")

        if role is None:
            role = (
                AgentRole.MODERATOR
                if affiliation in (AgentAffiliation.OWNER, AgentAffiliation.ADMIN)
                else AgentRole.PARTICIPANT
            )

        member = RoomMember(name=name, affiliation=affiliation, role=role)
        self.members[name] = member

        events: List[Message] = []

        # 1. Occupant list
        occupant_names = [m.name for m in self.members.values() if m.name != name]
        events.append(self._system_msg(
            f"Current participants: {', '.join(occupant_names) if occupant_names else '(empty)'}",
            receiver=name,
        ))

        # 2. Self-presence confirmation
        events.append(self._system_msg(
            f"{name} joined as {role.value} ({affiliation.value})",
            receiver="ALL",
            msg_type=MessageType.PRESENCE,
        ))

        # 3. History summary (last N messages)
        if self.messages:
            summary_lines = []
            for m in self.messages[-5:]:
                summary_lines.append(f"  [{m.sender}]: {m.content[:80]}...")
            events.append(self._system_msg(
                "Recent history:\n" + "\n".join(summary_lines),
                receiver=name,
            ))

        # 4. Current topic
        if self.topic:
            events.append(self._system_msg(
                f"Current topic: {self.topic}",
                receiver=name,
                msg_type=MessageType.TOPIC,
            ))

        logger.info("Room %s: %s joined (%s/%s)", self.room_id, name, affiliation.value, role.value)
        return events

    def leave(self, name: str) -> Message:
        if name in self.members:
            del self.members[name]
        return self._system_msg(f"{name} left the room", receiver="ALL", msg_type=MessageType.PRESENCE)

    # ── Voice ────────────────────────────────────────────────────

    def grant_voice(self, target: str, by: str) -> Message:
        self._require_moderator(by)
        if target in self.members:
            self.members[target].has_voice = True
            logger.info("Room %s: voice granted to %s by %s", self.room_id, target, by)
        return self._system_msg(f"{by} granted voice to {target}", receiver="ALL")

    def revoke_voice(self, target: str, by: str, reason: str = "") -> Message:
        self._require_moderator(by)
        if target in self.members:
            self.members[target].has_voice = False
            logger.info("Room %s: voice revoked from %s by %s (%s)", self.room_id, target, by, reason)
        reason_str = f" (reason: {reason})" if reason else ""
        return self._system_msg(f"{by} revoked voice from {target}{reason_str}", receiver="ALL")

    def check_voice(self, name: str) -> bool:
        member = self.members.get(name)
        return member.can_speak if member else False

    # ── Presence ─────────────────────────────────────────────────

    def update_presence(self, name: str, status: AgentPresence, reason: str = "") -> Message:
        if name in self.members:
            self.members[name].presence = status
        reason_str = f" ({reason})" if reason else ""
        return self._system_msg(
            f"{name} is now {status.value}{reason_str}",
            receiver="ALL",
            msg_type=MessageType.PRESENCE,
        )

    # ── Topic ────────────────────────────────────────────────────

    def set_topic(self, new_topic: str, by: str) -> Message:
        self._require_moderator(by)
        old_topic = self.topic
        self.topic = new_topic
        logger.info("Room %s: topic changed by %s: '%s' → '%s'", self.room_id, by, old_topic, new_topic)
        return self._system_msg(
            f"{by} changed topic to: {new_topic}",
            receiver="ALL",
            msg_type=MessageType.TOPIC,
        )

    # ── Kick / Ban ───────────────────────────────────────────────

    def kick(self, target: str, by: str, reason: str = "") -> Message:
        self._require_moderator(by)
        if target in self.members:
            del self.members[target]
        reason_str = f" (reason: {reason})" if reason else ""
        return self._system_msg(f"{target} was kicked by {by}{reason_str}", receiver="ALL")

    def ban(self, target: str, by: str, reason: str = "") -> Message:
        self._require_moderator(by)
        self.ban_list.add(target)
        if target in self.members:
            del self.members[target]
        reason_str = f" (reason: {reason})" if reason else ""
        return self._system_msg(f"{target} was banned by {by}{reason_str}", receiver="ALL")

    # ── Message handling ─────────────────────────────────────────

    def add_message(self, msg: Message) -> None:
        msg.room_id = self.room_id
        self._turn_counter += 1
        msg.turn_number = self._turn_counter
        self.messages.append(msg)

        # Track consecutive turns
        if msg.sender in self.members:
            member = self.members[msg.sender]
            member.consecutive_turns += 1
            # Reset others
            for name, m in self.members.items():
                if name != msg.sender:
                    m.consecutive_turns = 0

    @property
    def turn_count(self) -> int:
        return self._turn_counter

    @property
    def active_members(self) -> List[RoomMember]:
        return [m for m in self.members.values() if m.presence == AgentPresence.AVAILABLE]

    @property
    def agent_members(self) -> List[RoomMember]:
        """Non-owner (non-human) active members."""
        return [
            m for m in self.members.values()
            if m.affiliation != AgentAffiliation.OWNER and m.presence == AgentPresence.AVAILABLE
        ]

    # ── Internal helpers ─────────────────────────────────────────

    def _require_moderator(self, name: str) -> None:
        member = self.members.get(name)
        if not member or not member.is_moderator:
            raise PermissionError(f"{name} is not a moderator in room {self.room_id}")

    def _system_msg(
        self,
        content: str,
        receiver: str = "ALL",
        msg_type: MessageType = MessageType.SYSTEM,
    ) -> Message:
        return Message(
            sender="SYSTEM",
            receiver=receiver,
            content=content,
            msg_type=msg_type,
            room_id=self.room_id,
        )
