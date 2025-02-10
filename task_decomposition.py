"""
Module: task_decomposition.py

This module implements dynamic task decomposition using a chosen framework's capabilities. In a production environment, you might integrate a framework like LangChain, AutoGen, or Semantic Kernel to perform NLP-based task decomposition. Here, we provide a dummy implementation that demonstrates dynamic behavior based on input parameters.
"""

def decompose_task(request: str, level: int = 1, extra_params: dict = None) -> list:
    """
    Decompose a complex task into actionable subtasks dynamically.

    Args:
        request (str): The complex request that needs to be decomposed.
        level (int): Determines the granularity of the decomposition. Higher levels generate more detailed subtasks.
        extra_params (dict, optional): Additional parameters to control the decomposition strategy. For example, 
                                       {'decomposition_strategy': 'simple'} or {'decomposition_strategy': 'keyword'}.

    Returns:
        list: A list of subtasks derived from the request.

    Dynamic Behavior:
        - The function checks for an extra parameter 'decomposition_strategy' which allows switching between different
          decomposition strategies dynamically.
        - The 'level' parameter is used to increase the granularity of the subtasks (e.g., adding nested steps when level > 1).
    """
    if extra_params is None:
        extra_params = {}

    strategy = extra_params.get('decomposition_strategy', 'simple')

    if strategy == 'simple':
        # Basic decomposition: split the request into sentences by period.
        subtasks = [s.strip() for s in request.split('.') if s.strip()]
        # If a higher level is requested, simulate nested subtasks by duplicating steps.
        if level > 1:
            nested_subtasks = []
            for sub in subtasks:
                nested_subtasks.append(f"Step 1: {sub}")
                nested_subtasks.append(f"Step 2: {sub}")
            return nested_subtasks
        return subtasks

    elif strategy == 'keyword':
        # Advanced strategy: look for keywords in the request and generate subtasks based on them.
        keywords = ['plan', 'buy', 'research', 'organize']
        subtasks = []
        lowered_request = request.lower()
        for keyword in keywords:
            if keyword in lowered_request:
                subtasks.append(f"Perform task related to '{keyword}'")
        # If no keywords are found, fallback to the entire request as a single subtask.
        if not subtasks:
            subtasks = [request.strip()]
        return subtasks

    else:
        # Default behavior: return the full request as a single subtask.
        return [request.strip()]


if __name__ == "__main__":
    # Example usage and sample outputs
    sample_request = "Plan a vacation. Buy tickets. Book a hotel."
    print("Simple Strategy, Level 1:", decompose_task(sample_request))
    print("Simple Strategy, Level 2:", decompose_task(sample_request, level=2))
    print("Keyword Strategy:", decompose_task(sample_request, extra_params={'decomposition_strategy': 'keyword'}))
