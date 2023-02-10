from helpers2 import *

STORAGE: Optional[GlobalStorage] = None


def gen_struct_declaration(s: StructDeclaration) -> str:
    header = f"struct {s.data.name}[{','.join([str(t) for t in s.data.template_types])}] "
    body = []
    for t, n in s.fields:
        body.append(f'\t{str(t)} {n}')
    return header + "{\n" + ';\n'.join(body) + "\n};\n"


global_additive: str = ''
curr_line_additive: str = ''


def gen_expr(expr: Expression) -> str:
    global global_additive, curr_line_additive
    if isinstance(expr, FunctionInvokeExpression):
        if expr.templates:
            return f"{expr.name}[{','.join([str(t) for t in expr.templates])}]({','.join(gen_expr(e) for e in expr.arguments)})"
        else:
            return f"{expr.name}({','.join(gen_expr(e) for e in expr.arguments)})"
    elif isinstance(expr, BinaryOperatorExpression):
        return f"{expr.function.name}({gen_expr(expr.expr1)},{gen_expr(expr.expr2)})"
    elif isinstance(expr, UnaryOperatorExpression):
        return f"{expr.function.name}({gen_expr(expr.expr)})"
    elif isinstance(expr, VariableExpression):
        return expr.name
    elif isinstance(expr, VariableCreationExpression):
        if expr.expr:
            return f"{str(expr.type)} {expr.name} = {gen_expr(expr.expr)}"
        else:
            return f"{str(expr.data.type)} {expr.data.name}"
    elif isinstance(expr, ExpressionValueSetExpression):
        return f"{gen_expr(expr.to)} = {gen_expr(expr.expr)}"
    elif isinstance(expr, ReturnExpression):
        return f"return {gen_expr(expr.expr)}"
    elif isinstance(expr, Constant):
        return expr.value
    elif isinstance(expr, CastExpression):
        if expr.function:
            return f"{expr.function.name}({gen_expr(expr.expr)})"
        else:
            return f"({str(expr.cast_type)})({gen_expr(expr.expr)})"
    elif isinstance(expr, StructConstructorExpression):
        return f"({str(expr.type)}){{{','.join([gen_expr(e) for e in expr.exprs])}}}"
    elif isinstance(expr, GetterExpression):
        return f"{gen_expr(expr.expr)}.{expr.what}"
    elif isinstance(expr, VisibilityAreaExpression):
        return "{\n\t" + ';\n\t'.join([gen_expr(e) for e in expr.exprs]) + ";\n}"
    elif isinstance(expr, IfExpression):
        if not expr.else_body:
            return f"if {gen_expr(expr.expr)} {gen_expr(expr.if_body)}"
        else:
            return f"if {gen_expr(expr.expr)} {gen_expr(expr.if_body)}else {gen_expr(expr.else_body)}"
    elif isinstance(expr, WhileExpression):
        return f"while {gen_expr(expr.expr)} {gen_expr(expr.body)}"
    elif isinstance(expr, PointerUnpackExpression):
        return f"(*{gen_expr(expr.expr)})"
    elif isinstance(expr, PointerGetExpression):
        return f"&({gen_expr(expr.expr)})"
    elif isinstance(expr, UnsafeExpression):
        return f"unsafe {gen_expr(expr.expr)}"
    # elif isinstance(expr, TypeExpression):
    #    return gen_type_name(expr.type)
    elif isinstance(expr, SizeofExpression):
        return f"sizeof({str(expr.type)})"
    elif isinstance(expr, TypeidExpression):
        return f"{expr.type.str_hash()}U"
    elif isinstance(expr, TypestrExpression):
        n = str(expr.type)
        return f'{str(get_char_arr_t())} {{"{n}",{len(n) - 1}}}'
    elif isinstance(expr, ArrayCreationExpression):
        return f"[{','.join([gen_expr(e) for e in expr.exprs])}]"
    elif isinstance(expr, VariableDestroyExpression):
        return f"destroy {expr.name}"
    else:
        raise NotImplementedError(expr)


def gen_function_declaration(f: FunctionDeclaration) -> str:
    global curr_line_additive
    templates = f.data.template_types
    if isinstance(f, AppliedFunctionDeclarationContainer):
        templates = f.data.applied_templates

    header = f"{str(f.data.type)} {f.data.name}[{','.join([str(t) for t in templates])}]({','.join([f'{str(t)} {n}' for t, n in f.arguments])}) "
    body: List[str] = []
    for expr in f.body.expressions:
        gen = gen_expr(expr)
        if curr_line_additive:
            body.append(curr_line_additive)
            curr_line_additive = ''
        body.append(gen)
    return header + "{\n\t" + ';\n\t'.join(body) + ";\n};\n"


def gen_fatlang_code(storage: GlobalStorage):
    global STORAGE, global_additive
    global_additive = ''
    STORAGE = storage

    _generated_structs: List[Union[StructData, AppliedStructData]] = []

    struct_definitions: List[str] = []
    function_definitions: List[str] = []
    struct_declarations: List[str] = []
    function_declarations: List[str] = []

    # with generation order
    for s in storage.struct_declarations:
        if not s.is_extern():
            if not s.is_template():
                if s.data not in _generated_structs:
                    for t, _ in s.fields:
                        # struct A { &A a; }
                        if t.data != s.data and t.data not in _generated_structs and t.data not in BUILD_IN_PACK.struct_datas:
                            struct_declarations.append(gen_struct_declaration(s))
                            _generated_structs.append(t.data)
                    struct_declarations.append(gen_struct_declaration(s))
                    _generated_structs.append(s.data)
            else:
                for a in storage.applied_struct_declarations[s]:
                    if a.data not in _generated_structs:
                        for t, _ in a.fields:
                            if t.data != a.data and t.data not in _generated_structs and t.data not in BUILD_IN_PACK.struct_datas:
                                decl = STORAGE.get_declaration_by_data(t.data).apply_template(t.templates)
                                struct_declarations.append(gen_struct_declaration(decl))
                                _generated_structs.append(t.data)
                        struct_declarations.append(gen_struct_declaration(a))
                        _generated_structs.append(a.data)

    for f in storage.function_declarations:
        if not f.is_extern():
            if not f.is_template():
                function_declarations.append(gen_function_declaration(f))
            else:
                for a in storage.applied_function_declarations[f]:
                    function_declarations.append(gen_function_declaration(a))

    return ''.join(struct_definitions) + ''.join(struct_declarations) + global_additive + ''.join(
        function_definitions) + ''.join(function_declarations)
