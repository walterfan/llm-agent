#!/usr/bin/env python3
"""Demo script for file-based agent memory."""

from app.services.memory import FileMemoryBackend

def main():
    print("🧠 File-Based Agent Memory Demo\n")

    # Initialize memory backend
    memory = FileMemoryBackend()
    agent_id = "weather-assistant"

    print(f"Agent ID: {agent_id}\n")

    # Add some memories
    print("📝 Adding memories...")
    memory.add_memory(
        agent_id,
        "User asked about weather in Beijing. It was sunny, 25°C.",
        metadata={"user_id": "user123", "city": "Beijing"}
    )
    memory.add_memory(
        agent_id,
        "User's favorite color is blue. They mentioned liking outdoor activities.",
        metadata={"user_id": "user123", "type": "preference"}
    )
    memory.add_memory(
        agent_id,
        "User asked about tomorrow's weather. Forecast: cloudy, 22°C.",
        metadata={"user_id": "user123", "city": "Beijing"}
    )

    count = memory.count_memories(agent_id)
    print(f"✅ Added 3 memories. Total: {count}\n")

    # Search memories
    print("🔍 Searching for 'weather'...")
    results = memory.search_memories(agent_id, "weather", limit=3)
    for i, mem in enumerate(results, 1):
        print(f"  {i}. [{mem.timestamp}] {mem.content[:80]}...")
    print()

    print("🔍 Searching for 'favorite'...")
    results = memory.search_memories(agent_id, "favorite", limit=3)
    for i, mem in enumerate(results, 1):
        print(f"  {i}. [{mem.timestamp}] {mem.content[:80]}...")
    print()

    # Get recent memories
    print("📅 Recent memories (last 2):")
    recent = memory.get_recent_memories(agent_id, limit=2)
    for i, mem in enumerate(recent, 1):
        print(f"  {i}. {mem.content[:80]}...")
    print()

    # Storage location
    import os
    storage_dir = os.path.join(memory.base_dir, f"agent_{agent_id}")
    print(f"💾 Memories stored in: {storage_dir}")
    print(f"📊 Total memories: {count}")

    print("\n✅ Demo complete!")

if __name__ == "__main__":
    main()
