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


LLM_REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior technical editor and AI analyst. "
            "Your task is to synthesize the provided list of evaluated technical articles into a concise, high-signal Markdown briefing for software engineers.\n\n"
            "Formatting Guidelines:\n"
            "- Start directly with the first article without any introductory greetings, meta-commentary, or pleasantries.\n"
            "- Structure each item using this exact format:\n"
            "  ### [Title](URL)\n"
            "  - **Key Takeaway:** One sharp, technical sentence highlighting the core insight or architectural advancement.\n"
            "  - **Summary:** 2-3 concise sentences detailing the implementation, benchmark, or engineering substance.\n"
            "- Keep the tone objective, technical, and free of marketing fluff.",
        ),
        (
            "user",
            "Articles to synthesize:\n\n{articles_text}",
        ),
    ]
)