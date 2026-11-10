
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Guardrails.sql_guard import validate_sql
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from Models.schema import AgentSchema
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END


def curate_ques(state: AgentSchema) -> dict:
    user_question = state.user_question

    llm = pick_llm("low")

    response = llm.invoke(
        f"Curate the following user question into a more structured and clear question: {user_question}"
    ).content

    return {
        "curated_questions": response,
        "messages": [HumanMessage(content=response)]
    }


def prompt_query_context(state: AgentSchema) -> dict:
    curated_question = state.curated_questions

    conn_details = {
        "host": os.environ['host'],
        "port": os.environ['port'],
        "user": os.environ['user'],
        "password": os.environ['password'],
        "dbname": os.environ['database']
    }

    obj = DatabaseUtil(conn_details)
    schema_info = obj.schema_details("public")
    obj.close_connection()

    prompt = f"""
    You are an SQL analyst agent. Convert the user's natural language query into PostgreSQL SQL.
    You are provided with the database schema, table names, columns, data types and sample data.
    Unless the user explicitly asks for a specific number of rows, limit output to 10 rows.
    Generate only executable SQL without explanations.

    User's Original Query: {curated_question}
    Database Schema Details: {schema_info}
    """

    return {"prompt_Query_context": prompt}


def generate_Sql(state: AgentSchema) -> dict:
    llm = pick_llm("high")

    response = llm.invoke(state.prompt_Query_context).content

    response = response.strip()
    response = response.replace("```sql", "").replace("```", "").strip()

    return {"generated_SQL_query": response}


# ---------------------------- SQL SAFETY CHECK ---------------------------- #

def is_safe_sql(state: AgentSchema) -> dict:

    sql_query = state.generated_SQL_query

    # Deterministic SQL validation using SQLGlot
    is_valid, reason = validate_sql(sql_query)

    if not is_valid:
        return {
            "is_safe": "No",
            "comments": reason
        }

    return {
        "is_safe": "Yes",
        "comments": "SQL query passed deterministic validation."
    }


# ---------------------------- CANCEL UNSAFE SQL ---------------------------- #

def canceled_sql(state: AgentSchema) -> dict:

    final_answer = (
        f"The generated SQL query was deemed unsafe to execute. "
        f"Reason: {state.comments}. Therefore, it will not be executed."
    )

    return {
        "final_Answer": final_answer,
        "messages": [AIMessage(content=final_answer)]
    }


# ---------------------------- EXECUTE SQL ---------------------------- #

def execute_sql(state: AgentSchema) -> dict:

    # Final safety check immediately before database execution
    is_valid, reason = validate_sql(state.generated_SQL_query)

    if not is_valid:
        return {
            "sql_query_execution_result": f"Execution blocked: {reason}"
        }

    conn_details = {
        "host": os.environ['host'],
        "port": os.environ['port'],
        "user": os.environ['user'],
        "password": os.environ['password'],
        "dbname": os.environ['database']
    }

    obj = DatabaseUtil(conn_details)

    try:
        result = obj.execute_sql(state.generated_SQL_query)

        return {
            "sql_query_execution_result": result
        }

    except Exception as e:

        return {
            "sql_query_execution_result": f"Error: {str(e)}"
        }

    finally:
        obj.close_connection()


# ---------------------------- FINAL ANSWER ---------------------------- #

def represent_final_answer(state: AgentSchema) -> dict:

    llm_pick = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Provide a concise, clear and user-friendly
    answer based on the SQL execution result. Avoid SQL code and technical details.

    Execution Result: {state.sql_query_execution_result}
    User's Original Question: {state.curated_questions}
    """

    response = llm_pick.invoke(prompt).content

    return {
        "final_Answer": response,
        "messages": [AIMessage(content=response)]
    }


# -------------------------------- Graph Building --------------------------------

sql_agent_graph = StateGraph(AgentSchema)

sql_agent_graph.add_node("curate_ques", curate_ques)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_Sql)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")


def is_safe_sql_edge(state: AgentSchema) -> str:

    return "execute_sql" if state.is_safe == "Yes" else "canceled_sql"


sql_agent_graph.add_conditional_edges(
    "is_safe_sql",
    is_safe_sql_edge,
    {
        "execute_sql": "execute_sql",
        "canceled_sql": "canceled_sql"
    }
)

sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)


sql_analyst = sql_agent_graph.compile()


# -------------------------------- Execution --------------------------------

if __name__ == "__main__":

    print("Generating graph...")

    png_data = sql_analyst.get_graph().draw_mermaid_png()

    with open("sql_agent_graph.png", "wb") as f:
        f.write(png_data)

    print("Graph saved successfully!")

    input_schema = {
        "messages": [],
        "user_question": "Delete all records from the rides table.",
        "curated_questions": "",
        "prompt_Query_context": "",
        "generated_SQL_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_Answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    print("\n========== MESSAGES ==========")

    for message in response['messages']:
        print(message.content)

    print("\n========== GENERATED SQL ==========")
    print(response['generated_SQL_query'])

    print("\n========== SAFETY CHECK ==========")
    print(response['is_safe'], response['comments'])

    print("\n========== EXECUTION RESULT ==========")
    print(response['sql_query_execution_result'])

    print("\n========== FINAL ANSWER ==========")
    print(response['final_Answer'])
