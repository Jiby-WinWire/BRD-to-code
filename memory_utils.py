"""
Memory Utilities
Command-line tools for querying and managing mem0 memories
"""

import sys
import json
from pathlib import Path
from typing import Optional, List
import argparse
from datetime import datetime

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "agents"))

from mem0_manager import create_memory_manager


def search_memories(user_id: str, query: str, limit: int = 10):
    """
    Search memories by query
    
    Args:
        user_id: User identifier
        query: Search query
        limit: Maximum number of results
    """
    print(f"\n🔍 Searching memories for: '{query}'")
    print(f"👤 User: {user_id}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    memories = manager.get_relevant_memories(query=query, limit=limit)
    
    if not memories:
        print("No memories found.")
        return
    
    print(f"\nFound {len(memories)} relevant memories:\n")
    
    for i, mem in enumerate(memories, 1):
        print(f"{'='*80}")
        print(f"Memory #{i}")
        print(f"{'='*80}")
        print(f"Content: {mem.get('content', 'N/A')}")
        print(f"Relevance Score: {mem.get('score', 0.0):.4f}")
        
        metadata = mem.get('metadata', {})
        if metadata:
            print(f"Metadata:")
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
        
        print()


def list_all_memories(user_id: str, limit: int = 50):
    """
    List all memories for a user
    
    Args:
        user_id: User identifier
        limit: Maximum number of memories to display
    """
    print(f"\n📚 Listing all memories")
    print(f"👤 User: {user_id}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    memories = manager.get_all_memories(limit=limit)
    
    if not memories:
        print("No memories found.")
        return
    
    print(f"\nTotal memories: {len(memories)}\n")
    
    for i, mem in enumerate(memories, 1):
        print(f"{i}. [{mem.get('created_at', 'N/A')}]")
        print(f"   {mem.get('content', 'N/A')[:150]}...")
        
        metadata = mem.get('metadata', {})
        if metadata.get('agent'):
            print(f"   Agent: {metadata['agent']}")
        
        print()


def get_memory_statistics(user_id: str):
    """
    Get memory statistics for a user
    
    Args:
        user_id: User identifier
    """
    print(f"\n📊 Memory Statistics")
    print(f"👤 User: {user_id}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    stats = manager.get_memory_stats()
    
    print(f"\nTotal Memories: {stats.get('total_memories', 0)}")
    print(f"Session ID: {stats.get('session_id', 'N/A')}")
    
    agents = stats.get('agents', [])
    if agents:
        print(f"\nAgents Involved:")
        for agent in agents:
            print(f"  - {agent}")
    
    memory_types = stats.get('memory_types', {})
    if memory_types:
        print(f"\nMemory Types:")
        for mem_type, count in memory_types.items():
            print(f"  - {mem_type}: {count}")


def get_conversation_history(user_id: str, session_id: Optional[str] = None, limit: int = 20):
    """
    Get conversation history for a user/session
    
    Args:
        user_id: User identifier
        session_id: Optional session identifier
        limit: Maximum number of messages
    """
    print(f"\n💬 Conversation History")
    print(f"👤 User: {user_id}")
    if session_id:
        print(f"📅 Session: {session_id}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    if session_id:
        manager.set_session(session_id)
    
    history = manager.get_conversation_history(limit=limit)
    
    if not history:
        print("No conversation history found.")
        return
    
    print(f"\nShowing last {len(history)} messages:\n")
    
    for i, msg in enumerate(history, 1):
        metadata = msg.get('metadata', {})
        timestamp = metadata.get('timestamp', 'N/A')
        agent = metadata.get('agent', 'unknown')
        
        print(f"[{timestamp}] [{agent}]")
        print(f"{msg.get('content', 'N/A')}")
        print()


def delete_memory(user_id: str, memory_id: str):
    """
    Delete a specific memory
    
    Args:
        user_id: User identifier
        memory_id: Memory ID to delete
    """
    print(f"\n🗑️  Deleting Memory")
    print(f"👤 User: {user_id}")
    print(f"🆔 Memory ID: {memory_id}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    result = manager.delete_memory(memory_id)
    
    if result.get('success'):
        print("\n✅ Memory deleted successfully")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")


def export_memories(user_id: str, output_file: str, limit: int = 1000):
    """
    Export memories to a JSON file
    
    Args:
        user_id: User identifier
        output_file: Output file path
        limit: Maximum number of memories to export
    """
    print(f"\n💾 Exporting Memories")
    print(f"👤 User: {user_id}")
    print(f"📁 Output: {output_file}")
    print("-" * 80)
    
    manager = create_memory_manager(user_id=user_id)
    memories = manager.get_all_memories(limit=limit)
    stats = manager.get_memory_stats()
    
    export_data = {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "total_memories": len(memories),
        "statistics": stats,
        "memories": memories
    }
    
    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Exported {len(memories)} memories to {output_file}")


def main():
    """Main CLI interface"""
    
    parser = argparse.ArgumentParser(
        description="Memory Utilities - Query and manage mem0 memories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search memories
  python memory_utils.py search "todo application" --user john_doe

  # List all memories
  python memory_utils.py list --user john_doe

  # Get statistics
  python memory_utils.py stats --user john_doe

  # Get conversation history
  python memory_utils.py history --user john_doe --session supervisor-20260428-144000

  # Export memories
  python memory_utils.py export memories.json --user john_doe

  # Delete a memory
  python memory_utils.py delete mem_12345 --user john_doe
        """
    )
    
    parser.add_argument('command', choices=['search', 'list', 'stats', 'history', 'export', 'delete'],
                      help='Command to execute')
    parser.add_argument('query', nargs='?', help='Search query or memory ID (for delete) or filename (for export)')
    parser.add_argument('--user', '-u', required=True, help='User ID')
    parser.add_argument('--session', '-s', help='Session ID (for history command)')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Maximum number of results')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'search':
            if not args.query:
                parser.error("Search command requires a query")
            search_memories(args.user, args.query, args.limit)
            
        elif args.command == 'list':
            list_all_memories(args.user, args.limit)
            
        elif args.command == 'stats':
            get_memory_statistics(args.user)
            
        elif args.command == 'history':
            get_conversation_history(args.user, args.session, args.limit)
            
        elif args.command == 'export':
            if not args.query:
                parser.error("Export command requires a filename")
            export_memories(args.user, args.query, args.limit)
            
        elif args.command == 'delete':
            if not args.query:
                parser.error("Delete command requires a memory ID")
            delete_memory(args.user, args.query)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        sys.argv.append('--help')
    
    main()
