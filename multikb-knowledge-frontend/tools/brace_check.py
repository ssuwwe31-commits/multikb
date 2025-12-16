from pathlib import Path

text_path = Path(__file__).resolve().parents[1] / "src/views/Observability/index.ts"
text = text_path.read_text(encoding="utf-8")

stack = []
in_string = None
escape = False

for i, ch in enumerate(text):
    if in_string:
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == in_string:
            in_string = None
        continue
    else:
        if ch in ("'", '"', "`"):
            in_string = ch
            continue

    if ch == "{":
        stack.append(i)
    elif ch == "}":
        if stack:
            stack.pop()
        else:
            print("extra closing brace at index", i)
            break
else:
    if not stack:
        print("all braces matched")
    else:
        print("unmatched count", len(stack))
        for pos in stack[-5:]:
            line = text.count("\n", 0, pos) + 1
            col = pos - text.rfind("\n", 0, pos)
            snippet = text[pos-20:pos+20].replace("\n", "\\n")
            print("unmatched near line", line, "col", col, "context:", snippet)
