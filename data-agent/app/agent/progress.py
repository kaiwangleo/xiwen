def emit_progress(writer, step: str, status: str, *, stack=None, desc: str = "", detail: str = ""):
    """向问数 SSE 推一条 progress 事件，不改图状态。"""
    event = {"type": "progress", "step": step, "status": status}
    if stack:
        event["stack"] = list(stack)
    if desc:
        event["desc"] = desc
    if detail:
        event["detail"] = detail
    writer(event)
