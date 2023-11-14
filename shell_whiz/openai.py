import json
import os

import jsonschema
from jsonschema import validate
from openai import AsyncOpenAI

from shell_whiz.constants import DELIMITER
from shell_whiz.exceptions import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)
from shell_whiz.jsonschemas import (
    dangerous_command_jsonschema,
    edited_shell_command_jsonschema,
    translation_jsonschema,
)

client = AsyncOpenAI()


def get_my_preferences():
    return f"These are my preferences: {DELIMITER}\n{os.environ['SW_PREFERENCES']}\n{DELIMITER}"


async def translate_nl_to_shell_command_openai(prompt):
    response = await client.chat.completions.create(
        model=os.environ["SW_MODEL"],
        temperature=0.25,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{get_my_preferences()}\n\n{prompt}",
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


async def translate_nl_to_shell_command(prompt):
    translation = await translate_nl_to_shell_command_openai(prompt)

    try:
        translation_json = json.loads(translation)
    except json.JSONDecodeError:
        raise TranslationError("Could not extract JSON.")

    try:
        validate(instance=translation_json, schema=translation_jsonschema)
    except jsonschema.ValidationError:
        raise TranslationError("Generated JSON is not valid.")

    shell_command = translation_json["shell_command"].strip()

    if shell_command == "":
        raise TranslationError("Extracted shell command is empty.")

    return shell_command


async def recognize_dangerous_command_openai(shell_command):
    response = await client.chat.completions.create(
        model=os.environ["SW_MODEL"],
        temperature=0,
        max_tokens=96,
        messages=[
            {
                "role": "user",
                "content": f"{get_my_preferences()}\n\nI want to run this command: {DELIMITER}\n{shell_command}\n{DELIMITER}",
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


async def recognize_dangerous_command(shell_command):
    dangerous_command = await recognize_dangerous_command_openai(shell_command)

    try:
        dangerous_command_json = json.loads(dangerous_command)
    except json.JSONDecodeError:
        raise WarningError("Could not extract JSON.")

    try:
        validate(
            instance=dangerous_command_json,
            schema=dangerous_command_jsonschema,
        )
    except jsonschema.ValidationError:
        raise WarningError("Generated JSON is not valid.")

    is_dangerous = dangerous_command_json["dangerous_to_run"]
    dangerous_consequences = dangerous_command_json.get(
        "dangerous_consequences", ""
    ).strip()

    if not is_dangerous:
        return False, ""

    if dangerous_consequences == "":
        raise WarningError("Extracted dangerous consequences are empty.")
    elif "\n" in dangerous_consequences:
        raise WarningError("Extracted dangerous consequences contain newlines.")

    return True, dangerous_consequences


async def get_explanation_of_shell_command_openai(
    shell_command, explain_using=None
):
    prompt = f'Split the command into parts and explain it in **list** format. Each line should follow the format "command part" followed by an explanation.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists directory contents.\n  * `-l` displays in long format.\n\nFor `cat file | grep "foo"`, the explanation would be:\n* `cat file` reads the content of `file`.\n* `| grep "foo"` filters lines containing "foo".\n\n* Never explain basic command line concepts like pipes, variables, etc.\n* Keep explanations clear, simple, concise and elegant (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\nIf you can\'t provide an explanation for a specific shell command or it\'s not a shell command, you should reply with an empty JSON object.\n\n{get_my_preferences()}\n\nShell command: {DELIMITER}\n{shell_command}\n{DELIMITER}'

    temperature = 0.1
    max_tokens = 512

    return await client.chat.completions.create(
        model=os.environ["SW_EXPLAIN_USING"]
        if explain_using is None
        else explain_using,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        messages=[{"role": "user", "content": prompt}],
    )


async def get_explanation_of_shell_command(
    explain_using=None, shell_command=None, stream=None
):
    if stream is None:
        response = await get_explanation_of_shell_command_openai(
            shell_command, explain_using=explain_using
        )
    else:
        response = stream

    is_first_chunk = True
    skip_initial_spaces = True
    async for chunk in response:
        chunk_message = chunk.choices[0].delta.content
        if chunk_message is None:
            break

        if skip_initial_spaces:
            chunk_message = chunk_message.lstrip()
            if chunk_message:
                skip_initial_spaces = False
            else:
                continue

        if is_first_chunk:
            if not chunk_message.startswith("*"):
                raise ExplanationError("Explanation is not valid.")
            is_first_chunk = False

        yield chunk_message


async def edit_shell_command_openai(shell_command, prompt):
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


async def edit_shell_command(shell_command, prompt):
    edited_shell_command = await edit_shell_command_openai(
        shell_command, prompt
    )

    try:
        edited_shell_command_json = json.loads(edited_shell_command)
    except json.JSONDecodeError:
        raise EditingError("Could not extract JSON.")

    try:
        validate(
            instance=edited_shell_command_json,
            schema=edited_shell_command_jsonschema,
        )
    except jsonschema.ValidationError:
        raise EditingError("Generated JSON is not valid.")

    edited_shell_command = edited_shell_command_json[
        "edited_shell_command"
    ].strip()
    if edited_shell_command == "":
        raise EditingError("Edited shell command is empty.")

    return edited_shell_command
