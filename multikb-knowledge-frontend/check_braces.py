import pathlib
text=pathlib.Path('src/views/Observability/index.ts').read_text(encoding='utf-8')
stack=[]
pairs={'{':'}','(' :')','[':']'}
quotes=('"',"'",'')
n=len(text)
i=0
while i<n:
    ch=text[i]
    if ch=='\\':
        i+=2
        continue
    if ch in quotes:
        quote=ch
        i+=1
        while i<n:
            c=text[i]
            if c=='\\':
                i+=2
                continue
            if c==quote:
                break
            i+=1
        i+=1
        continue
    if ch=='/' and i+1<n:
        if text[i+1]=='/':
            i+=2
            while i<n and text[i]!='\n':
                i+=1
            continue
        if text[i+1]=='*':
            i+=2
            while i+1<n and not(text[i]=='*' and text[i+1]=='/'):
                i+=1
            i+=2
            continue
    if ch in pairs:
        stack.append((ch,i))
    elif ch in pairs.values():
        if not stack:
            print('extra close',ch,'at',i)
            break
        open_ch,idx=stack.pop()
        if pairs[open_ch]!=ch:
            print('mismatch',open_ch,idx,'->',ch,i)
            break
    i+=1
else:
    print('stack size',len(stack))
    if stack:
        print('unclosed tail',stack[-5:])
