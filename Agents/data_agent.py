
import os
import sys
import re

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)

from utils.llm_pick import pick_llm
from Models.schema import DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from Agents.etl_analyst import etl_analyst
from Agents.sql_analyst import sql_analyst


# Use plain-text output instead of structured tool calling
llm = pick_llm("high")
llm_router = llm


# ---------------------------- GREETING DETECTION ---------------------------- #

GREETINGS = {
    "hi",
    "hii",
    "hello",
    "hey",
    "hiii",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you"
}


def is_greeting(message: str) -> bool:
    return message.strip().lower().rstrip("!.?,") in GREETINGS


# ---------------------------- SQL DETECTION ---------------------------- #

SQL_PATTERN = re.compile(
    r"""
    ^\s*
    (?:```(?:sql)?\s*)?
    (?:
        SELECT |
        WITH |
        INSERT |
        UPDATE |
        DELETE |
        DROP |
        ALTER |
        CREATE |
        TRUNCATE |
        GRANT |
        REVOKE |
        MERGE |
        EXPLAIN |
        SHOW |
        DESCRIBE
    )\b
    """,
    re.IGNORECASE | re.VERBOSE
)


def is_raw_sql(message: str) -> bool:
    return bool(SQL_PATTERN.match(message.strip()))


# ---------------------------- DATA AGENT GRAPH ---------------------------- #

def router_node(state: DataAgentSchema):

    message = state.messages[-1].content.strip()

    if not message:
        raise ValueError("User message cannot be empty.")

    # 1. Handle greetings directly
    if is_greeting(message):
        return {"route_response": "greeting"}

    # 2. Detect raw SQL directly
    # Destructive SQL is routed to SQL Analyst,
    # where the SQL guardrail will reject unsafe queries.
    if is_raw_sql(message):
        return {"route_response": "sql"}

    # 3. Route natural-language requests using plain-text output
    try:

        routing_prompt = [
            SystemMessage(
                content="""
                You are the strict routing controller for DataSage.

                You must classify every user request into exactly one route.

                Available routes:

                1. sql:
                   - Database queries
                   - SQL analytics
                   - Counting, filtering, grouping, joining records
                   - Questions about database tables and records
                   - Requests to inspect database information
                   - Requests involving SQL operations

                2. etl:
                   - Extracting data from URLs or APIs
                   - Loading files
                   - Reading CSV, JSON, or Parquet files
                   - Data cleaning and transformation
                   - Removing duplicates
                   - Handling missing values
                   - Renaming, selecting, or sorting columns
                   - Saving transformed datasets

                Strict rules:
                - Return only one route: sql or etl.
                - Never return explanations or additional text.
                - Do not execute or explain the user's request.
                - If the request concerns database records, choose sql.
                - If the request concerns file extraction or transformation,
                  choose etl.
                """
            ),
            HumanMessage(content=message)
        ]

        # Get normal text response instead of a structured tool call
        route_response = llm_router.invoke(routing_prompt).content

        if not isinstance(route_response, str):
            raise ValueError("Router returned a non-string response.")

        route_response = route_response.strip().lower().rstrip(" .,!")

        if route_response not in {"sql", "etl"}:
            raise ValueError(
                f"Invalid route returned by LLM: {route_response}"
            )

        return {"route_response": route_response}

    except Exception as e:
        raise RuntimeError(
            f"DataSage routing failed. Request was not forwarded. Reason: {str(e)}"
        ) from e


# ---------------------------- GREETING NODE ---------------------------- #

def greeting_node(state: DataAgentSchema):

    message = state.messages[-1].content.strip().lower()

    if message.rstrip("!.?,") in {"thanks", "thank you"}:
        response = (
            "You're welcome! How can I help you with your data today?"
        )
    else:
        response = (
            "Hello! Welcome to DataSage. "
            "I can help you with SQL analytics and ETL operations. "
            "What would you like to do?"
        )

    return {
        "messages": [AIMessage(content=response)]
    }


# ---------------------------- ETL NODE ---------------------------- #

def etl_node(state: DataAgentSchema):

    message = state.messages[-1].content

    response = etl_analyst.invoke({
        "messages": [HumanMessage(content=message)]
    })

    final_answer = AIMessage(
        content=response["messages"][-1].content
    )

    return {"messages": [final_answer]}


# ---------------------------- SQL NODE ---------------------------- #

def sql_node(state: DataAgentSchema):

    message = state.messages[-1].content

    input_schema = {
        "messages": [],
        "user_question": message,
        "curated_questions": "",
        "prompt_Query_context": "",
        "generated_SQL_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_Answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    final_answer = AIMessage(
        content=response["final_Answer"]
    )

    return {"messages": [final_answer]}


# ---------------------------- GRAPH NODES ---------------------------- #

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("greeting_node", greeting_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")


# ---------------------------- CONDITIONAL ROUTING ---------------------------- #

def route_edge(state: DataAgentSchema) -> str:

    if state.route_response == "sql":
        return "sql_node"

    elif state.route_response == "etl":
        return "etl_node"

    elif state.route_response == "greeting":
        return "greeting_node"

    else:
        raise ValueError(
            f"Invalid route response: {state.route_response}"
        )


data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node",
        "greeting_node": "greeting_node"
    }
)

data_agent_graph.add_edge("sql_node", END)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("greeting_node", END)


data_agent = data_agent_graph.compile()


# ---------------------------- GRAPH VISUALIZATION ---------------------------- #

if __name__ == "__main__":

    from IPython.display import Image

    png_data = data_agent.get_graph().draw_mermaid_png()

    with open("data_agent_graph.png", "wb") as f:
        f.write(png_data)

    response = data_agent.invoke({
        "messages": [
            HumanMessage(
                content="How many rides are there in our database?"
            )
        ],
        "route_response": ""
    })

    print("\n========== DATA AGENT RESPONSE ==========\n")

    for message in response["messages"]:
        print(message.content)
