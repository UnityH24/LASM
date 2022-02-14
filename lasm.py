#!/usr/bin/python3

import sys
import os
from tables import *

def fatal(progname, msg):
    print("\033[0;31m%s: fatal:\033[0m %s" % (progname, msg))
    exit(1)

def parse_args(progname, args):
    infile = outfile = None
    autorun = False
    while args:
        opt = args.pop()
        if opt == "-o":
            if args:
                if outfile is not None:
                    fatal(progname, "You can only specify one outfile")
                outfile = args.pop()
            else:
                fatal(progname, "Expected outfile after -o but got nothing")
        elif opt == "-r":
            if autorun:
                print(f"{progname}: Warning: option -r is repeated")
            autorun = True
            
        else:
            if infile is None:
                infile = opt
            else:
                fatal(progname, "We only support compilation of single files for now")
    
    if outfile is None:
        outfile = "a.out"
    if infile is None:
        fatal(progname, "You have to specify an input file")
    
    return infile, outfile, autorun

def int_bytes_little_endian(n, size):
    bs = []
    for i in range(size):
        curr = n & 255 # get the least significant byte
        n >>= 8 # right shift by one byte to get next byte
        bs.append(curr)
    return bs

def find_col(line, col, predicate):
    while col < len(line):
        c = line[col]
        if predicate(c):
            return col
        col += 1
    return len(line) # there is no next token so return the length to stop the lex_line function

def lex_line(line):
    col = find_col(line, 0, lambda x: not x.isspace())
    while col < len(line):
        word_end = find_col(line, col, lambda x: x.isspace())
        word = line[col:word_end]
        yield col, get_token(word)
        col = word_end + 1 # if you remove the +1 then it will go to an infinite loop at end of line

def lex_file(progname, path):
    if not os.path.exists(path):
        fatal(progname, f"File {path} doesn't exist")
    
    with open(path, "r") as f:
        return [{"loc": (path, row + 1, col + 1), **token}
                for (row, line) in enumerate(f.readlines())
                for (col, token) in lex_line(line)] # wow such cool list comprehension and stuff

def get_token(word):
    if word.startswith("#"): # it is a number
        num = word[1:]
        if num.startswith('0x'): # it is hexadecimal number
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
            reg = (None, None) # see the return statement below
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

def check_operands(instruction, *ops):
    if instruction == OP_MOV:
        dest, src = ops
        return (dest["type"], src["type"]) in [(TOKEN_REG, TOKEN_IMM), (TOKEN_REG, TOKEN_REG)]
    elif instruction == OP_INT:
        nr ,= ops
        return dest["type"] == TOKEN_IMM
    elif instruction == OP_ADD:
        dest, src = ops
        return (dest["type"], src["type"]) in [(TOKEN_REG, TOKEN_IMM), (TOKEN_REG, TOKEN_REG)]

def compile_program(progname, program, outfile, infile, autorun):
    ip = 0
    size = 0
    labels = set()
    output = bytearray()

    # Writing the elf header
    output += bytearray(b'\x7fELF') # magic num
    output.append(0x01) # 32-bit
    output.append(0x01) # little-endian
    output.append(0x01) # version must be 1
    output.append(0x00) # system V ABI will work
    output.append(0x00) # ABI version 0 will work
    output += bytearray(b'\x00' * 7) # padding
    output += bytearray(b'\x02\x00') # executable file
    output += bytearray(b'\x03\x00') # x86
    output += bytearray(b'\x01\x00\x00\x00') # must be 1
    output += bytearray(b'\x54\x80\x04\x08') # _start
    output += bytearray(b'\x34\x00\x00\x00') # program header table
    output += bytearray(b'\x00\x00\x00\x00') # section header table (unused for us)
    output += bytearray(b'\x00\x00\x00\x00') # the flags are unused for x86
    output += bytearray(b'\x34\x00') # elf header size
    output += bytearray(b'\x20\x00') # program header entry size
    output += bytearray(b'\x01\x00') # number of program header entries
    output += bytearray(b'\x28\x00') # section header entry size
    output += bytearray(b'\x00\x00') # num of section header entries
    output += bytearray(b'\x00\x00') # section header string index (idk)
    # Writing the program header table
    output += bytearray(b'\x01\x00\x00\x00') # this is going to be a loadable segment
    output += bytearray(b'\x54\x00\x00\x00') # offset in the file
    output += bytearray(b'\x54\x80\x04\x08') # virtual address in memory
    output += bytearray(b'\x00\x00\x00\x00') # physical address (unused for x86)
    output += bytearray(b'\x00\x00\x00\x00') # file size (we'll set this later)
    output += bytearray(b'\x00\x00\x00\x00') # memory size (we'll set this later)
    output += bytearray(b'\x07\x00\x00\x00') # readable, writable and executable (pretty unsafe but we don't have .data yet)
    output += bytearray(b'\x00\x10\x00\x00') # alignment (0x1000 big endian)

    # Compiling the program
    while ip < len(program):
        token = program[ip]

        if token["type"] == TOKEN_OP:
            if token["val"] == OP_MOV:
                dest, src = program[ip+1:ip+3] # look at it for a second
                ip += 2
                if (dest["type"], src["type"]) not in [(TOKEN_REG, TOKEN_IMM)]: # TODO: make function to check for invalid opcode and operand combinations
                    print("%s:%d:%d invalid combination of opcode and operands" % token["loc"])
                    exit(1)
                if dest["type"] == TOKEN_REG:
                    if src["type"] == TOKEN_IMM:
                        opcode = bytearray([mov_r_imm[dest["width"]] + dest["val"]] + int_bytes_little_endian(src["val"], 4))  
                        output += opcode

            elif token["val"] == OP_ADD:
                dest, src = program[ip+1:ip+3]
                ip += 2
            elif token["val"] == OP_INT:
                nr = program[ip+1]
                ip += 1
                if nr["type"] == TOKEN_IMM:
                    opcode = bytearray([0xcd, nr["val"] & 255])
                    output += opcode
                else:
                    print("%s:%d:%d invalid combination of opcode and operands" % nr["loc"])
            else:
                assert False, "unreachable"
            ip += 1

        elif token["type"] == TOKEN_IMM:
            output.append(token["val"] & 255)
            ip += 1

        elif token["type"] == TOKEN_REG:
            print("%s:%d:%d dangeling register found in file" % token["loc"])
            exit(1)

        else:
            assert False, "unreachable"

    size = len(output) - 0x54
    output[0x44:0x48] = bytearray(int_bytes_little_endian(size, 4)) # setting p_filesz
    output[0x48:0x4c] = bytearray(int_bytes_little_endian(size, 4)) # setting p_memsz

    with open(outfile, "wb") as out:
        out.write(output)	

    os.system(f"chmod +x {outfile}")
    if autorun:
        os.system(f"./{outfile}")
    
def main():
    ra = list(reversed(sys.argv))
    progname = ra.pop()
    infile, outfile, autorun = parse_args(progname, ra)
    
    program = lex_file(progname, infile)
    compile_program(progname, program, outfile, infile, autorun)

    print("compilation successful")

if __name__ == "__main__":
    main()
