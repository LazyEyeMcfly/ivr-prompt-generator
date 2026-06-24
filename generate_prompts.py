from prompt_utils import read_prompts, synthesize_prompt

INPUT_CSV = "prompts.csv"

prompts = read_prompts(INPUT_CSV)
print(f"Found {len(prompts)} prompts to process.\n")

for name, text in prompts:
    print(f"[PROCESS] {name} => \"{text}\"")
    result = synthesize_prompt(text, name)
    print(result)
