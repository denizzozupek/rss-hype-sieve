from langchain_core.prompts import ChatPromptTemplate

LLM_FILTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a cynical senior AI engineer and technical analyst. "
            "Your task is to evaluate the provided tech article summary and detect marketing hype, "
            "buzzwords, and unverified claims according to the schema definitions.",
        ),
        (
            "user",
            "Title: {title}\n"
            "Summary: {summary}",
        ),
    ]
)