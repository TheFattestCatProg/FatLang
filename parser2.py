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
    ('right', 'UMINUS', 'UPLUS'),
    ('right', 'CAST'),
    ('nonassoc', 'BRACKETS'),
    ('nonassoc', 'SQUARE_BRACKETS'),
    ('left', '.')
)


def p_error(p):
    log_error(AnalyzerException(f"can't parse this fragment of code", (p.lineno, p.lexpos, p.lineno, p.lexpos)), PACKAGE, None)
    exit(1)


def p_code(p):
    '''code : package-declaration import-declarations main'''


def p_package_declaration(p):
    '''package-declaration : PACKAGE path ';'
                        | PACKAGE ID ';'
    '''
    global PACKAGE
    if not isinstance(p[2], Path):
        p[2] = Path([p[2]])

    PACKAGE = Package(p[2], [])
    PACKAGE.sources = SOURCE
    STORAGE.add_package(PACKAGE)


def p_import_declarations(p):
    '''import-declarations : import-declarations import-declaration
                        | import-declaration
                        |
    '''
    if len(p) == 2:
        PACKAGE.imports.append(p[1])
    elif len(p) == 3:
        PACKAGE.imports.append(p[2])


def p_import_declaration(p):
    """import-declaration : USING path ';'
                        | USING ID ';'
    """
    if not isinstance(p[2], Path):
        p[2] = Path([p[2]])
    p[0] = p[2]


def p_main(p):
    'main : '
    pass


def p_main_function_declaration(p):
    'main : main function-declaration'
    STORAGE.register(p[2])

def p_main_struct_declaration(p):
    'main : main struct-declaration'
    STORAGE.register(p[2])

def p_main_operator_declaration(p):
    'main : main operator-declaration'
    if p[2] is not None:  # because cast may be None
        STORAGE.register(p[2])

def p_main_variable_declaration(p):
    'main : main variable-declaration'
    raise NotImplementedError

#####################################################
#               FUNCTION_DECLARATION                #
#####################################################

def p_function_declaration(p):
    '''function-declaration : type ID '(' function-arguments-declaration ')' function-body
    '''
    p[0] = FunctionDeclaration(PACKAGE, p[1], p[2], p[4], [], p[6], position=getpos(p))

def p_unsafe_function_declaration(p):
    '''function-declaration : UNSAFE type ID '(' function-arguments-declaration ')' function-body
    '''
    p[0] = FunctionDeclaration(PACKAGE, p[2], p[3], p[5], [], p[7], False, position=getpos(p))


def p_function_declaration_extern(p):
    '''function-declaration : EXTERN type ID '(' function-arguments-declaration ')' ';'
    '''
    p[0] = FunctionDeclaration(PACKAGE, p[2], p[3], p[5], [], None, False, position=getpos(p))


def p_function_declaration_template(p):
    '''function-declaration : type ID template-declaration '(' function-arguments-declaration ')' function-body
    '''
    p[0] = FunctionDeclaration(PACKAGE, p[1], p[2], p[5], p[3], p[7], position=getpos(p))

def p_unsafe_function_declaration_template(p):
    '''function-declaration : UNSAFE type ID template-declaration '(' function-arguments-declaration ')' function-body
    '''
    p[0] = FunctionDeclaration(PACKAGE, p[2], p[3], p[6], p[4], p[8], False, position=getpos(p))


def p_function_arguments_declaration(p):
    '''function-arguments-declaration : function-arguments-declaration ',' type ID
                    | type ID
                    |
    '''
    l = len(p)
    if l == 1:
        p[0] = []
    elif l == 3:
        p[0] = [(p[1], p[2])]
    else:
        p[0] = p[1]
        p[0].append((p[3], p[4]))


def p_function_body(p):
    "function-body : '{' expression-lines '}'"
    body = FunctionBody()
    for i in p[2]:
        body.add_expression(i)
    p[0] = body


def p_function_body_expression_lines(p):
    '''expression-lines : expression-lines expression-line
                | expression-line
    '''
    if len(p) == 3:
        p[0] = p[1]
        if p[2] is not None:
            p[0].append(p[2])
    else:
        if p[1] is not None:
            p[0] = [p[1]]
        else:
            p[0] = []

def p_expression_line(p):
    '''expression-line :
                | if
                | for
                | while
                | unsafe-area
                | visibility-area
                | return-expression ';'
                | variable-declaration ';'
                | variable-declaration-looks-like ';'
                | expression-set ';'
                | equals-operation ';'
                | compound-expression ';'
    '''
    p[0] = p[1] if len(p) > 1 else None

#####################################################
#               OPERATOR_DECLARATION                #
#####################################################

def p_operator_declaration_plus(p):
    """operator-declaration : type OPERATOR PLUS '(' type ID ',' type ID ')' function-body
                            | type OPERATOR PLUS template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_plus', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_plus', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_minus(p):
    """operator-declaration : type OPERATOR MINUS '(' type ID ',' type ID ')' function-body
                            | type OPERATOR MINUS template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_minus', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_minus', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_times(p):
    """operator-declaration : type OPERATOR TIMES '(' type ID ',' type ID ')' function-body
                            | type OPERATOR TIMES template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_times', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_times', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_divide(p):
    """operator-declaration : type OPERATOR DIVIDE '(' type ID ',' type ID ')' function-body
                            | type OPERATOR DIVIDE template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_divide', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_divide', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_mod(p):
    """operator-declaration : type OPERATOR MOD '(' type ID ',' type ID ')' function-body
                            | type OPERATOR MOD template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_mod', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_mod', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_and(p):
    """operator-declaration : type OPERATOR AND '(' type ID ',' type ID ')' function-body
                            | type OPERATOR AND template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_and', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_and', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_or(p):
    """operator-declaration : type OPERATOR OR '(' type ID ',' type ID ')' function-body
                            | type OPERATOR OR template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_or', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_or', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_xor(p):
    """operator-declaration : type OPERATOR XOR '(' type ID ',' type ID ')' function-body
                            | type OPERATOR XOR template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_xor', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_xor', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_lshift(p):
    """operator-declaration : type OPERATOR LSHIFT '(' type ID ',' type ID ')' function-body
                            | type OPERATOR LSHIFT template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_lshift', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_lshift', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_rshift(p):
    """operator-declaration : type OPERATOR RSHIFT '(' type ID ',' type ID ')' function-body
                            | type OPERATOR RSHIFT template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_rshift', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_rshift', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_less(p):
    """operator-declaration : type OPERATOR LS '(' type ID ',' type ID ')' function-body
                            | type OPERATOR LS template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_less', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_less', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_less_equals(p):
    """operator-declaration : type OPERATOR LE '(' type ID ',' type ID ')' function-body
                            | type OPERATOR LE template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_less_equals', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_less_equals', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_greater(p):
    """operator-declaration : type OPERATOR GR '(' type ID ',' type ID ')' function-body
                            | type OPERATOR GR template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_greater', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_greater', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_greater_equals(p):
    """operator-declaration : type OPERATOR GE '(' type ID ',' type ID ')' function-body
                            | type OPERATOR GE template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_greater_equals', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_greater_equals', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_equals(p):
    """operator-declaration : type OPERATOR EE '(' type ID ',' type ID ')' function-body
                            | type OPERATOR EE template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_equals', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_equals', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_not_equals(p):
    """operator-declaration : type OPERATOR NE '(' type ID ',' type ID ')' function-body
                            | type OPERATOR NE template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 12:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_not_equals', [(p[5], p[6]), (p[8], p[9])], [], p[11], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__binary_operator_not_equals', [(p[6], p[7]), (p[9], p[10])], p[4], p[12], position=getpos(p))

def p_operator_declaration_cast(p):
    """operator-declaration : type OPERATOR '(' ')' '(' type ID ')' function-body
                            | type OPERATOR template-declaration '(' ')' '(' type ID ')' function-body
    """
    if len(p) == 10:
        STORAGE._register_cast((PACKAGE, p[1], (p[6], p[7]), p[9]))
    else:
        raise NotImplementedError

def p_operator_declaration_square_brackets(p):
    """operator-declaration : type OPERATOR '[' ']' '(' type ID ',' type ID ')' function-body
                            | type OPERATOR '[' ']' template-declaration '(' type ID ',' type ID ')' function-body
    """
    if len(p) == 13:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__operator_square_brackets', [(p[6], p[7]), (p[9], p[10])], [], p[12], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__operator_square_brackets', [(p[7], p[8]), (p[10], p[11])], p[5], p[13], position=getpos(p))

def p_operator_declaration_unary_minus(p):
    """operator-declaration : type OPERATOR MINUS '(' ')' '(' type ID ')' function-body
                            | type OPERATOR MINUS '(' ')' template-declaration '(' type ID ')' function-body
    """
    if len(p) == 11:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_minus', [(p[7], p[8])], [], p[10], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_minus', [(p[8], p[9])], p[6], p[11], position=getpos(p))

def p_operator_declaration_unary_plus(p):
    """operator-declaration : type OPERATOR PLUS '(' ')' '(' type ID ')' function-body
                            | type OPERATOR PLUS '(' ')' template-declaration '(' type ID ')' function-body
    """
    if len(p) == 11:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_plus', [(p[7], p[8])], [], p[10], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_plus', [(p[8], p[9])], p[6], p[11], position=getpos(p))

def p_operator_declaration_unary_not(p):
    """operator-declaration : type OPERATOR '!' '(' ')' '(' type ID ')' function-body
                            | type OPERATOR '!' '(' ')' template-declaration '(' type ID ')' function-body
    """
    if len(p) == 11:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_not', [(p[7], p[8])], [], p[10], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__unary_operator_not', [(p[8], p[9])], p[6], p[11], position=getpos(p))

# TODO: make assign void (T* this, const T* other)
def p_operator_declaration_copy(p):
    """operator-declaration : type OPERATOR '=' '(' type ID ')' function-body
                            | type OPERATOR '=' template-declaration '(' type ID ')' function-body
    """
    if len(p) == 9:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__copy', [(p[5], p[6])], [], p[8], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, p[1], '__copy', [(p[6], p[7])], p[4], p[9], position=getpos(p))

def p_operator_declaration_destructor(p):
    """operator-declaration : OPERATOR '~' '(' type ID ')' function-body
                            | OPERATOR '~' template-declaration '(' type ID ')' function-body
    """
    if len(p) == 8:
        p[0] = FunctionDeclaration(PACKAGE, VOID_T.raw, '__destructor', [(p[4], p[5])], [], p[7], position=getpos(p))
    else:
        p[0] = FunctionDeclaration(PACKAGE, VOID_T.raw, '__destructor', [(p[5], p[6])], p[3], p[8], position=getpos(p))

#####################################################
#                STRUCT_DECLARATION                 #
#####################################################

def split_fields_methods(l) -> Tuple[list, list]:
    methods = []
    fields = []
    for i in l:
        if len(i) > 3:
            methods.append(i)
        else:
            fields.append(i)
    return fields, methods

def p_struct_declaration(p):
    '''struct-declaration : STRUCT ID '{' struct-body-declaration '}'
    '''
    fields, methods = split_fields_methods(p[4])
    p[0] = StructDeclaration(PACKAGE, p[2], fields, methods, [], position=getpos(p))

def p_struct_declaration_extern(p):
    '''struct-declaration : EXTERN STRUCT ID ';'
    '''
    p[0] = StructDeclaration(PACKAGE, p[3], [], [], [], is_extern=True, position=getpos(p))

def p_struct_declaration_extern_with_body(p):
    '''struct-declaration : EXTERN STRUCT ID '{' struct-body-declaration '}'
    '''
    fields, methods = split_fields_methods(p[5])
    p[0] = StructDeclaration(PACKAGE, p[3], fields, methods, [], is_extern=True, position=getpos(p))

def p_struct_template_declaration(p):
    '''struct-declaration : STRUCT ID template-declaration '{' struct-body-declaration '}'
    '''
    fields, methods = split_fields_methods(p[5])
    p[0] = StructDeclaration(PACKAGE, p[2], fields, methods, p[3], position=getpos(p))

def p_struct_body_declaration(p):
    "struct-body-declaration : struct-objects"
    p[0] = p[1]

def p_struct_fields(p):
    '''struct-objects : struct-objects struct-field
                    | struct-objects struct-method
                    | struct-field
                    | struct-method
                    |
    '''
    if len(p) == 3:
        p[0] = p[1]
        p[0].append(p[2])
    elif len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_struct_field(p):
    '''struct-field : type ID ';'
                    | ACCMOD type ID ';'
    '''
    if len(p) == 4:
        p[0] = ('public', p[1], p[2])
    else:
        p[0] = (p[1], p[2], p[3])

def p_struct_method(p):
    '''struct-method : function-declaration'''
    src: FunctionDeclaration = p[1]
    p[0] = (src.data.type.raw, src.data.name, [(t.raw, n) for t, n in src.arguments], src.data.template_types, src.body, src.data.is_safe, src.position)
    raise NotImplementedError


#####################################################
#               VARIABLE_DECLARATION                #
#####################################################

def p_variable_declaration(p):
    '''variable-declaration : variable-declaration-short
                            | variable-declaration-full
    '''
    p[0] = p[1]

def p_variable_declaration_expression_line(p):
    "variable-declaration-looks-like : ID TIMES ID '=' expression"
    t = RawType(Path([]), p[1], 1, [], src_pack=PACKAGE, position=getpos(p))
    t.gen_hash()
    p[0] = VariableCreationExpression(p[3], p[5], t, getpos(p))

def p_variable_declaration_short(p):
    "variable-declaration-short : type ID"
    if not isinstance(p[1], TypeData):
        p[0] = VariableCreationExpression(p[2], None, p[1], getpos(p))
    else:
        p[0] = VariableCreationExpression(p[2], None, p[1], getpos(p))


def p_variable_declaration_full(p):
    "variable-declaration-full : type ID '=' expression"
    if not isinstance(p[1], TypeData):
        p[0] = VariableCreationExpression(p[2], p[4], p[1], getpos(p))
    else:
        p[0] = VariableCreationExpression(p[2], p[4], p[1], getpos(p))


#####################################################
#           IF, ELSE, FOR, WHILE, UNSAFE            #
#####################################################

def p_while(p):
    "while : WHILE expression visibility-area"
    p[0] = WhileExpression(p[2], p[3], getpos(p))

def p_for(p):
    "for : FOR '(' variable-declaration ';' expression ';' expression-line ')' visibility-area"
    raise NotImplementedError

def p_if(p):
    """if : IF expression visibility-area
        | IF expression visibility-area ELSE visibility-area
        | IF expression visibility-area ELSE if
    """
    if len(p) == 4:
        p[0] = IfExpression(p[2], p[3], None, getpos(p))
    else:
        p[0] = IfExpression(p[2], p[3], p[5], getpos(p))

def p_if_look_like_1(p):
    """if : IF ID LS expression visibility-area
        | IF ID LS expression visibility-area ELSE visibility-area
        | IF ID LS expression visibility-area ELSE if
    """
    be = BinaryOperatorExpression(VariableExpression(p[2], getpos(p, 2, 2)), p[4], p[3], getpos(p, 2, 4))
    if len(p) == 6:
        p[0] = IfExpression(be, p[5], None, position=getpos(p))
    else:
        p[0] = IfExpression(be, p[7], None, position=getpos(p))

def p_if_look_like_2(p):
    """if : IF expression '.' ID LS expression visibility-area
        | IF expression '.' ID LS expression visibility-area ELSE visibility-area
        | IF expression '.' ID LS expression visibility-area ELSE if
    """
    be = BinaryOperatorExpression(GetterExpression(p[2], p[4], getpos(p, 2, 4)), p[6], p[5], getpos(p, 2, 6))
    if len(p) == 8:
        p[0] = IfExpression(be, p[7], None, position=getpos(p))
    else:
        p[0] = IfExpression(be, p[7], p[9], position=getpos(p))

def p_visibility_area(p):
    "visibility-area : '{' expression-lines '}'"
    p[0] = VisibilityAreaExpression(p[2], getpos(p))


def p_getter(p):
    "getter : expression '.' ID"
    p[0] = GetterExpression(p[1], p[3], getpos(p))


def p_function_invoke(p):
    """function-invoke : ID '(' expressions ')'
                | path '(' expressions ')'
    """
    path = Path([])
    name = p[1]
    if isinstance(p[1], Path):
        path = Path(p[1].nodes[:-1])
        name = p[1].nodes[-1]
    p[0] = FunctionInvokeExpression(path, name, p[3], [], getpos(p))

def p_method_invoke(p):
    "method-invoke : expression '.' ID '(' expressions ')'"
    p[0] = FunctionInvokeExpression(Path([]), p[3], [p[1]] + p[5], [], getpos(p))

def p_template_method_invoke(p):
    "method-invoke : expression '.' ID template-declaration '(' expressions ')'"
    p[0] = FunctionInvokeExpression(Path([]), p[3], [p[1]] + p[6], p[4], getpos(p))


def p_function_template_invoke(p):
    """function-invoke : ID template-declaration '(' expressions ')'
                | path template-declaration '(' expressions ')'
    """
    path = Path([])
    name = p[1]
    if isinstance(p[1], Path):
        path = Path(p[1].nodes[:-1])
        name = p[1].nodes[-1]
    p[0] = FunctionInvokeExpression(path, name, p[4], p[2], getpos(p))


def p_function_invoke_arguments(p):
    """expressions : expressions ',' expression
                    | expression
                    |
    """
    l = len(p)
    if l == 1:
        p[0] = []
    elif l == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])


def p_variable_set(p):
    """expression-set : left-side-expression '=' expression"""
    p[0] = ExpressionValueSetExpression(p[1], p[3], getpos(p))


def p_return_expression(p):
    '''return-expression : RETURN expression
                    | RETURN
    '''
    if len(p) == 3:
        p[0] = ReturnExpression(p[2], getpos(p))
    else:
        p[0] = ReturnExpression(None, getpos(p))


def p_struct_construct(p):
    """struct-construct : type '{' struct-construct-expressions '}'
    """
    p[0] = StructConstructorExpression(p[1], p[3], getpos(p))

def p_struct_construct_expressions(p):
    '''struct-construct-expressions : struct-construct-expressions ',' expression
                                    | expression
                                    |
    '''
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    elif len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_unsafe_area(p):
    "unsafe-area : UNSAFE visibility-area"
    p[0] = UnsafeExpression(p[2], getpos(p))



def p_primitive_expression(p):
    """primitive-expression : constant-expression
                            | variable-expression
    """
    p[0] = p[1]

def p_compound_left_side_expression(p):
    """compound-left-side-expression : unpack-expression
                                    | getter
                                    | function-invoke
                                    | method-invoke
                                    | bracket-expression
    """
    p[0] = p[1]

def p_primitive_left_side_expression(p):
    """primitive-left-side-expression : variable-expression"""
    p[0] = p[1]

def p_compound_expression(p):
    """compound-expression : binary-expression
                            | unary-expression
                            | cast-expression
                            | struct-construct
                            | unpack-expression
                            | pack-expression
                            | unsafe-expression
                            | sizeof-expression
                            | typeid-expression
                            | typestr-expression
                            | array-creation
                            | getter
                            | function-invoke
                            | method-invoke
                            | bracket-expression
                            | square-brackets-expression
    """
    p[0] = p[1]

def p_left_side_expression(p):
    """left-side-expression : primitive-left-side-expression
                            | compound-left-side-expression
    """
    p[0] = p[1]

def p_expression(p):
    """expression : primitive-expression
                | compound-expression
    """
    p[0] = p[1]

def p_unsafe_expression(p):
    "unsafe-expression : UNSAFE compound-expression"
    p[0] = UnsafeExpression(p[2], getpos(p))

def p_array_creation(p):
    "array-creation : '[' expressions ']'"
    p[0] = ArrayCreationExpression(p[2], getpos(p))

def p_square_brackets_expression_var(p):
    "square-brackets-expression : expression '[' expression ']' %prec SQUARE_BRACKETS"
    p[0] = BinaryOperatorExpression(p[1], p[3], '[]', getpos(p))


def p_sizeof_expression(p):
    "sizeof-expression : SIZEOF '(' type ')'"
    p[0] = SizeofExpression(p[3], getpos(p))

def p_typeid_expression(p):
    """typeid-expression : TYPEID '(' type ')'
                        | TYPEID '(' expression ')'
    """
    p[0] = TypeidExpression(p[3], getpos(p))

def p_typestr_expression(p):
    """typestr-expression : TYPESTR '(' type ')'
                        | TYPESTR '(' expression ')'
    """
    p[0] = TypestrExpression(p[3], getpos(p))

def p_unpack_expression(p):
    "unpack-expression : TIMES expression"
    p[0] = PointerUnpackExpression(p[2], getpos(p))

def p_pack_expression(p):
    """pack-expression : AND expression
    """
    p[0] = PointerGetExpression(p[2], getpos(p))

def p_expression_cast(p):
    """cast-expression : '(' type ')' expression %prec CAST
    """
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = CastExpression(p[2], p[4], getpos(p))

def p_looks_like_cast(p):
    "cast-expression : '(' variable-expression TIMES ')' expression"
    t = RawType(Path([]), p[2].name, 1, [], src_pack=PACKAGE, position=getpos(p))
    t.gen_hash()
    p[0] = CastExpression(t, p[5], getpos(p))


def p_expression_brackets(p):
    """bracket-expression : '(' compound-expression ')' %prec BRACKETS
    """
    p[0] = p[2]


def p_expression_binary_math(p):
    '''binary-expression : expression PLUS expression
                | expression MINUS expression
                | expression TIMES expression
                | variable-expression TIMES expression
                | expression DIVIDE expression
                | expression MOD expression
                | expression AND expression
                | expression OR expression
                | expression XOR expression
                | expression LSHIFT expression
                | expression RSHIFT expression
    '''
    p[0] = BinaryOperatorExpression(p[1], p[3], p[2], getpos(p))

def p_expression_binary_logic(p):
    '''binary-expression : expression LS expression
                | expression GR expression
                | expression LE expression
                | expression GE expression
                | expression EE expression
                | expression NE expression'''
    p[0] = BinaryOperatorExpression(p[1], p[3], p[2], getpos(p))


def p_expression_unary(p):
    '''unary-expression : MINUS expression %prec UMINUS
                | PLUS expression %prec UPLUS
                | '!' expression
    '''
    p[0] = UnaryOperatorExpression(p[2], p[1], getpos(p))


def p_equals_expression(p):
    '''equals-operation : left-side-expression PLUSEQ expression
                        | left-side-expression MINUSEQ expression
                        | left-side-expression TIMESEQ expression
                        | left-side-expression DIVIDEEQ expression
                        | left-side-expression MODEQ expression
                        | left-side-expression ANDEQ expression
                        | left-side-expression OREQ expression
                        | left-side-expression XOREQ expression
                        | left-side-expression LSHIFTEQ expression
                        | left-side-expression RSHIFTEQ expression
    '''
    p[0] = ExpressionValueSetExpression(p[1], BinaryOperatorExpression(p[1], p[3], p[2][:-1], getpos(p)), getpos(p))

def p_value_variable(p):
    '''variable-expression : ID
    '''
    p[0] = VariableExpression(p[1], getpos(p))


def p_constant_expression(p):
    '''constant-expression : INT
                        | FLOAT
                        | STR
                        | BOOL
                        | CHAR
    '''
    p[0] = Constant(p[1], getpos(p))

def p_type(p):
    """type : type-raw
            | CONST type-raw
    """
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]
        p[0].is_const = True
    p[0].gen_hash()

def p_type_raw(p):
    '''type-raw : type-raw TIMES
            | ID template-declaration
            | ID
            | path template-declaration
            | path
    '''

    if len(p) == 3 and (type(p[2]) == str and p[2] == '*'):
        p[0] = p[1]
        p[0].pointer_level += 1
    else:
        if isinstance(p[1], Path):
            path = Path(p[1].get_nodes()[:-1])
            name = p[1].get_nodes()[-1]
        else:
            path = Path([])
            name = p[1]

        if len(p) == 2:
            t = RawType(path, name, 0, [], src_pack=PACKAGE, position=getpos(p))
        else:
            t = RawType(path, name, 0, p[2], src_pack=PACKAGE, position=getpos(p))
        p[0] = t


def p_type_var(p):
    'type : VAR'
    t = NOTYPE_T.raw.copy()
    t.position = getpos(p)
    p[0] = t

def p_type_const_var(p):
    'type : CONST VAR'
    t = NOTYPE_T.raw.copy()
    t.is_const = True
    t.position = getpos(p)
    p[0] = t


def p_template_declaration(p):
    '''template-declaration : LS template-declaration-types GR
    '''
    p[0] = p[2]


def p_template_declaration_types(p):
    '''template-declaration-types : template-declaration-types ',' type
                    | type
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        arr = p[1]
        arr.append(p[3])
        p[0] = arr


def p_path(p):
    '''path : path-nodes
    '''
    p[0] = Path(p[1])


def p_path_nodes(p):
    '''path-nodes : path-nodes ':' ID
                | ID ':' ID
                | ':' ID
    '''
    if len(p) == 4:
        if isinstance(p[1], list):
            p[0] = p[1]
            p[0].append(p[3])
        else:
            p[0] = [p[1], p[3]]
    else:
        p[0] = [p[2]]


parser = yacc.yacc()


def parse(t: str, storage: GlobalStorage):
    global STORAGE, SOURCE
    SOURCE = t
    STORAGE = storage
    lexer.lexer.lineno = 0
    lexer.lexer.lexpos = 0
    parser.parse(t, lexer=lexer.lexer, tracking=True)#, debug=True)
    return PACKAGE
