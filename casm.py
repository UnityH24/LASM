#!/usr/bin/python3

import sys
import os


auto_acc = 0
def auto(reset=False):
	global auto_acc
	if reset:
		auto_acc = 0
	else:
		auto_acc += 1
	return auto_acc

EAX = auto(True)
ECX = auto()
EDX = auto()
EBX = auto()
ESP = auto()
EBP = auto()
ESI = auto()
EDI = auto()
AX  = auto(True)
CX  = auto()
DX  = auto()
BX  = auto()
SP  = auto()
BP  = auto()
SI  = auto()
DI  = auto()
AL  = auto(True)
CL  = auto()
DL  = auto()
BL  = auto()
AH  = auto()
CH  = auto()
DH  = auto()
BH  = auto()	

TOKEN_OP = auto(True)
TOKEN_REG = auto()
TOKEN_IMM = auto()

OP_MOV = auto(True)
OP_INT = auto()
OP_ADD = auto()

regs = {
	"eax": (EAX, 4),
	"ecx": (ECX, 4),
	"edx": (EDX, 4),
	"ebx": (EBX, 4),
	"esp": (ESP, 4),
	"ebp": (EBP, 4),
	"esi": (ESI, 4),
	"edi": (EDI, 4),
	"ax":  (AX, 2),
	"cx":  (CX, 2),
	"dx":  (DX, 2),
	"bx":  (BX, 2),
	"sp":  (SP, 2),
	"bp":  (BP, 2),
	"si":  (SI, 2),
	"di":  (DI, 2),
	"al":  (AL, 1),
	"cl":  (CL, 1),
	"dl":  (DL, 1),
	"bl":  (BL, 1),
	"ah":  (AH, 1),
	"ch":  (CH, 1),
	"dh":  (DH, 1),
	"bh":  (BH, 1) 
}

OP_TABLE = {
	"mov": OP_MOV,
	"int": OP_INT,
	"add": OP_ADD
}

MOV_R_IMM = {
	2: 0xb8,
	4: 0xb8
}
ADD_R_IMM = {
	2: 0x81,
	4: 0x81
}

def fatal(progname, msg):
	print("\033[0;31m%s: error:\033[0m %s" % (progname, msg))
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
				print("Warning: option -r is repeated")
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

def lex_line(line):
	col = find_col(line, 0, lambda x: not x.isspace())
	while col is not None and col < len(line):
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

def get_opc(instruction, *args):
	if instruction == OP_MOV:
		dest, src = args
		if dest["type"] == TOKEN_REG:
			if src["type"] == TOKEN_IMM:
				instr = MOV_R_IMM[dest["width"]]
				opcode = bytearray([instr + dest["val"]] + int_bytes_little_endian(src["val"], 4))
				return opcode
	elif instruction == OP_INT:
		interrupt ,= args
		opcode = bytearray([0xcd, interrupt["val"] & 255])
		return opcode
	elif instruction == OP_ADD:
		dest, src = args
		if dest["type"] == TOKEN_REG:
			if src["type"] == TOKEN_IMM:
				instr = ADD_R_IMM[dest["width"]]
				opcode = bytearray([instr, 0xc0 + dest["val"]] + int_bytes_little_endian(src["val"], 4))
				return opcode			

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
				dest, src = program[ip + 1], program[ip + 2]
				ip += 2
				opcode = get_opc(OP_MOV, dest, src)

			elif token["val"] == OP_INT:
				n = program[ip + 1]
				ip += 1
				opcode = get_opc(OP_INT, n)

			elif token["val"] == OP_ADD:
				dest, src = program[ip + 1], program[ip + 2]
				ip += 2
				opcode = get_opc(OP_ADD, dest, src)

			else:
				assert False, "unreachable"
				
			size += len(opcode)
			output += opcode
			ip += 1

	output[0x44:0x48] = bytearray(int_bytes_little_endian(size, 4))
	output[0x48:0x4c] = bytearray(int_bytes_little_endian(size, 4))

	with open(outfile, "wb") as out:
		out.write(output)	

	os.system(f"chmod +x {outfile}")
	if autorun:
		os.system(f"./{outfile}")
	
def main():
	ra = list(reversed(sys.argv))
	progname = ra.pop()
	infile, outfile, autorun = parse_args(progname, ra)
	
	# program = [{"type": TOKEN_OP, "val": OP_MOV}, {"type": TOKEN_REG, "width": 32, "val": EAX}, {"type": TOKEN_IMM, "val": 1}, {"type": TOKEN_OP, "val": OP_INT}, {"type": TOKEN_IMM, "val": 0x80}]
	program = lex_file(progname, infile)
	compile_program(progname, program, outfile, infile, autorun)

	print("compilation successful")

if __name__ == "__main__":
	main()
