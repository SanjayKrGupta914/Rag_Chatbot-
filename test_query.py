import asyncio
from main import ask_with_chat_history, AskRequest

async def main():
    req = AskRequest(
        pdf_text="This is a test document. It contains the secret code: 12345.",
        question="What is the secret code?",
        chat_history=[],
        model="gemini-2.0-flash"
    )
    res = await ask_with_chat_history(req)
    print(res)

asyncio.run(main())
