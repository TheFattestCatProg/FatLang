import ply.yacc as yacc
from helpers2 import *

from lexer import Lexer

tokens = Lexer.tokens

lexer = Lexer()
lexer.build()

tokens = Lexer.tokens
used_types = []

PACKAGE: Optional[Package] = None
STORAGE: Optional[GlobalStorage] = None
SOURCE: Optional[str] = None


def parser_log_error(text, pos):
    log_error(AnalyzerException(text, pos), PACKAGE, None)
    exit(1)


def getpos(p, n=1, max=None) -> Tuple[int, int, int, int]:
    if max is None:
        max = len(p) - 1
    _, end_line = p.linespan(max)
    _, end_pos = p.lexspan(max)
    return p.lineno(n), p.lexpos(n), end_line, end_pos


precedence = (
    ('left', 'EE', 'NE', 'LS', 'GR', 'LE', 'GE'),
    ('left', 'OR'),
    ('left', 'XOR'),
    ('left', 'AND'),
    ('left', 'LSHIFT', 'RSHIFT'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'CAST'),
    ('right', 'UMINUS'),
    ('left', '.'),
    ('left', 'GETTER')
)


def p_error(p):
    log_error(AnalyzerException(f"can't parse this fragment of code", (p.lineno, p.lexpos, p.lineno, p.lexpos)),
              PACKAGE, None)
    exit(1)


def p_code(p):
    '''code : package-declaration import-declarations main-code'''
    pass


def p_package_declaration(p):
    """package-declaration : PACKAGE ID ';'
                            | PACKAGE package-complicated-name ';'
    """
    if type(p[2]) == str:
        path = Path([p[2]])
    else:
        path = Path(p[2])

    global PACKAGE
    PACKAGE = Package(path, [])
    PACKAGE.sources = SOURCE
    STORAGE.add_package(PACKAGE)


def p_package_complicated_name1(p):
    """package-complicated-name : package-complicated-name ':' ID
                                | ID ':' ID
    """
    if type(p[1]) == list:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [p[1], p[3]]

def p_package_complicated_name2(p):
    """package-complicated-name :
    """
    p[0] = ['']


def p_import_declarations(p):
    """import-declarations : import-declarations import-declaration
                           | import-declaration
                           |
    """
    if len(p) == 2:
        PACKAGE.imports.append(p[1])
    elif len(p) == 3:
        PACKAGE.imports.append(p[2])


def p_import_declaration(p):
    """import-declaration : USING ID ';'
                        | USING package-complicated-name ';'
    """

    if type(p[2]) == str:
        p[0] = Path([p[2]])
    else:
        p[0] = Path(p[2])


def p_main_code(p):
    """main-code : main-code main
                |
    """
    pass


def p_main_function_declaration1(p):
    """main : ID ID function-arguments function-body
            | complicated-type ID function-arguments function-body
    """
    ret_type = p[1]
    if type(ret_type) == str:
        ret_type = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, ret_type, p[2], p[3], [], p[4], True, getpos(p))
    STORAGE.register(f)


def p_main_function_declaration2(p):
    """main : ID ID template-declaration function-arguments function-body
            | complicated-type ID template-declaration function-arguments function-body
    """
    ret_type = p[1]
    if type(ret_type) == str:
        ret_type = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, ret_type, p[2], p[4], p[3], p[5], True, getpos(p))
    STORAGE.register(f)

def p_main_function_declaration3(p):
    """main : UNSAFE ID ID function-arguments function-body
            | UNSAFE complicated-type ID function-arguments function-body
    """
    ret_type = p[2]
    if type(ret_type) == str:
        ret_type = RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))

    f = FunctionDeclaration(PACKAGE, ret_type, p[3], p[4], [], p[5], False, getpos(p))
    STORAGE.register(f)


def p_main_function_declaration4(p):
    """main : UNSAFE ID ID template-declaration function-arguments function-body
            | UNSAFE complicated-type ID template-declaration function-arguments function-body
    """
    ret_type = p[2]
    if type(ret_type) == str:
        ret_type = RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))

    f = FunctionDeclaration(PACKAGE, ret_type, p[3], p[5], p[4], p[6], False, getpos(p))
    STORAGE.register(f)
    
def p_main_operator_declaration1(p):
    """main : ID OPERATOR binary-operator function-arguments function-body
            | ID OPERATOR TIMES function-arguments function-body
            | ID OPERATOR LS function-arguments function-body
            | ID OPERATOR GR function-arguments function-body
            | complicated-type OPERATOR binary-operator function-arguments function-body
            | complicated-type OPERATOR TIMES function-arguments function-body
            | complicated-type OPERATOR LS function-arguments function-body
            | complicated-type OPERATOR GR function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__binary_operator_{operator_to_text(p[3])}', p[4], [], p[5], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration2(p):
    """main : ID OPERATOR binary-operator template-declaration function-arguments function-body
            | ID OPERATOR TIMES template-declaration function-arguments function-body
            | ID OPERATOR LS template-declaration function-arguments function-body
            | ID OPERATOR GR template-declaration function-arguments function-body
            | complicated-type OPERATOR binary-operator template-declaration function-arguments function-body
            | complicated-type OPERATOR TIMES template-declaration function-arguments function-body
            | complicated-type OPERATOR LS template-declaration function-arguments function-body
            | complicated-type OPERATOR GR template-declaration function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__binary_operator_{operator_to_text(p[3])}', p[5], p[4], p[6], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration3(p):
    """main : ID OPERATOR binary-operator '(' ')' function-arguments function-body
            | ID OPERATOR '!' '(' ')' function-arguments function-body
            | complicated-type OPERATOR binary-operator '(' ')' function-arguments function-body
            | complicated-type OPERATOR '!' '(' ')' function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__unary_operator_{operator_to_text(p[3])}', p[6], [], p[7], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration31(p):
    """main : ID OPERATOR binary-operator '(' ')' template-declaration function-arguments function-body
            | ID OPERATOR '!' '(' ')' template-declaration function-arguments function-body
            | complicated-type OPERATOR binary-operator '(' ')' template-declaration function-arguments function-body
            | complicated-type OPERATOR '!' '(' ')' template-declaration function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__unary_operator_{operator_to_text(p[3])}', p[7], p[6], p[8], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration4(p):
    """main : ID OPERATOR '(' ')' function-arguments function-body
            | complicated-type OPERATOR '(' ')' function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    STORAGE._register_cast((PACKAGE, t, p[5][0], p[6]))  # TODO: make normally

def p_main_operator_declaration5(p):
    """main : OPERATOR '~' function-arguments function-body
    """
    t = VOID_T.raw.copy()
    t.position = getpos(p)

    f = FunctionDeclaration(PACKAGE, t, '__destructor', p[3], [], p[4], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration6(p):
    """main : OPERATOR '~' template-declaration function-arguments function-body
    """
    t = VOID_T.raw.copy()
    t.position = getpos(p)

    f = FunctionDeclaration(PACKAGE, t, '__destructor', p[4], p[3], p[5], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration7(p):
    """main : ID OPERATOR '[' ']' function-arguments function-body
            | complicated-type OPERATOR '[' ']' function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, '__binary_operator_square_brackets', p[5], [], p[6], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration8(p):
    """main : ID OPERATOR '[' ']' template-declaration function-arguments function-body
            | complicated-type OPERATOR '[' ']' template-declaration function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, '__binary_operator_square_brackets', p[6], p[5], p[7], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration9(p):
    """main : ID OPERATOR '=' function-arguments function-body
            | complicated-type OPERATOR '=' function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__copy', p[4], [], p[5], True, getpos(p))
    STORAGE.register(f)

def p_main_operator_declaration10(p):
    """main : ID OPERATOR '=' template-declaration function-arguments function-body
            | complicated-type OPERATOR '=' template-declaration function-arguments function-body
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    f = FunctionDeclaration(PACKAGE, t, f'__copy', p[5], p[4], p[6], True, getpos(p))
    STORAGE.register(f)


def p_main_extern_function_declaration(p):
    """main : EXTERN ID ID function-arguments ';'
            | EXTERN complicated-type ID function-arguments ';'
    """
    t = p[2]
    if type(t) == str:
        t = RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))
    f = FunctionDeclaration(PACKAGE, t, p[3], p[4], [], None, False, getpos(p))
    STORAGE.register(f)


def p_complicated_type1(p):
    """complicated-type : package-complicated-name ':' ID
                        | package-complicated-name ':' ID TIMES
                        | package-complicated-name ':' ID complicated-pointer-level
    """
    if len(p) == 4:
        p[0] = RawType(Path(p[1]), p[3], 0, [], PACKAGE, getpos(p), False)
    elif type(p[4]) == str:
        p[0] = RawType(Path(p[1]), p[3], 1, [], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(Path(p[1]), p[3], p[4], [], PACKAGE, getpos(p), False)

def p_complicated_type2(p):
    """complicated-type : ID ':' ID
                        | ID ':' ID TIMES
                        | ID ':' ID complicated-pointer-level
    """
    if len(p) == 4:
        p[0] = RawType(Path([p[1]]), p[3], 0, [], PACKAGE, getpos(p), False)
    elif type(p[4]) == str:
        p[0] = RawType(Path([p[1]]), p[3], 1, [], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(Path([p[1]]), p[3], p[4], [], PACKAGE, getpos(p), False)


def p_complicated_type3(p):
    """complicated-type : package-complicated-name ':' ID template-declaration
                        | package-complicated-name ':' ID template-declaration TIMES
                        | package-complicated-name ':' ID template-declaration complicated-pointer-level
    """
    if len(p) == 5:
        p[0] = RawType(Path(p[1]), p[3], 0, p[4], PACKAGE, getpos(p), False)
    elif type(p[5]) == str:
        p[0] = RawType(Path(p[1]), p[3], 1, p[4], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(Path(p[1]), p[3], p[4], p[4], PACKAGE, getpos(p), False)

def p_complicated_type4(p):
    """complicated-type : ID ':' ID template-declaration
                        | ID ':' ID template-declaration TIMES
                        | ID ':' ID template-declaration complicated-pointer-level
    """
    if len(p) == 5:
        p[0] = RawType(Path([p[1]]), p[3], 0, p[4], PACKAGE, getpos(p), False)
    elif type(p[5]) == str:
        p[0] = RawType(Path([p[1]]), p[3], 1, p[4], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(Path([p[1]]), p[3], p[4], p[4], PACKAGE, getpos(p), False)


def p_complicated_type5(p):
    """complicated-type : ID template-declaration
                        | ID template-declaration TIMES
                        | ID template-declaration complicated-pointer-level
    """
    path = Path([])
    if len(p) == 3:
        p[0] = RawType(path, p[1], 0, p[2], PACKAGE, getpos(p), False)
    elif type(p[3]) == str:
        p[0] = RawType(path, p[1], 1, p[2], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(path, p[1], p[3], p[2], PACKAGE, getpos(p), False)


def p_complicated_type6(p):
    """complicated-type : ID TIMES
                        | ID complicated-pointer-level
    """
    path = Path([])
    if type(p[2]) == str:
        p[0] = RawType(path, p[1], 1, [], PACKAGE, getpos(p), False)
    else:
        p[0] = RawType(path, p[1], p[2], [], PACKAGE, getpos(p), False)

def p_complicated_type7(p):
    """complicated-type : CONST complicated-type"""
    t = p[2]
    t.is_const = True
    p[0] = t


def p_complicated_pointer_level(p):
    """complicated-pointer-level : complicated-pointer-level TIMES
                                | TIMES TIMES
    """
    if type(p[1]) == str:
        p[0] = 2
    else:
        p[0] = p[1] + 1


def p_template_declaration1(p):
    """template-declaration : LS template-declaration-body GR
    """
    p[0] = p[2]


def p_template_declaration2(p):
    """template-declaration : LS ID GR
    """
    p[0] = [RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))]


def p_template_declaration3(p):
    """template-declaration : LS complicated-type GR
    """
    p[0] = [p[2]]


def p_template_declaration_body1(p):
    """template-declaration-body : template-declaration-body ',' ID
                                | template-declaration-body ',' complicated-type
    """
    p[0] = p[1]
    if type(p[3]) == str:
        p[0].append(RawType(Path([]), p[3], 0, [], PACKAGE, getpos(p, 3, 3)))
    else:
        p[0].append(p[3])


def p_template_declaration_body2(p):
    """template-declaration-body :  ID ',' ID
                                | complicated-type ',' ID
    """
    t2 = RawType(Path([]), p[3], 0, [], PACKAGE, getpos(p, 3, 3))
    t1 = p[1]
    if type(t1) == str:
        t1 = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    p[0] = [t1, t2]


def p_template_declaration_body3(p):
    """template-declaration-body : ID ',' complicated-type
                                | complicated-type ',' complicated-type
    """
    t2 = p[3]
    t1 = p[1]
    if type(t1) == str:
        t1 = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    p[0] = [t1, t2]


def p_p_function_arguments(p):
    """function-arguments : '(' function-arguments-body ')'
                        | '(' ')'
    """
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = []


def p_function_arguments_body(p):
    """function-arguments-body : function-arguments-body ',' function-argument
                        | function-argument
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])


def p_function_argument(p):
    """function-argument : ID ID
                        | complicated-type ID
    """
    if type(p[1]) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))
    else:
        t = p[1]

    p[0] = (t, p[2])


def p_function_body(p):
    """function-body : '{' expression-lines '}'"""
    body = FunctionBody()
    for i in p[2]:
        body.add_expression(i)
    p[0] = body


def p_struct_declaration1(p):
    """main : STRUCT ID struct-body"""
    fields, methods = p[3], []
    struct = StructDeclaration(PACKAGE, p[2], fields, methods, [], False, getpos(p))
    STORAGE.register(struct)


def p_struct_declaration2(p):
    """main : STRUCT ID template-declaration struct-body"""
    fields, methods = p[4], []
    struct = StructDeclaration(PACKAGE, p[2], fields, methods, p[3], False, getpos(p))
    STORAGE.register(struct)

def p_extern_struct_declaration1(p):
    """main : EXTERN STRUCT ID struct-body"""
    fields, methods = p[4], []
    struct = StructDeclaration(PACKAGE, p[3], fields, methods, [], True, getpos(p))
    STORAGE.register(struct)


def p_struct_body(p):
    """struct-body : '{' struct-fields '}'"""
    p[0] = p[2]


def p_struct_body_fields(p):
    """struct-fields : struct-fields struct-field
                    |
    """
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1]
        p[0].append(p[2])


def p_struct_field1(p):
    """struct-field : ID ID ';'
                    | complicated-type ID ';'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))
    p[0] = ('public', t, p[2])

def p_struct_field2(p):
    """struct-field : ACCMOD ID ID ';'
                    | ACCMOD complicated-type ID ';'
    """
    t = p[2]
    if type(t) == str:
        t = RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))
    p[0] = (p[1], t, p[3])


def p_expression_lines(p):
    """expression-lines : expression-lines expression-line
                        | expression-line
                        |
    """
    if len(p) == 1:
        p[0] = []
    elif len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[2])


def p_expression_line1(p):
    """expression-line : complicated-expression ';'
                        | return-statement
                        | variable-declaration
                        | if-statement
                        | while-statement
                        | unsafe-area
                        | visibility-area
                        | set-statement
    """
    p[0] = p[1]

def p_expression_line2(p):
    """expression-line : ID ';'"""
    p[0] = VariableExpression(p[1], getpos(p, 1, 1))


def p_return_statement(p):
    """return-statement : RETURN complicated-expression ';'
                        | RETURN ID ';'
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))

    p[0] = ReturnExpression(expr, getpos(p))


def p_variable_declaration1(p):
    """variable-declaration : ID ID ';'
                            | complicated-type ID ';'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))
    p[0] = VariableCreationExpression(p[2], None, t, getpos(p))


def p_variable_declaration2(p):
    """variable-declaration : ID ID '=' ID ';'
                            | complicated-type ID '=' ID ';'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    expr = VariableExpression(p[4], getpos(p, 4, 4))
    p[0] = VariableCreationExpression(p[2], expr, t, getpos(p))


def p_variable_declaration3(p):
    """variable-declaration : ID ID '=' complicated-expression ';'
                            | complicated-type ID '=' complicated-expression ';'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))
    p[0] = VariableCreationExpression(p[2], p[4], t, getpos(p))

def p_variable_declaration4(p):
    """variable-declaration : VAR ID '=' ID ';'
                            | VAR ID '=' complicated-expression ';'
    """
    expr = p[4]
    if type(expr) == str:
        expr = VariableExpression(p[4], getpos(p, 4, 4))
    t = NOTYPE_T.raw.copy()
    t.position = getpos(p, 1, 1)
    p[0] = VariableCreationExpression(p[2], expr, t, getpos(p))


def p_if_statement1(p):
    """if-statement : IF complicated-expression visibility-area
                    | IF complicated-expression visibility-area ELSE visibility-area
                    | IF complicated-expression visibility-area ELSE if-statement
    """
    else_body = None
    if len(p) != 4:
        else_body = p[5]

    p[0] = IfExpression(p[2], p[3], else_body, getpos(p))


def p_if_statement2(p):
    """if-statement : IF ID visibility-area
                    | IF ID visibility-area ELSE visibility-area
                    | IF ID visibility-area ELSE if-statement
    """
    else_body = None
    if len(p) != 4:
        else_body = p[6]

    expr = VariableExpression(p[2], getpos(p, 2, 2))
    p[0] = IfExpression(expr, p[3], else_body, getpos(p))


def p_while_statement1(p):
    """while-statement : WHILE complicated-expression visibility-area"""
    p[0] = WhileExpression(p[2], p[3], getpos(p))


def p_while_statement2(p):
    """while-statement : WHILE ID visibility-area"""
    expr = VariableExpression(p[2], getpos(p, 2, 2))
    p[0] = WhileExpression(expr, p[3], getpos(p))


def p_unsafe_area(p):
    """unsafe-area : UNSAFE visibility-area"""
    p[0] = UnsafeExpression(p[2], getpos(p))

def p_unsafe_expression(p):
    """complicated-expression : UNSAFE complicated-expression"""
    p[0] = UnsafeExpression(p[2], getpos(p))

def p_array_creation_expression1(p):
    """complicated-expression : '[' ']'
    """
    raise NotImplementedError

def p_array_creation_expression2(p):
    """complicated-expression : '[' ID ']'
                            | '[' complicated-expression ']'
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))
    p[0] = ArrayCreationExpression([expr], getpos(p))

def p_array_creation_expression3(p):
    """complicated-expression : '[' invoke-arguments-list ']'
    """
    p[0] = ArrayCreationExpression(p[2], getpos(p))

def p_struct_construct_expression1(p):
    """complicated-expression : ID '{' invoke-arguments-list '}'
                                | complicated-type '{' invoke-arguments-list '}'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    p[0] = StructConstructorExpression(t, p[3], getpos(p))

def p_struct_construct_expression2(p):
    """complicated-expression : ID '{' ID '}'
                                | ID '{' complicated-expression '}'
                                | complicated-type '{' ID '}'
                                | complicated-type '{' complicated-expression '}'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    expr = p[3]
    if type(expr) == str:
        expr = VariableExpression(p[3], getpos(p, 3, 3))

    p[0] = StructConstructorExpression(t, [expr], getpos(p))

def p_struct_construct_expression3(p):
    """complicated-expression : ID '{' '}'
                                | complicated-type '{' '}'
    """
    t = p[1]
    if type(t) == str:
        t = RawType(Path([]), p[1], 0, [], PACKAGE, getpos(p, 1, 1))

    p[0] = StructConstructorExpression(t, [], getpos(p))

def p_square_brackets_expression(p):
    """complicated-expression : ID '[' ID ']'
                            | ID '[' complicated-expression ']'
                            | complicated-expression '[' ID ']'
                            | complicated-expression '[' complicated-expression ']'
    """
    expr1 = p[1]
    if type(expr1) == str:
        expr1 = VariableExpression(p[1], getpos(p, 1, 1))

    expr2 = p[3]
    if type(expr2) == str:
        expr2 = VariableExpression(p[3], getpos(p, 3, 3))

    p[0] = BinaryOperatorExpression(expr1, expr2, '[]', getpos(p))

def p_set_statement1(p):
    """set-statement : ID '=' ID ';'
                    | complicated-expression '=' ID ';'
    """
    from_expr = VariableExpression(p[3], getpos(p, 3, 3))
    to = p[1]

    if type(to) == str:
        to = VariableExpression(p[1], getpos(p, 1, 1))

    p[0] = ExpressionValueSetExpression(to, from_expr, getpos(p))


def p_set_statement2(p):
    """set-statement : ID '=' complicated-expression ';'
                    | complicated-expression '=' complicated-expression ';'
    """
    to = p[1]

    if type(to) == str:
        to = VariableExpression(p[1], getpos(p, 1, 1))

    p[0] = ExpressionValueSetExpression(to, p[3], getpos(p))


def p_visibility_area(p):
    """visibility-area : function-body"""
    area = VisibilityAreaExpression(p[1].expressions, getpos(p))
    p[0] = area

def p_constant_expression(p):
    """constant-expression : INT
                            | FLOAT
                            | STR
                            | BOOL
                            | CHAR
    """
    p[0] = Constant(p[1], getpos(p))

def p_unpack_expression(p):
    """complicated-expression : TIMES ID
                            | TIMES complicated-expression
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))
    p[0] = PointerUnpackExpression(expr, getpos(p))

def p_pack_expression(p):
    """complicated-expression : AND ID
                            | AND complicated-expression
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))
    p[0] = PointerGetExpression(expr, getpos(p))

def p_getter_expression(p):
    """complicated-expression : ID '.' ID %prec GETTER
                            | complicated-expression '.' ID %prec GETTER
    """
    expr = p[1]
    if type(expr) == str:
        expr = VariableExpression(p[1], getpos(p, 1, 1))

    p[0] = GetterExpression(expr, p[3], getpos(p))

def p_sizeof_expression(p):
    """complicated-expression : SIZEOF '(' ID ')'
                            | SIZEOF '(' complicated-type ')'
    """
    t = p[3]
    if type(t) == str:
        t = RawType(Path([]), p[3], 0, [], PACKAGE, getpos(p, 3, 3))
    p[0] = SizeofExpression(t, getpos(p))  # TODO: typeid & typestr

def p_function_invoke_expression1(p):
    """complicated-expression : ID invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path([]), p[1], p[2], [], getpos(p))

def p_function_invoke_expression2(p):
    """complicated-expression : ID ':' ID invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path([p[1]]), p[3], p[4], [], getpos(p))

def p_function_invoke_expression3(p):
    """complicated-expression : package-complicated-name ':' ID invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path(p[1]), p[3], p[4], [], getpos(p))

def p_function_invoke_expression4(p):
    """complicated-expression : ID template-declaration invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path([]), p[1], p[3], p[2], getpos(p))

def p_function_invoke_expression5(p):
    """complicated-expression : ID ':' ID template-declaration invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path([p[1]]), p[3], p[5], p[4], getpos(p))

def p_function_invoke_expression6(p):
    """complicated-expression : package-complicated-name ':' ID template-declaration invoke-arguments
    """
    p[0] = FunctionInvokeExpression(Path(p[1]), p[3], p[5], p[4], getpos(p))

def p_method_invoke_expression1(p):
    """complicated-expression : ID '.' ID invoke-arguments
                            | complicated-expression '.' ID invoke-arguments
    """
    from_expr = p[1]
    if type(from_expr) == str:
        from_expr = VariableExpression(p[1], getpos(p, 1, 1))
    p[0] = FunctionInvokeExpression(Path([]), p[3], [from_expr] + p[4], [], getpos(p))

def p_method_invoke_expression2(p):
    """complicated-expression : ID '.' ID template-declaration invoke-arguments
                            | complicated-expression '.' ID template-declaration invoke-arguments
    """
    from_expr = p[1]
    if type(from_expr) == str:
        from_expr = VariableExpression(p[1], getpos(p, 1, 1))
    p[0] = FunctionInvokeExpression(Path([]), p[3], [from_expr] + p[5], p[4], getpos(p))

def p_function_invoke_arguments1(p):
    """invoke-arguments : '(' ')'
    """
    p[0] = []

def p_function_invoke_arguments2(p):
    """invoke-arguments : '(' ID ')'
                        | '(' complicated-expression ')'
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))

    p[0] = [expr]

def p_function_invoke_arguments3(p):
    """invoke-arguments : '(' invoke-arguments-list ')'
    """
    p[0] = p[2]

def p_function_invoke_arguments_list1(p):
    """invoke-arguments-list : invoke-arguments-list ',' ID
                            | invoke-arguments-list ',' complicated-expression
    """
    expr = p[3]
    if type(expr) == str:
        expr = VariableExpression(p[3], getpos(p, 3, 3))

    p[0] = p[1]
    p[0].append(expr)

def p_function_invoke_arguments_list2(p):
    """invoke-arguments-list : ID ',' ID
                            | complicated-expression ',' ID
    """
    expr1 = p[1]
    if type(expr1) == str:
        expr1 = VariableExpression(p[1], getpos(p, 1, 1))
    expr2 = VariableExpression(p[3], getpos(p, 3, 3))
    p[0] = [expr1, expr2]

def p_function_invoke_arguments_list3(p):
    """invoke-arguments-list : ID ',' complicated-expression
                            | complicated-expression ',' complicated-expression
    """
    expr1 = p[1]
    if type(expr1) == str:
        expr1 = VariableExpression(p[1], getpos(p, 1, 1))
    p[0] = [expr1, p[3]]

def p_complicated_expression1(p):
    """complicated-expression : ID binary-operator ID
                            | ID TIMES ID
                            | ID LS ID
                            | ID GR ID
                            | complicated-expression binary-operator ID
                            | complicated-expression LS ID
                            | complicated-expression GR ID
                            | complicated-expression TIMES ID
                            | ID binary-operator complicated-expression
                            | ID LS complicated-expression
                            | ID GR complicated-expression
                            | ID TIMES complicated-expression
                            | complicated-expression binary-operator complicated-expression
                            | complicated-expression LS complicated-expression
                            | complicated-expression GR complicated-expression
                            | complicated-expression TIMES complicated-expression
    """
    expr1 = p[1]
    if type(expr1) == str:
        expr1 = VariableExpression(p[1], getpos(p, 1, 1))

    expr2 = p[3]
    if type(expr2) == str:
        expr2 = VariableExpression(p[3], getpos(p, 3, 3))

    p[0] = BinaryOperatorExpression(expr1, expr2, p[2], getpos(p))

def p_complicated_expression2(p):
    """complicated-expression : MINUS ID %prec UMINUS
                            | MINUS complicated-expression %prec UMINUS
                            | '!' ID %prec UMINUS
                            | '!' complicated-expression %prec UMINUS
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))

    p[0] = UnaryOperatorExpression(expr, p[1], getpos(p))

def p_complicated_expression4(p):
    """complicated-expression : constant-expression"""
    p[0] = p[1]


def p_complicated_expression5(p):
    """complicated-expression : '(' ID ')'
                            | '(' complicated-expression ')'
    """
    expr = p[2]
    if type(expr) == str:
        expr = VariableExpression(p[2], getpos(p, 2, 2))

    p[0] = expr


def p_complicated_expression6(p):
    """complicated-expression : '(' ID ')' ID %prec CAST
                            | '(' ID ')' complicated-expression %prec CAST
    """
    t = RawType(Path([]), p[2], 0, [], PACKAGE, getpos(p, 2, 2))
    expr = p[4]
    if type(expr) == str:
        expr = VariableExpression(p[4], getpos(p, 4, 4))

    p[0] = CastExpression(t, expr, getpos(p))

def p_complicated_expression7(p):
    """complicated-expression : '(' complicated-type ')' ID %prec CAST
                            | '(' complicated-type ')' complicated-expression %prec CAST
    """
    expr = p[4]
    if type(expr) == str:
        expr = VariableExpression(p[4], getpos(p, 4, 4))

    p[0] = CastExpression(p[2], expr, getpos(p))

def p_eq_operator(p):
    """sub-equal-operator : PLUSEQ
                        | MINUSEQ
                        | TIMESEQ
                        | DIVIDEEQ
                        | MODEQ
                        | ANDEQ
                        | OREQ
                        | XOREQ
                        | LSHIFTEQ
                        | RSHIFTEQ
    """
    p[0] = p[1]

def p_complicated_expression8(p):
    """complicated-expression : ID sub-equal-operator ID
                        | complicated-expression sub-equal-operator ID
                        | ID sub-equal-operator complicated-expression
                        | complicated-expression sub-equal-operator complicated-expression
    """
    expr_to_copy = p[1]
    if type(expr_to_copy) == str:
        expr_to_copy = VariableExpression(p[1], getpos(p, 1, 1))
    expr = p[3]
    if type(expr) == str:
        expr = VariableExpression(p[3], getpos(p, 3, 3))

    p[0] = ExpressionValueSetExpression(expr_to_copy.copy(), BinaryOperatorExpression(expr_to_copy, expr, p[2][:-1], getpos(p)), getpos(p))

def p_binary_operator(p):
    """binary-operator : PLUS
                        | MINUS
                        | DIVIDE
                        | MOD
                        | AND
                        | OR
                        | XOR
                        | LSHIFT
                        | RSHIFT
                        | LE
                        | GE
                        | EE
                        | NE
    """
    p[0] = p[1]


parser = yacc.yacc()


def parse(t: str, storage: GlobalStorage):
    global STORAGE, SOURCE
    SOURCE = t
    STORAGE = storage
    lexer.lexer.lineno = 0
    lexer.lexer.lexpos = 0
    parser.parse(t, lexer=lexer.lexer, tracking=True)# , debug=True)
    return PACKAGE


if __name__ == "__main__":
    parse("""
    package main:beda;
    using kek:io;
    
    struct A<T> {
        i32<T> field;
    }
    
    extern void* kek(i32 val);
    
    """, GlobalStorage())
