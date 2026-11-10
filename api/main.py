
import os
import sys
import logging

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage

from Models.schema import ChatRequest, ChatResponse
from Agents.data_agent import data_agent
from Guardrails.etl_guard import resolve_data_path


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(title="DataSage API")


# Project root directory
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        logger.info("Received chat request: %s", request.message)

        result = data_agent.invoke({
            "messages": [HumanMessage(content=request.message)],
            "route_response": ""
        })

        logger.info(
            "Request processed successfully. Route: %s",
            result["route_response"]
        )

        return ChatResponse(
            response=result["messages"][-1].content,
            route_used=result["route_response"]
        )

    except Exception as e:
        logger.exception("Error while processing chat request")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/download")
def download_file(
    file_path: str = Query(...)
):
    try:
        # Resolve and validate the requested path
        resolved_path = resolve_data_path(
            PROJECT_ROOT,
            file_path
        )

        # Only allow regular CSV files
        if not resolved_path.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files can be downloaded."
            )

        if not os.path.isfile(resolved_path):
            raise HTTPException(
                status_code=404,
                detail="Requested file does not exist."
            )

        return FileResponse(
            path=resolved_path,
            filename=os.path.basename(resolved_path),
            media_type="text/csv"
        )

    except HTTPException:
        raise

    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Access outside the data directory is not allowed."
        )

    except Exception:
        logger.exception("File download failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to download the requested file."
        )
