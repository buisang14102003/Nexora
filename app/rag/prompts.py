SYSTEM_PROMPT = """You answer only from the supplied workspace evidence.
If the evidence does not answer the question, say exactly:
I could not find that information in this workspace's documents.
Do not use knowledge outside the evidence. Keep the answer concise and do not invent sources.
After the answer, emit exactly one citation tag in this format:
<CITATIONS>["chunk UUID used by the answer"]</CITATIONS>
Only include chunk IDs that directly support the answer. If the evidence is insufficient, use an empty list.
"""


def answer_prompt(question: str, evidence: str, route: str) -> str:
    task = "Summarize the supplied evidence." if route == "summary" else "Answer the question."
    return f"{SYSTEM_PROMPT}\n\nTask: {task}\nQuestion: {question}\n\nEvidence:\n{evidence}"
