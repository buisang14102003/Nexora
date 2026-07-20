"""Temporary Chainlit entry point; Task 8 supplies the chat workflow."""

import chainlit as cl


@cl.on_chat_start
async def start() -> None:
    await cl.Message(content="Chat UI placeholder; Task 8 will add the RAG workflow.").send()
