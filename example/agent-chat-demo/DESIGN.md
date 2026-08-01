# AI Agent Communication Design

## 1. Overview

This document describes a communication framework for AI agents that supports two scenarios:

| Scenario | Participants | Core Challenge |
|----------|-------------|----------------|
| **Peer Talk** | 2 AI Agents | Auto-stop after reaching conclusion; avoid infinite loops and token waste |
| **Group Chat** | 2 AI Agents + 1 Human | `@mention` routing; human can intervene at any time |

### 1.1 Inspirations from XMPP MUC (XEP-0045)

This design draws heavily from the **XMPP Multi-User Chat (MUC)** protocol, a battle-tested group chat standard. Key borrowed concepts:

| MUC Concept | Our Adaptation |
|-------------|---------------|
| Room JID (`room@service`) | Conversation `room_id` — unique session identifier |
| Occupant JID (`room@service/nick`) | `agent_name` scoped within a room |
| Affiliation (Owner/Admin/Member) | Long-term agent permissions across sessions |
| Role (Moderator/Participant/Visitor) | Session-level speaking rights |
| Presence stanzas | Agent availability status (available/busy/away) |
| Voice mechanism (moderated rooms) | Grant/revoke speaking rights to prevent monopolization |
| Room Subject | Dynamic topic updates mid-conversation |
| Kick/Ban | Remove misbehaving agents |
| Room history on join | Context catch-up via summary for late joiners |

---

## 2. Overall Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Orchestrator                         │
│  ┌───────────┐ ┌──────────┐ ┌──────────────┐            │
│  │  Message   │ │  Router  │ │ Termination  │            │
│  │   Bus      │ │ @mention │ │  Detector    │            │
│  └─────┬─────┘ └────┬─────┘ └──────┬───────┘            │
│        │             │              │                     │
│  ┌─────▼─────────────▼──────────────▼──────────────────┐ │
│  │              Token Budget Manager                    │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │                                  │
│  ┌─────────────────────▼───────────────────────────────┐ │
│  │          Room Manager (from MUC)                     │ │
│  │  ┌────────────┐ ┌──────────┐ ┌───────────────────┐  │ │
│  │  │ Affiliation│ │  Role /  │ │    Presence        │  │ │
│  │  │  Registry  │ │  Voice   │ │    Tracker         │  │ │
│  │  └────────────┘ └──────────┘ └───────────────────┘  │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────────┬─────────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
      ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
      │ Agent A │  │ Agent B │  │  Human  │
      │  (LLM)  │  │  (LLM)  │  │  Proxy  │
      └─────────┘  └─────────┘  └─────────┘
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **Orchestrator** | Manages conversation lifecycle, enforces rules |
| **Message Bus** | Routes messages between participants |
| **Router** | Parses `@mentions`, determines recipients |
| **Termination Detector** | Detects consensus/conclusion to stop conversation |
| **Token Budget Manager** | Tracks token usage, enforces budget limits |
| **Room Manager** ⭐ | Manages rooms, affiliations, roles, presence, voice (from MUC) |
| **Agent** | LLM-powered participant with role-specific system prompt |
| **Human Proxy** | Bridges human I/O into the message bus |

---

## 3. Communication Protocol

### 3.1 Enhanced Message Schema (with MUC concepts)

```json
{
  "id": "msg_001",
  "room_id": "room_rest_vs_grpc_001",
  "sender": "Architect",
  "sender_role": "participant",
  "receiver": "Engineer",
  "content": "I propose we use gRPC for internal services...",
  "msg_type": "CHAT",
  "control_signal": null,
  "mentions": [],
  "thread_id": null,
  "token_count": 45,
  "turn_number": 1,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

New fields borrowed from MUC:

| Field | MUC Origin | Purpose |
|-------|-----------|---------|
| `room_id` | Room JID | Unique conversation identifier |
| `sender_role` | Role | Indicates speaker's current role |
| `msg_type` | Stanza type | CHAT / CONTROL / PRESENCE / TOPIC |
| `mentions` | — | Parsed @mention targets |
| `thread_id` | Thread support | Sub-topic threading |

### 3.2 Message Types (borrowed from XMPP stanza types)

| Type | Description | Example |
|------|-------------|---------|
| `CHAT` | Normal conversation message | "I think REST is better because..." |
| `CONTROL` | Control signal message | `[CONCLUDE]`, `[YIELD]` |
| `PRESENCE` | Agent status change | Agent becomes busy/away/unavailable |
| `TOPIC` | Room topic update | "New topic: Let's discuss deployment strategy" |
| `SYSTEM` | System notification | "Engineer has joined the room" |

### 3.3 Control Signals

| Signal | Meaning | Usage |
|--------|---------|-------|
| `CONCLUDE` | Propose to end the conversation | Agent includes `[CONCLUDE]` in message |
| `AGREE_CONCLUDE` | Agree to end | Other agent responds with `[AGREE_CONCLUDE]` |
| `YIELD` | Give up own position | Agent concedes a point |
| `ESCALATE` | Request human intervention | Agent needs human decision |

### 3.4 Consensus Handshake

```
Agent A: [CONCLUDE] I believe we should use hybrid approach...
Agent B: [AGREE_CONCLUDE] I agree. Summary: gRPC internal, REST external.
→ Orchestrator detects handshake → Conversation ends ✅
```

### 3.5 @Mention Routing Protocol

| Pattern | Behavior | Example |
|---------|----------|---------|
| `@AgentName` | Route to specific agent | `@Architect what do you think?` |
| `@all` | Broadcast to all participants | `@all let's vote on this` |
| No mention | Round-robin or last speaker's partner | Default routing |

---

## 4. XMPP MUC Borrowed Mechanisms

### 4.1 Affiliation & Role — Dual-Layer Permission Model

MUC separates permissions into two layers. We adopt the same pattern:

```
Affiliation (persistent, cross-session)     Role (session-level, per-room)
────────────────────────────────────────    ─────────────────────────────────
  OWNER   — created the conversation         MODERATOR   — controls flow
  ADMIN   — can manage agents                PARTICIPANT — can speak
  MEMBER  — invited participant               OBSERVER    — listen only
  OUTCAST — banned agent
```

**Why two layers?**
- **Affiliation** persists: a human is always the OWNER of conversations they create
- **Role** is dynamic: an agent can be temporarily muted (demoted to OBSERVER) if it monopolizes the conversation

```python
class AgentAffiliation(Enum):
    OWNER = "owner"        # Human who created the conversation
    ADMIN = "admin"        # Orchestrator or privileged agent
    MEMBER = "member"      # Normal participant
    OUTCAST = "outcast"    # Banned agent

class AgentRole(Enum):
    MODERATOR = "moderator"      # Can control turn-taking, end conversation
    PARTICIPANT = "participant"  # Can speak
    OBSERVER = "observer"        # Listen only (like MUC's Visitor)
```

**Key rule:** Only MODERATOR or OWNER can issue `CONCLUDE`, `kick`, or change topics.

### 4.2 Presence Mechanism

MUC uses presence stanzas to track member availability. For AI agents this is critical:

```python
class AgentPresence(Enum):
    AVAILABLE = "available"        # Ready to respond
    BUSY = "busy"                  # Processing, temporarily unavailable
    AWAY = "away"                  # Rate limited or waiting for external resource
    UNAVAILABLE = "unavailable"    # Left the conversation

@dataclass
class PresenceEvent:
    agent_name: str
    status: AgentPresence
    reason: Optional[str] = None   # e.g., "API rate limited, retry in 30s"
    timestamp: datetime
```

**Use cases:**
- Agent hits API rate limit → broadcasts `BUSY` with retry ETA
- Agent's token budget exhausted → broadcasts `UNAVAILABLE`
- Human steps away → `AWAY`, agents pause or continue autonomously

### 4.3 Voice Mechanism (Moderated Room)

In MUC's moderated rooms, only members with "voice" can speak. The moderator grants/revokes voice.

```python
class ModeratedRoom:
    def __init__(self):
        self.voice_set: Set[str] = set()

    async def grant_voice(self, agent_name: str, by: str):
        """Moderator grants speaking rights"""
        self.voice_set.add(agent_name)
        await self.broadcast(SystemMessage(f"{agent_name} can now speak (granted by {by})"))

    async def revoke_voice(self, agent_name: str, by: str, reason: str):
        """Moderator revokes speaking rights — prevents agent monopolization"""
        self.voice_set.discard(agent_name)
        await self.broadcast(SystemMessage(
            f"{agent_name}'s voice revoked by {by}: {reason}"
        ))

    async def handle_message(self, msg: Message):
        if msg.sender not in self.voice_set:
            raise NoVoiceError(f"{msg.sender} does not have voice in this room")
        # ... process message
```

**Anti-monopolization:** If an agent sends 3+ consecutive messages without others speaking, the orchestrator automatically revokes its voice for 1 turn.

### 4.4 Room Join Sequence

MUC defines a strict order of events when joining a room. We adopt this for context catch-up:

```
Step 1: Occupant list     → New agent learns who's in the room
Step 2: Self-presence     → Confirm join success, broadcast to others
Step 3: History summary   → Summarized past messages (not full history, saves tokens)
Step 4: Current topic     → What's being discussed right now
Step 5: Live stream       → Start receiving real-time messages
```

```python
class RoomJoinSequence:
    async def on_agent_join(self, agent: Agent, room: Room):
        # 1. Send occupant list
        await agent.receive(SystemMessage(
            f"Current participants: {', '.join(room.participant_names)}"
        ))

        # 2. Broadcast join event
        await room.broadcast(PresenceEvent(agent.name, AgentPresence.AVAILABLE))

        # 3. Send history summary (compressed to save tokens)
        if room.messages:
            summary = self.summarize_history(room.messages, max_tokens=200)
            await agent.receive(SystemMessage(f"Conversation so far: {summary}"))

        # 4. Send current topic
        await agent.receive(SystemMessage(f"Current topic: {room.topic}"))

        # 5. Add to live participants
        room.add_participant(agent)
```

### 4.5 Dynamic Topic Updates

MUC allows moderators to change the room subject. This maps to redirecting agent discussions:

```python
async def update_topic(self, new_topic: str, requester: str):
    """Only MODERATOR or OWNER can change topic"""
    role = self.get_role(requester)
    if role not in (AgentRole.MODERATOR,) and \
       self.get_affiliation(requester) != AgentAffiliation.OWNER:
        raise PermissionError(f"{requester} cannot change topic")

    self.room.topic = new_topic
    await self.broadcast(TopicMessage(
        content=f"Topic changed to: {new_topic}",
        set_by=requester
    ))
```

**Use case:** Human says `@all New topic: Let's discuss deployment strategy instead` → all agents receive topic update and adjust their responses.

### 4.6 Kick & Ban

```python
async def kick_agent(self, agent_name: str, reason: str, by: str):
    """Remove agent from current session (MUC kick)"""
    await self.broadcast(SystemMessage(f"{agent_name} was kicked: {reason}"))
    self.room.remove_participant(agent_name)

async def ban_agent(self, agent_name: str, reason: str, by: str):
    """Permanently ban agent (MUC ban = set affiliation to outcast)"""
    self.set_affiliation(agent_name, AgentAffiliation.OUTCAST)
    await self.kick_agent(agent_name, reason, by)
```

**Trigger scenarios:**
- Agent produces 3+ meaningless/repetitive messages → auto-kick
- Agent ignores CONCLUDE handshake repeatedly → kick + warning
- Human explicitly requests removal → immediate kick

---

## 5. Main Flows

### 5.1 Peer Talk Flow

```
┌──────────┐                    ┌──────────────┐                    ┌──────────┐
│ Agent A   │                    │ Orchestrator │                    │ Agent B   │
└─────┬─────┘                    └──────┬───────┘                    └─────┬─────┘
      │                                 │                                  │
      │  1. Send message                │                                  │
      │────────────────────────────────>│                                  │
      │                                 │  2. Check termination            │
      │                                 │──────┐                           │
      │                                 │<─────┘ Not terminated            │
      │                                 │                                  │
      │                                 │  3. Route to Agent B             │
      │                                 │─────────────────────────────────>│
      │                                 │                                  │
      │                                 │  4. Agent B responds             │
      │                                 │<─────────────────────────────────│
      │                                 │                                  │
      │                                 │  5. Check termination            │
      │                                 │──────┐                           │
      │                                 │<─────┘ Not terminated            │
      │                                 │                                  │
      │  6. Route to Agent A            │                                  │
      │<────────────────────────────────│                                  │
      │                                 │                                  │
      │         ... (repeat) ...        │                                  │
      │                                 │                                  │
      │  N. [CONCLUDE] proposal         │                                  │
      │────────────────────────────────>│                                  │
      │                                 │─────────────────────────────────>│
      │                                 │                                  │
      │                                 │  N+1. [AGREE_CONCLUDE]           │
      │                                 │<─────────────────────────────────│
      │                                 │                                  │
      │                                 │  ✅ Consensus reached → STOP     │
      │                                 │──────┐                           │
      │                                 │<─────┘                           │
```

### 5.2 Group Chat Flow (with MUC mechanisms)

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐
│  Human    │    │ Orchestrator │    │ Agent A   │    │ Agent B   │
└─────┬─────┘    └──────┬───────┘    └─────┬─────┘    └─────┬─────┘
      │                 │                   │                │
      │  Join room      │                   │                │
      │────────────────>│  [Join sequence]  │                │
      │                 │──────────────────>│                │
      │                 │──────────────────────────────────>│
      │                 │                   │                │
      │  Set topic      │                   │                │
      │────────────────>│  [TOPIC broadcast]│                │
      │                 │──────────────────>│                │
      │                 │──────────────────────────────────>│
      │                 │                   │                │
      │  @AgentA start  │                   │                │
      │────────────────>│  Route to A       │                │
      │                 │──────────────────>│                │
      │                 │                   │                │
      │                 │  A responds @AgentB                │
      │                 │<──────────────────│                │
      │                 │  Route to B       │                │
      │                 │──────────────────────────────────>│
      │                 │                   │                │
      │                 │  B responds @all  │                │
      │                 │<─────────────────────────────────│
      │  [broadcast]    │                   │                │
      │<────────────────│──────────────────>│                │
      │                 │                   │                │
      │                 │  [Voice check: B sent 3 in a row] │
      │                 │  Revoke B's voice │                │
      │                 │──────────────────────────────────>│
      │                 │                   │                │
      │  @all conclude  │                   │                │
      │────────────────>│  [OWNER CONCLUDE] │                │
      │                 │──────────────────>│                │
      │                 │──────────────────────────────────>│
      │                 │                   │                │
      │                 │  ✅ OWNER concluded → STOP        │
```

---

## 6. Termination Conditions (7-Layer Protection)

| Layer | Mechanism | Default | Priority |
|-------|-----------|---------|----------|
| 1. Protocol | `CONCLUDE` + `AGREE_CONCLUDE` handshake | — | Highest |
| 2. Owner override | OWNER sends CONCLUDE → immediate stop | — | Highest |
| 3. Max turns | Per-agent turn limit | 10 | High |
| 4. Token budget | Total conversation token cap | 4000 | High |
| 5. Repetition | Content similarity > threshold | 0.85 | Medium |
| 6. YIELD | Agent concedes, no further argument | — | Medium |
| 7. Consecutive limit | Same agent speaks N times without others | 6 | Low |
| 8. Timeout | Wall-clock time limit | 300s | Low |

---

## 7. Agent System Prompt Template

```
You are {agent_name}, a {role_description}.

## Room Context
- Room: {room_id}
- Topic: {topic}
- Your role: {role} (affiliation: {affiliation})
- Other participants: {participant_list}

## Communication Rules
1. Stay focused on the topic. If the topic changes, adapt.
2. Use @AgentName to direct messages to specific participants.
3. Use @all to broadcast to everyone.
4. When you believe a conclusion has been reached, include [CONCLUDE]
   followed by a clear summary.
5. If another agent proposes [CONCLUDE] and you agree, respond with
   [AGREE_CONCLUDE].
6. If you change your mind or concede, include [YIELD].
7. If you need human input, include [ESCALATE].

## Presence Awareness
- If another agent is BUSY, wait for them before expecting a response.
- If you encounter an error, signal [ESCALATE] rather than retrying endlessly.

## Budget Awareness
- Be concise. You have a limited token budget.
- Avoid repeating points already made.
- Aim for conclusion within {max_turns} turns.
```

---

## 8. Code Examples

### 8.1 Project Structure

```
agent-chat-demo/
├── DESIGN.md              # This document
├── README.md              # Quick start guide
├── requirements.txt       # Dependencies
├── config.py              # Configuration constants
├── protocol.py            # Message types, control signals, presence
├── room.py                # Room manager with MUC features
├── termination.py         # 7-layer termination detector
├── agent.py               # AI Agent class
├── orchestrator.py        # Conversation orchestrator
├── demo_peer_talk.py      # Demo 1: Two agents discuss
├── demo_group_chat.py     # Demo 2: 2 AI + 1 Human
└── demo_mock.py           # Demo 3: No API key needed
```

### 8.2 Enhanced Protocol (protocol.py)

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

class MessageType(Enum):
    CHAT = "chat"
    CONTROL = "control"
    PRESENCE = "presence"
    TOPIC = "topic"
    SYSTEM = "system"

class ControlSignal(Enum):
    CONCLUDE = "CONCLUDE"
    AGREE_CONCLUDE = "AGREE_CONCLUDE"
    YIELD = "YIELD"
    ESCALATE = "ESCALATE"

class AgentAffiliation(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    OUTCAST = "outcast"

class AgentRole(Enum):
    MODERATOR = "moderator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"

class AgentPresence(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    UNAVAILABLE = "unavailable"

@dataclass
class Message:
    id: str
    room_id: str
    sender: str
    receiver: str                              # agent_name or "ALL"
    content: str
    msg_type: MessageType = MessageType.CHAT
    sender_role: AgentRole = AgentRole.PARTICIPANT
    control_signal: Optional[ControlSignal] = None
    mentions: List[str] = field(default_factory=list)
    thread_id: Optional[str] = None
    token_count: int = 0
    turn_number: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
```

### 8.3 Room Manager (room.py) — MUC-inspired

```python
class Room:
    def __init__(self, room_id: str, topic: str):
        self.room_id = room_id
        self.topic = topic
        self.participants: Dict[str, ParticipantInfo] = {}
        self.messages: List[Message] = []
        self.voice_set: Set[str] = set()
        self.is_moderated: bool = False

    def add_participant(self, name, affiliation, role):
        self.participants[name] = ParticipantInfo(name, affiliation, role)
        if role != AgentRole.OBSERVER:
            self.voice_set.add(name)

    def has_voice(self, name: str) -> bool:
        if not self.is_moderated:
            return True
        return name in self.voice_set

    def grant_voice(self, name: str):
        self.voice_set.add(name)

    def revoke_voice(self, name: str):
        self.voice_set.discard(name)

    def update_topic(self, new_topic: str, by: str):
        p = self.participants.get(by)
        if p and (p.role == AgentRole.MODERATOR or
                  p.affiliation == AgentAffiliation.OWNER):
            self.topic = new_topic
            return True
        return False

    def kick(self, name: str):
        self.participants.pop(name, None)
        self.voice_set.discard(name)
```

### 8.4 Termination Detector

```python
class TerminationDetector:
    def should_stop(self, messages, config, start_time) -> Tuple[bool, str]:
        # Layer 1: CONCLUDE + AGREE_CONCLUDE handshake
        # Layer 2: Owner CONCLUDE (immediate)
        # Layer 3: Max turns exceeded
        # Layer 4: Token budget exceeded
        # Layer 5: Repetition detected (similarity > 0.85)
        # Layer 6: YIELD with no counter-argument
        # Layer 7: Consecutive same-agent messages
        # Layer 8: Wall-clock timeout
        ...
```

---

## 9. Recommended Technology Stack

| Layer | Python | TypeScript |
|-------|--------|------------|
| Agent Framework | AutoGen / CrewAI | LangGraph.js |
| LLM Client | `openai`, `anthropic` | `@ai-sdk/openai` |
| Embedding (similarity) | `sentence-transformers` | `@xenova/transformers` |
| Orchestration | Custom / AutoGen GroupChat | LangGraph StateGraph |
| Message Bus | `asyncio.Queue` / Redis Streams | BullMQ / Redis Streams |
| Presence / Pub-Sub | Redis Pub/Sub | Redis Pub/Sub / WebSocket |
| UI | Gradio / Chainlit | Next.js + Vercel AI SDK |

---

## 10. Design Principles

1. **Human-in-the-loop**: Human always has OWNER affiliation and can override any decision
2. **Fail-safe termination**: 8 layers of protection ensure conversations always end
3. **Token economy**: Every message is budgeted; agents are prompted to be concise
4. **Protocol-driven**: Explicit control signals, not heuristic-only detection
5. **MUC-proven patterns**: Affiliation/Role/Presence/Voice are battle-tested in 20+ years of XMPP

---

## 11. Comparison: Before vs After MUC Integration

| Feature | Original Design | + MUC Enhancements |
|---------|----------------|-------------------|
| Identity | `agent_name` only | `agent_name` + `room_id` (occupant JID) |
| Permissions | None | Affiliation + Role dual-layer model |
| Speaking control | Round-robin / @mention | + Voice mechanism (moderated room) |
| Status tracking | None | Presence mechanism (available/busy/away) |
| Join flow | Start immediately | Ordered sequence (occupants → history → topic → live) |
| Anti-monopolization | Consecutive message limit | + Voice revoke + Kick |
| Topic management | Fixed topic | Dynamic topic updates by moderator/owner |
| Thread support | None | `thread_id` for sub-topics |
| Misbehavior handling | None | Kick + Ban |

---

## 12. Future Enhancements

- [ ] **Persistent rooms**: Save room state to database for long-running discussions
- [ ] **Agent discovery**: Registry service for finding available agents by capability
- [ ] **Federation**: Cross-system agent communication (like XMPP server federation)
- [ ] **Message archive (MAM)**: Searchable conversation history (XEP-0313 inspired)
- [ ] **End-to-end encryption**: OMEMO-like encryption for sensitive agent discussions
- [ ] **Service discovery**: Agents advertise capabilities (like XMPP disco, XEP-0030)
- [ ] **PubSub topics**: Agents subscribe to topics of interest (XEP-0060 inspired)
