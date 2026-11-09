
import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)

from utils.llm_pick import pick_llm
from Models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from Agents.etl_analyst import etl_analyst
from Agents.sql_analyst import sql_analyst


llm = pick_llm("high")
llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #


def router_node(state: DataAgentSchema):
    message = state.messages[-1].content
    route_response = llm_router.invoke(message).answer
    return {"route_response": route_response}


def etl_node(state: DataAgentSchema):
    message = state.messages[-1].content
    response = etl_analyst.invoke({"messages": [HumanMessage(content=message)]})
    final_answer = AIMessage(content=response["messages"][-1].content)
    return {"messages": [final_answer]}


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

    final_answer = AIMessage(content=response["final_Answer"])

    return {"messages": [final_answer]}


# ---------------------------- GRAPH NODES ---------------------------- #


data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")


def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node"
    }
)

data_agent_graph.add_edge("sql_node", END)
data_agent_graph.add_edge("etl_node", END)

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
