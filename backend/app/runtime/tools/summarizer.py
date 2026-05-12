from langchain_core.tools import tool

from app.runtime.tools.registry import register_tool


@tool
def summarizer(text: str) -> str:
    """Summarize the given text into a concise paragraph. Useful for condensing research results."""
    from langchain_openai import ChatOpenAI
    from app.config import settings

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, max_tokens=512)
    response = llm.invoke(
        f"Summarize the following text in one concise paragraph:\n\n{text[:8000]}"
    )
    return response.content


register_tool("summarizer", summarizer)
