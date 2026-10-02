def route_after_conflict(state):
    """Return the next LangGraph node after meta review."""
    if state.get('human_review_required') and not state.get('human_feedback_applied'):
        return 'human_review'
    conflicts = state.get('conflicts', [])
    for c in conflicts:
        if c.get('requires_re_review') and state.get('reflection_loops', 0) < 2:
            return f"re_review_{c.get('target_agent', 'novelty')}"
    return 'finalize'
