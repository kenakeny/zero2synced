# define the agent here, han7ot hena the FivetranMCP toolset + define the model
# and get prompt as well
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from .prompts import SYSTEM_PROMPT
import warnings
warnings.filterwarnings(
    "ignore", message="StdioServerParameters is not recommended")
load_dotenv()  # Load environment variables from .env file


async def create_agent(api_key: str | None = None, api_secret: str | None = None):
    # Per-user keys when provided; fall back to .env (keeps the CLI working).
    api_key = api_key or os.getenv("FIVETRAN_API_KEY")
    api_secret = api_secret or os.getenv("FIVETRAN_API_SECRET")
    mcp_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=[os.path.join(os.path.dirname(__file__),
                               "..", "fivetran-mcp", "server.py")],
            env={
                "FIVETRAN_API_KEY": api_key,
                "FIVETRAN_API_SECRET": api_secret,
                "FIVETRAN_ALLOW_WRITES": "true"
            }
        ), tool_filter=[
            "metadata_connectors", "metadata_connector_config",
            "list_groups", "list_destinations", "destination_details", "create_destination",
            "list_connections", "connection_details", "create_connection", "connect_card",
            "connection_schema_config", "modify_connection_schema_config",
            "run_setup_tests", "sync_connection",
        ]
    )
    agent = Agent(
        name="zero_to_synced",
        model="gemini-2.5-flash",
        instruction=SYSTEM_PROMPT,
        tools=[mcp_toolset]
    )

    return agent, mcp_toolset
