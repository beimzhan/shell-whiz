import os

from openai import AsyncOpenAI

from shell_whiz.constants import DELIMITER
from shell_whiz.llm_jsonschemas import (
    dangerous_command_jsonschema,
    edited_shell_command_jsonschema,
    translation_jsonschema,
)

client = AsyncOpenAI()


def get_user_preferences():
    return f"These are my preferences: {DELIMITER}\n{os.environ['SW_PREFERENCES']}\n{DELIMITER}"


async def translate_nl_to_shell_command(prompt):
    response = await client.chat.completions.create(
        model=os.environ["SW_MODEL"],
        temperature=0.25,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{get_user_preferences()}\n\n{prompt}",
            }
        ],
        functions=[
            {
                "name": "perform_task_in_command_line",
                "description": "Perform a task in the command line",
                "parameters": translation_jsonschema,
            }
        ],
        function_call={"name": "perform_task_in_command_line"},
    )
    return response.choices[0].message.function_call.arguments


async def recognize_dangerous_command(shell_command):
    response = await client.chat.completions.create(
        model=os.environ["SW_MODEL"],
        temperature=0,
        max_tokens=96,
        messages=[
            {
                "role": "user",
                "content": f"{get_user_preferences()}\n\nI want to run this command: {DELIMITER}\n{shell_command}\n{DELIMITER}",
            },
        ],
        functions=[
            {
                "name": "recognize_dangerous_command",
                "description": "Recognize a dangerous shell command. This function should be very low sensitive, only mark a command dangerous when it has very serious consequences.",
                "parameters": dangerous_command_jsonschema,
            }
        ],
        function_call={"name": "recognize_dangerous_command"},
    )
    return response.choices[0].message.function_call.arguments


async def get_explanation_of_shell_command_as_stream(
    shell_command, explain_using=None
):
    prompt = f'Split the command into parts and explain it in **list** format. Each line should follow the format "command part" followed by an explanation.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists directory contents.\n  * `-l` displays in long format.\n\nFor `cat file | grep "foo"`, the explanation would be:\n* `cat file` reads the content of `file`.\n* `| grep "foo"` filters lines containing "foo".\n\n* Never explain basic command line concepts like pipes, variables, etc.\n* Keep explanations clear, simple, concise and elegant (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\nIf you can\'t provide an explanation for a specific shell command or it\'s not a shell command, you should reply with an empty JSON object.\n\n{get_user_preferences()}\n\nShell command: {DELIMITER}\n{shell_command}\n{DELIMITER}'

    temperature = 0.1
    max_tokens = 512

    return await client.chat.completions.create(
        model=explain_using or os.environ["SW_EXPLAIN_USING"],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        messages=[{"role": "user", "content": prompt}],
    )


async def get_explanation_of_shell_command_by_chunks(
    shell_command=None, explain_using=None, stream=None
):
    if stream is None:
        stream = await get_explanation_of_shell_command_as_stream(
            shell_command, explain_using=explain_using
        )

    async for chunk in stream:
        yield chunk.choices[0].delta.content


async def edit_shell_command(shell_command, prompt):
    response = await client.chat.completions.create(
        model=os.environ["SW_MODEL"],
        temperature=0.2,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{shell_command}\n\nPrompt: {DELIMITER}\n{prompt}\n{DELIMITER}",
            },
        ],
        functions=[
            {
                "name": "edit_shell_command",
                "description": "Edit a shell command, according to the prompt",
                "parameters": edited_shell_command_jsonschema,
            }
        ],
        function_call={"name": "edit_shell_command"},
    )
    return response.choices[0].message.function_call.arguments
