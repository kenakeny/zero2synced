# define the agent here, han7ot hena the FivetranMCP toolset + define the model
# and get prompt as well
import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from .prompts import SYSTEM_PROMPT

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "devpostagent"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"


async def create_agent():
    mcp_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=[os.path.join(os.path.dirname(__file__),
                               "..", "fivetran-mcp", "server.py")],
            env={
                "FIVETRAN_APIKEY": os.getenv("FIVETRAN_API_KEY"),
                "FIVETRAN_APISECRET": os.getenv("FIVETRAN_API_SECRET"),
                "FIVETRAN_ALLOW_WRITES": "true"
            }
        )
    )

    agent = Agent(
        name="zero_to_synced",
        model="gemini-2.5-flash",
        instruction=SYSTEM_PROMPT,
        tools=[mcp_toolset]
    )

    return agent, mcp_toolset
