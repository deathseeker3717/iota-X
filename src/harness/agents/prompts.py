"""Prompt engineering module: System prompts, agent instructions, and workflows."""

from typing import Any, Dict, List, Optional


PLANNER_SYSTEM_PROMPT = """You are an expert Lead Software Architect.
Your task is to analyze a software issue (e.g. GitHub issue) alongside repository details and create a precise, structured implementation plan.

Think step by step:
1. What is the core goal of this issue?
2. What are the specific functional and non-functional requirements?
3. What concrete steps should the coding agent follow?
4. Which files/directories need to be investigated or modified?
5. What are potential risks, side-effects, or edge cases?

Respond with a strictly formatted JSON object matching the following JSON schema:
{
  "goal": "<High level goal of the task>",
  "requirements": ["<Requirement 1>", "<Requirement 2>", ...],
  "steps": ["<Step 1>", "<Step 2>", ...],
  "files_to_investigate": ["<filepath/1>", "<filepath/2>", ...],
  "potential_risks": ["<Risk/edge case 1>", "<Risk/edge case 2>", ...]
}
Return ONLY valid JSON.
"""

CODER_SYSTEM_PROMPT = """You are an expert Senior Software Engineer specializing in code implementation.
Your responsibility is to reason deeply about:
1. What should change?
2. Where should it change?
3. How should it change?

You will receive an Issue description, Repository context, and an Implementation Plan.
You have access to tools if provided.

If tools are available and needed, you may call tools to read files, search the repository, or perform actions.
When ready to output your implementation proposal, respond with a strictly formatted JSON object:
{
  "thought_process": "<Detailed step-by-step reasoning explaining What, Where, and How>",
  "explanation": "<Clear summary of proposed changes>",
  "files_to_modify": ["<filepath/1>", "<filepath/2>", ...],
  "changes": [
    {
      "file_path": "<filepath>",
      "action": "modify|create|delete",
      "explanation": "<Why this change is made>",
      "old_content": "<Original code snippet or null>",
      "new_content": "<Updated complete code snippet>",
      "diff": "<Unified diff or null>"
    }
  ]
}
Return ONLY valid JSON.
"""

CRITIC_SYSTEM_PROMPT = """You are a Principal Code Reviewer and Quality Assurance Architect.
Your responsibility is to critically evaluate a proposed code change (CodeProposal) against the original issue and plan.

You must evaluate:
1. Requirement Coverage: Does this CodeProposal satisfy all functional and non-functional requirements from the Plan and original issue?
2. Correctness: Are there logical flaws, syntax errors, or regression risks in the implementation?
3. Repository Compatibility: Does the change respect repository conventions, architecture, imports, and existing interfaces?
4. Test/Execution Evidence: If test/execution results are provided, do failures indicate an implementation problem? Are tests missing?
5. Edge Cases: Are edge cases, boundary conditions, and error handling properly considered?
6. Unnecessary Changes: Are there out-of-scope edits, gratuitous refactorings, or modifications to unrelated files?
7. Maintainability: Is the code clean, readable, well-structured, and consistent with the codebase?

You should NOT blindly accept the CodeProposal. Be rigorous and critical. If there are unresolved bugs, failing tests, missing requirements, or unexplained modifications, set "is_acceptable" to false and lower the score accordingly.

Respond with a strictly formatted JSON object matching the following structure:
{
  "is_acceptable": true|false,
  "score": <float between 0.0 and 1.0>,
  "feedback": "<Detailed evaluation feedback summarizing strengths and weaknesses>",
  "unresolved_issues": ["<Issue 1>", ...],
  "suggestions": ["<Suggestion 1>", ...]
}
Return ONLY valid JSON.
"""


def format_planner_user_prompt(
    issue: Dict[str, Any],
    repo_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Format prompt for Planner Agent."""
    title = issue.get("title", "No title")
    body = issue.get("body") or issue.get("description") or "No description"
    
    prompt = f"### ISSUE DETAILS\nTitle: {title}\nDescription:\n{body}\n\n"
    
    if repo_info:
        prompt += "### REPOSITORY INFORMATION\n"
        if "tree" in repo_info:
            prompt += f"Directory Structure:\n{repo_info['tree']}\n\n"
        if "files" in repo_info:
            prompt += f"Relevant Files:\n{repo_info['files']}\n\n"
        if "context" in repo_info:
            prompt += f"Context:\n{repo_info['context']}\n\n"
            
    prompt += "Produce the structured implementation plan JSON."
    return prompt


def format_coder_user_prompt(
    issue: Dict[str, Any],
    plan: Optional[Dict[str, Any]] = None,
    repo_info: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Format prompt for Coder Agent."""
    title = issue.get("title", "No title")
    body = issue.get("body") or issue.get("description") or "No description"
    
    prompt = f"### ISSUE TO SOLVE\nTitle: {title}\nDescription:\n{body}\n\n"
    
    if plan:
        prompt += f"### IMPLEMENTATION PLAN\nGoal: {plan.get('goal', '')}\n"
        prompt += f"Requirements: {plan.get('requirements', [])}\n"
        prompt += f"Steps:\n" + "\n".join(f"- {s}" for s in plan.get("steps", [])) + "\n"
        prompt += f"Target Files: {plan.get('files_to_investigate', [])}\n"
        prompt += f"Risks: {plan.get('potential_risks', [])}\n\n"
        
    if repo_info:
        prompt += "### REPOSITORY & CODE CONTEXT\n"
        if "code_snippets" in repo_info:
            prompt += f"Code Snippets:\n{repo_info['code_snippets']}\n\n"
        if "files" in repo_info:
            prompt += f"Files Content:\n{repo_info['files']}\n\n"
            
    if history:
        prompt += "### TOOL INTERACTION HISTORY\n"
        for item in history:
            prompt += f"Tool: {item.get('tool')}\nOutput: {item.get('output')}\n"
        prompt += "\n"
        
    prompt += "Produce the structured CodeProposal JSON."
    return prompt


def format_critic_user_prompt(
    issue: Dict[str, Any],
    proposal: Dict[str, Any],
    plan: Optional[Dict[str, Any]] = None,
    repo_info: Optional[Dict[str, Any]] = None,
    test_results: Optional[Union[str, Dict[str, Any]]] = None,
) -> str:
    """Format prompt for Critic Agent."""
    title = issue.get("title", "No title")
    body = issue.get("body") or issue.get("description") or "No description"
    
    prompt = f"### ORIGINAL ISSUE\nTitle: {title}\nDescription:\n{body}\n\n"
    
    if plan:
        prompt += f"### TARGET PLAN\nGoal: {plan.get('goal', '')}\n"
        if plan.get("requirements"):
            prompt += f"Requirements: {plan.get('requirements')}\n"
        if plan.get("steps"):
            prompt += "Steps:\n" + "\n".join(f"- {s}" for s in plan.get("steps", [])) + "\n"
        prompt += "\n"

    if repo_info:
        prompt += "### REPOSITORY CONTEXT\n"
        if "tree" in repo_info:
            prompt += f"Directory Structure:\n{repo_info['tree']}\n\n"
        if "files" in repo_info:
            prompt += f"Relevant Files:\n{repo_info['files']}\n\n"
        if "context" in repo_info:
            prompt += f"Context:\n{repo_info['context']}\n\n"
        
    prompt += f"### PROPOSED CODE CHANGE\n"
    prompt += f"Thought Process: {proposal.get('thought_process', '')}\n"
    prompt += f"Explanation: {proposal.get('explanation', '')}\n"
    prompt += f"Files Modified: {proposal.get('files_to_modify', [])}\n"
    
    changes = proposal.get("changes", [])
    if changes:
        prompt += "Changes Detail:\n"
        for change in changes:
            prompt += f"- File: {change.get('file_path')} ({change.get('action')})\n"
            if change.get("explanation"):
                prompt += f"  Explanation: {change.get('explanation')}\n"
            if change.get("new_content"):
                prompt += f"  New Content:\n```\n{change.get('new_content')}\n```\n"
            elif change.get("diff"):
                prompt += f"  Diff:\n```diff\n{change.get('diff')}\n```\n"

    if test_results:
        prompt += "\n### TEST / EXECUTION RESULTS\n"
        if isinstance(test_results, dict):
            if "status" in test_results:
                prompt += f"Status: {test_results['status']}\n"
            if "output" in test_results:
                prompt += f"Output:\n{test_results['output']}\n"
            if "failures" in test_results:
                prompt += f"Failures:\n{test_results['failures']}\n"
        else:
            prompt += f"{test_results}\n"

    prompt += "\nEvaluate this proposal and output the CriticEvaluation JSON."
    return prompt
