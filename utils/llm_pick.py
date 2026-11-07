
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def pick_llm(level: str):
    """
    Picks the appropriate LLM based on question complexity.

    Args:
        level (str): "low", "medium", or "high"

    Returns:
        LLM instance based on the selected level.
    """

    level = level.lower()

    if level == "low":
        llm = ChatGroq(
            model=os.getenv("GROQ_MODEL"),
            temperature=0,
            reasoning_effort="low"
        )

    elif level == "medium":
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL"),
            temperature=0
        )

    elif level == "high":
        llm = ChatGroq(
            model=os.getenv("GROQ_MODEL"),
            temperature=0,
            reasoning_effort="high"
        )

    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm


if __name__ == "__main__":

    llm_obj = pick_llm("low")

    response = llm_obj.invoke(
        "What is the capital of France?"
    )

    print(response.content)
