from pathlib import Path

path = Path(__file__).resolve().parent / "src/views/Observability/index.ts"
text = path.read_text(encoding="utf-8")
stack = []
for i, ch in enumerate(text):
    if ch == "{":
        stack.append(i)
    elif ch == "}":
        if stack:
            stack.pop()
        else:
            print("extra closing at", i)
            break
else:
    if stack:
        print("total missing", len(stack))
        for pos in stack[-5:]:
            line = text.count("\n", 0, pos) + 1
            col = pos - text.rfind("\n", 0, pos)
            excerpt = text[pos-30:pos+30].replace("\n", "\\n")
            print(f"missing closing near line {line}, col {col}: {excerpt}")
    else:
        print("all balanced")
