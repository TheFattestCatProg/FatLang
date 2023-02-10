from helpers2 import *
from lexer import Lexer
from parser3 import parse
import os

from codegen2 import gen_c_code
from codegen_fatlang_debug import gen_fatlang_code

if 0:
    type_dict = {
        RawType(Path([]), 'T', 0, []): TypeData.new_raw(BUILD_IN_PACK, RawType(Path([]), 'point', 0, [RawType(Path([]), 'i32', 0, [])])),
        RawType(Path([]), 'U', 0, []): TypeData.new_raw(BUILD_IN_PACK, RawType(Path([]), 'arr', 0, []))
    }
    t = RawType(Path([]), 'arr', 0, [RawType(Path([]), 'T', 0, [])])
    nt = TypeData.new_raw_templates(t, type_dict)
    print(nt)
    quit()
l = Lexer()
l.build()

storage = GlobalStorage()
storage.add_package(BUILD_IN_PACK)

packs = []
for i in os.listdir('./build-in'):
    with open(f'./build-in/{i}', 'r') as file:
       packs.append(parse(file.read(), storage))


for i in os.listdir('./src'):
    with open(f'./src/{i}', 'r') as file:
        packs.append(parse(file.read(), storage))


if storage.is_valid():
    print("success")
    code = gen_c_code(storage)
    #print(code)
    with open("./gcc_gens/test.c", 'w') as file:
        file.write(code)

else:
    print("error, can't build code")
