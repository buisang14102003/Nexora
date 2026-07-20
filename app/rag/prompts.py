SYSTEM_PROMPT = """You answer only from the supplied workspace evidence.
If the evidence does not answer the question, say exactly:
I could not find that information in this workspace's documents.
Do not use knowledge outside the evidence. Keep the answer concise and do not invent sources.
"""


def answer_prompt(question: str, evidence: str, route: str) -> str:
    task = "Summarize the supplied evidence." if route == "summary" else "Answer the question."
    return f"{SYSTEM_PROMPT}\n\nTask: {task}\nQuestion: {question}\n\nEvidence:\n{evidence}"
