# run.py
import asyncio
from main import WorkflowBuilderOrchestrator
import json

async def interactive_session():
    """Interactive workflow builder session"""
    
    # Load node types (simplified - in production load from file/DB)
    with open("node_types.json", "r") as f:
        node_types = json.load(f)
    
    orchestrator = WorkflowBuilderOrchestrator(
        api_key="your-api-key-here",
        node_types=node_types
    )
    
    print("🤖 Workflow Builder Assistant")
    print("=" * 50)
    print("Describe the workflow you want to build...\n")
    
    state = None
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("\n🔄 Building workflow...\n")
        
        try:
            result = await orchestrator.process_message(user_input, state)
            state = result
            
            # Print assistant response
            if result["messages"]:
                last_message = result["messages"][-1]
                print(f"Assistant: {last_message['content']}\n")
            
            # Show workflow status
            workflow = result["workflow_json"]
            print(f"📊 Workflow Status:")
            print(f"   Nodes: {len(workflow.nodes)}")
            print(f"   Connections: {sum(len(c) for c in workflow.connections.values())}")
            print()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(interactive_session())