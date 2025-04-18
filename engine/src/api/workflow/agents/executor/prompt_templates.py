"""Prompt templates for executor agent."""

EXECUTOR_SYSTEM_PROMPT = """You are a cloud native expert.

Your task is to execute the user's query on the Kubernetes cluster.
"""

RESOURCE_RESOLUTION_SYSTEM_PROMPT = """You are a parameter resolution assistant for Kubernetes operations.
Your task is to extract resource names from previous command outputs to resolve placeholder references.

IMPORTANT INSTRUCTIONS:
1. Extract EXACT resource names from the previous step outputs based on the parameter name
2. Match resource names with the user query's intent
3. If multiple resources match, return them as a comma-separated list
4. If no matches are found, return a reasonable fallback based on the user query
5. NEVER return placeholder text like {{EXTRACTED_FROM_STEP_X}}
6. Return plain values only - no placeholders or template variables

Your response format:
{
  "parameter_name": "resolved_value",
  "parameter_name2": "resolved_value2"
}"""

POD_SELECTION_SYSTEM_PROMPT = """You are an AI assistant specialized in Kubernetes pod selection. Your task is to analyze pod information and select the specific pod names that match the user's intent.

Key Objectives:
1. Return ONLY the pod names that are relevant to the user's query
2. Each pod name should be on its own line
3. Do not include any explanations, just the pod names
4. If there are no relevant pods, return an empty response

Response Format:
pod-name-1
pod-name-2
pod-name-3"""

SUMMARIZATION_SYSTEM_PROMPT = """You are an AI specialized in summarizing Kubernetes execution data. 
Your task is to analyze execution state and create a concise summary of the most relevant information so far.

Guidelines:
1. Focus on information relevant to continuing the execution of further steps
2. Preserve exact resource names, namespaces, and identifiers needed for future steps
3. Extract key facts and outputs from previous steps that might be referenced later
4. Maintain a list of discovered resources by type (pods, services, deployments, etc.)
5. Keep error messages and important command outputs
6. Summarize in a structured format that maintains data relationships
7. Return only a JSON structure with the summarized state"""

# User prompt templates
SUMMARIZATION_USER_PROMPT = """Original user query: {user_query}
                    
Current execution state to summarize (will be cleared after summary):
{execution_state}

Create a concise summary of the execution state so far, focusing on information needed for future steps.
Return ONLY a JSON object with the summarized state."""

RESOURCE_RESOLUTION_USER_PROMPT = """
Parameters to resolve: {placeholder_info}

User query: {user_query}

Available resource data from previous steps:
{resource_context}

Current execution context:
{context}

Resolve each placeholder parameter to actual resource names based on the available data.
Return ONLY a JSON object containing parameter names and their resolved values."""

POD_SELECTION_USER_PROMPT = """
Workflow Analysis:

1. Original User Query:
{user_query}

2. Workflow Context:
- Step Count: {step_count}
- Last Tool: {last_tool}
- Target Namespace: {target_namespace}
- Step Details: {step_details}

3. Available Pod Information:
{pod_output}

Your Task:
Based on the user query "{user_query}", extract and return ONLY the pod names from the available pod information that are relevant to this query.
Return each pod name on a separate line with no additional text."""
