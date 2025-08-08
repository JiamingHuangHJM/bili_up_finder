from pathlib import Path

prompts_path = Path("src/bili_up_finder/search_helper/system_prompt/latest")


def get_system_prompts(func_name) -> str:
    with open("prompt.txt", "r", encoding="utf-8") as f:
        instructions = f.read(prompts_path / f"{func_name}.txt")

    return instructions
