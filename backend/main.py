import asyncio
import threading

import asyncpg
import gradio as gr
from dotenv import load_dotenv

from src.db import database_connect

load_dotenv()

from src.agent import Deps, agent
from src.build_rag import build_search_db


class ChatApp:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.deps = Deps(conn=conn)
        self.loop = asyncio.get_event_loop()

    async def close(self):
        await self.conn.close()

    async def chat_response(self, message, history):
        try:
            answer = await agent.run(message, deps=self.deps)
            return answer.output
        except Exception as e:
            return f"Error: {str(e)}"

    def create_interface(self):
        with gr.Blocks(title="AI Assistant Chat") as interface:
            gr.Markdown("# AI Assistant")
            gr.Markdown("Ask me anything about your data!")

            chatbot = gr.Chatbot(
                height=500,
                show_label=False,
                show_copy_button=True
            )

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message here...",
                    show_label=False,
                    scale=4
                )
                submit = gr.Button("Send", variant="primary", scale=1)
                clear = gr.Button("Clear", variant="secondary", scale=1)

            def user_message(user_input, history):
                return "", history + [[user_input, None]]

            def bot_response(history):
                if history and history[-1][1] is None:
                    user_msg = history[-1][0]

                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.chat_response(user_msg, history),
                            self.loop
                        )
                        bot_msg = future.result(timeout=30)
                    except Exception as e:
                        bot_msg = f"Error: {str(e)}"

                    history[-1][1] = bot_msg
                return history

            msg.submit(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_response, chatbot, chatbot
            )
            submit.click(user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
                bot_response, chatbot, chatbot
            )
            clear.click(lambda: None, None, chatbot, queue=False)

        return interface


async def main():
    conn = await database_connect()

    try:
        await build_search_db(conn)

        chat_app = ChatApp(conn)
        interface = chat_app.create_interface()

        def run_gradio():
            interface.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                debug=True
            )

        gradio_thread = threading.Thread(target=run_gradio, daemon=True)
        gradio_thread.start()

        try:
            while gradio_thread.is_alive():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
