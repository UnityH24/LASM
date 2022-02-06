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