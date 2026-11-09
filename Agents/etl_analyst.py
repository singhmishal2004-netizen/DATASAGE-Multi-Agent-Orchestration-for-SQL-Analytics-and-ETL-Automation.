
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from Models.schema import ETLAgentSchema

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage
)
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool


# ------------------------------------ AGENT TOOLS ------------------------------------ #


@tool
def extract_load_tool(url: str, output_folder: str, format: str) -> str:
    """
    Extract data from an API endpoint and save it in the requested format.

    Args:
        url: API endpoint.
        output_folder: Folder where extracted data will be saved.
        format: Output format (csv, json, parquet).
    """
    etl_tools = ETLTools()
    return etl_tools.extract_load(url, output_folder, format)


@tool
def transform_load_tool(
    input_file_path: str,
    output_folder: str,
    output_format: str,
    user_question: str
) -> str:
    """
    Transform data using Pandas according to the user's requirement
    and save the transformed data.

    Args:
        input_file_path: Input file path.
        output_folder: Destination folder.
        output_format: Output format (csv, json, parquet).
        user_question: Required transformation.
    """

    etl_tools = ETLTools()

    top_3_rows = etl_tools.transform_load_context(input_file_path)

    # High reasoning model for Pandas code generation
    llm = pick_llm("high")

    prompt = f"""
You are a Python Data Analyst who uses Pandas.

Generate ONLY executable Python Pandas code.

Requirements:
1. Read the input file using Pandas.
2. Perform the transformation requested by the user.
3. Save the transformed dataframe inside the given output folder.
4. Save the result in the requested output format.
5. Create the output folder if it does not exist.
6. Do not include explanations or markdown.

Input file: {input_file_path}
Output folder: {output_folder}
Output format: {output_format}

User's requirement:
{user_question}

Data context:
{top_3_rows}
"""

    response = llm.invoke(prompt).content

    # Clean generated code
    pandas_code = response.strip()

    if pandas_code.startswith("```"):
        pandas_code = pandas_code.split("\n", 1)[-1]
        pandas_code = pandas_code.rsplit("```", 1)[0].strip()

    if pandas_code.startswith("python"):
        pandas_code = pandas_code[len("python"):].strip()

    # Execute generated Pandas code
    results = etl_tools.execute_code(pandas_code)

    return f"""
Transformation completed.

Output folder: {output_folder}
Output format: {output_format}

Pandas Code Executed:
{pandas_code}

Execution Result:
{results}
"""


# ------------------------------------ TOOLKIT ------------------------------------ #


tools = [extract_load_tool, transform_load_tool]

# Low reasoning model for deciding which tool to call
llm = pick_llm("low")
llm_bind = llm.bind_tools(tools)


# ------------------------------------ AGENT GRAPH ------------------------------------ #


def llm_node(state: ETLAgentSchema):

    prompt = SystemMessage(content="""
You are a Python Data Analyst with access to two ETL tools:

1. extract_load_tool:
   Extracts data from an API and saves it in the requested format.

2. transform_load_tool:
   Reads an existing file, transforms its data using Pandas,
   and saves the transformed data.

Understand the user's request and call the appropriate tool.

If the user requests extraction, use extract_load_tool.
If the user requests transformation, use transform_load_tool.

If the required information is missing, ask the user for it.

After successful tool execution, provide a clear final answer.
Do not claim an operation was successful unless the tool confirms it.
""")

    messages = [prompt] + state.messages

    response = llm_bind.invoke(messages)

    # Return only the newly generated message.
    return {"messages": [response]}


def tool_node(state: ETLAgentSchema):
    """
    Execute the tools selected by the LLM.
    """

    tools_results = []

    tools_by_name = {tool.name: tool for tool in tools}

    tool_calls = state.messages[-1].tool_calls

    for tool_call in tool_calls:

        selected_tool = tools_by_name[tool_call["name"]]

        try:
            observation = selected_tool.invoke(tool_call["args"])
        except Exception as e:
            observation = f"Tool execution failed: {str(e)}"

        tools_results.append(
            ToolMessage(
                content=str(observation),
                tool_call_id=tool_call["id"]
            )
        )

    # Return only new tool messages.
    return {"messages": tools_results}


# ------------------------------------ GRAPH ------------------------------------ #


etl_analyst_graph = StateGraph(ETLAgentSchema)

etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

etl_analyst_graph.add_edge(START, "llm_node")


def is_tool_call(state: ETLAgentSchema):

    tool_calls = state.messages[-1].tool_calls

    if tool_calls:
        return "tool_node"

    return "end"


etl_analyst_graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    }
)

etl_analyst_graph.add_edge("tool_node", "llm_node")

etl_analyst = etl_analyst_graph.compile()


# ------------------------------------ TESTING ------------------------------------ #


if __name__ == "__main__":

    # Optional: Save graph visualization
    png_data = etl_analyst.get_graph().draw_mermaid_png()

    with open("etl_analyst_graph.png", "wb") as f:
        f.write(png_data)

    response = etl_analyst.invoke({
        "messages": [
            HumanMessage(
                content="""
                Extract data from the API endpoint
                https://pokeapi.co/api/v2/pokemon
                and save it inside the data/extract folder
                in CSV format.
                """
            )
        ]
    })

    print("\n========== ETL AGENT RESPONSE ==========\n")

    for message in response["messages"]:
        print(message.content)
