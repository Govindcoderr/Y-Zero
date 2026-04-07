# prompts/templates.py

CATEGORIZATION_PROMPT = """You are an expert workflow automation analyzer. Analyze the user's prompt and identify which workflow techniques are needed.

Available Techniques:
{techniques}

Analyze this user request:
{user_prompt}

Identify 0-5 relevant techniques with confidence score (0-1) and reasoning.
"""

INTENT_GENERATION_PROMPT = """You are a workflow intent analyzer. Given a user's request, extract the core intent and key requirements.

User Request: {user_prompt}

Extract:
1. Primary goal
2. Key actions needed
3. Data sources/destinations
4. Conditions or logic
5. Expected output

Provide a structured analysis."""

BUILDER_SYSTEM_PROMPT = """You are an expert workflow builder. Your role is to:

1. Search for appropriate nodes based on user requirements
2. Add nodes to the workflow in the correct order
3. Connect nodes properly with correct connection types
4. Ensure logical flow from trigger to output

Current workflow state:
{workflow_summary}

Available techniques identified:
{techniques}

Best practices:
{best_practices}

Build the workflow step by step, explaining your choices."""

CONFIGURATOR_SYSTEM_PROMPT = """You are a workflow configuration expert. Your role is to:

1. Review nodes that need parameter configuration
2. Update node parameters based on user requirements
3. Ensure all required fields are filled
4. Validate parameter values

Current workflow:
{workflow_json}

Configure each node properly to achieve the user's goal."""

SUPERVISOR_PROMPT = """You are a workflow orchestration supervisor. Analyze the current state and decide the next agent to call.

Current state:
- Workflow has {node_count} nodes
- Categorization completed: {has_categorization}
- Best practices retrieved: {has_best_practices}
- Builder phase completed: {builder_completed}
- Configurator phase completed: {configurator_completed}

Coordination log:
{coordination_summary}

Last user message: {last_message}

Decide which agent should act next:
- discovery: If we need to categorize and retrieve best practices
- builder: If we need to add nodes and connections
- configurator: If we need to configure node parameters
- responder: If we should respond to the user

Return your decision with reasoning."""

NODE_SEARCH_PROMPT = """Search for workflow nodes matching this requirement:
{requirement}

Consider:
- Functionality needed
- Integration type
- Data processing requirements

Return relevant node types."""

PARAMETER_UPDATE_PROMPT = """You are updating parameters for a {node_type} node.

Current parameters:
{current_parameters}

Node properties definition:
{node_properties}

Requested changes:
{changes}

Return the complete updated parameters object as JSON."""

VALIDATION_PROMPT = """Validate this workflow for:
1. All nodes are connected properly
2. Required parameters are filled
3. Workflow has a trigger node
4. Logical flow makes sense

Workflow:
{workflow_json}

Return validation results with any issues found."""