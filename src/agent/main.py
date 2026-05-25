# Loads .env, initializes the agent
# and starts the command loop
import asyncio
import os
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent.agent import create_agent

load_dotenv()

# validate
if not os.getenv("FIVETRAN_APIKEY") or not os.getenv("FIVETRAN_APISECRET"):
    raise ValueError("Missing Fivetran credentials in .env")
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("Missing Google API key in .env")

APP_NAME = "Zero-to-Synced"
USER_ID = "user"  # will be different later dh just for testing
SESSION_ID = "session"


async def main():
    agent, exit_stack = await create_agent()

    session_service = InMemorySessionService()
    await session_service.create_session(
        session_id=SESSION_ID,
        user_id=USER_ID,
        app_name=APP_NAME
    )

    runner = Runner(agent=agent, app_name=APP_NAME,
                    session_service=session_service)

    print("Welcome to Zero-to-Synced! Ask me anything about setting up your data pipeline.")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            await exit_stack.aclose()
            print("Goodbye!")
            break
        if not user_input:
            continue

        message = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=message
        ):
            if event.is_final_response():
                print(f"Agent: {event.response.text}\n")

if __name__ == "__main__":
    asyncio.run(main())
