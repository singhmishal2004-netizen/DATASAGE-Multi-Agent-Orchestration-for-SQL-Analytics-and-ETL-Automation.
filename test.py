
from langchain_core.messages import HumanMessage
from Agents.sql_analyst import sql_analyst

question = """
For every vehicle type, rank all vehicles by their number of completed rides. Use DENSE_RANK() partitioned by vehicle type. Return every vehicle whose dense rank is less than or equal to 3. Include all ties. Do not apply a global LIMIT. Do not use RANK() or ROW_NUMBER(). Show vehicle ID, vehicle type, completed ride count, and dense rank. Sort by vehicle type, dense rank, and vehicle ID.
"""

input_schema = {
    "messages": [],
    "user_question": question,
    "curated_questions": "",
    "prompt_Query_context": "",
    "generated_SQL_query": "",
    "is_safe": "No",
    "comments": "",
    "sql_query_execution_result": "",
    "final_Answer": ""
}

result = sql_analyst.invoke(input_schema)

print("\n========== GENERATED SQL ==========\n")
print(result["generated_SQL_query"])

print("\n========== SAFETY CHECK ==========\n")
print(result["is_safe"])
print(result["comments"])

print("\n========== EXECUTION RESULT ==========\n")
print(result["sql_query_execution_result"])

print("\n========== FINAL ANSWER ==========\n")
print(result["final_Answer"])
