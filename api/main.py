import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from Models.schema import ChatRequest,ChatResponse
from Agents.data_agent import data_agent

app=FastAPI(title="DataSage API")
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = data_agent.invoke({
            "messages": [HumanMessage(content=request.message)],
            "route_response": ""
        })

        return ChatResponse(
            response=result["messages"][-1].content,
            route_used=result["route_response"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
