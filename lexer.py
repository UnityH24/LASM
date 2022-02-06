from tables import *
import os

def find_col(line, col, predicate):
    while col < len(line):
        c = line[col]
        if predicate(c):
            return col
        col += 1
    return len(line)

def lex_line(line):
    col = find_col(line, 0, lambda x: not x.isspace())
    while col < len(line):
        word_end = find_col(line, col, lambda x: x.isspace())
        word = line[col:word_end]
        yield col, get_token(word)
        col = word_end + 1

def lex_file(progname, path):
    if not os.path.exists(path):
        fatal(progname, f"File {path} doesn't exist")
    
    with open(path, "r") as f:
        return [{"loc": (path, row + 1, col + 1), **token}
                for (row, line) in enumerate(f.readlines())
                for (col, token) in lex_line(line)]

def get_token(word):
    if word.startswith("#"): # it is a number
        num = word[1:]
        if num.startswith('0x'):	
            base = 16
            num = num[2:]
        else:
            base = 10
        try:
            return {
                "type": TOKEN_IMM,
                "val": int(num, base),
                "text": word
            }
        except ValueError:
            print(f"Invalid immediate {word}")
            exit(1)

    elif word.startswith("%"): # it is a register
        reg = regs.get(word[1:].lower())
        if reg is None:
            reg = (None, None)
        return {
            "type": TOKEN_REG,
            "val": reg[0],
            "width": reg[1],
            "text": word
        }
    else:
        return {
            "type": TOKEN_OP,
            "val": OP_TABLE.get(word),
            "text": word
        }

print(lex_file("lexer.py", "test.asm"))
