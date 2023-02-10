from helpers2 import *

STORAGE: Optional[GlobalStorage] = None


def gen_func_name(f: Union[FunctionData, FunctionDeclaration]) -> str:
    if isinstance(f, FunctionDeclaration):
        if f.is_extern():
            return f.data.name
        else:
            return f"{f.data.name}_H{f.data.str_hash()}"
    elif isinstance(f, FunctionData):
        fd = STORAGE.get_declaration_by_data(f)
        if not fd.is_extern():
            return f"{f.name}_H{f.str_hash()}"
        else:
            return f.name
    else:
        raise ValueError(f)


def gen_type_name(t: [TypeData, StructData]) -> str:
    if isinstance(t, TypeData):
        return f"{'const ' if t.is_constant() else ''}{gen_type_name(t.data)}{'*' * t.pointer_level}"
    elif isinstance(t, StructData):
        sd = STORAGE.get_declaration_by_data(t)
        if sd:
            if not sd.is_extern():
                return f"{t.name}_H{t.str_hash()}"
            else:
                return f"struct {t.name}"
        else:
            return f"{t.name}_H{t.str_hash()}"
    else:
        raise ValueError(t)


def gen_function_definition(f: FunctionDeclaration) -> str:
    return f"{gen_type_name(f.data.type)} {gen_func_name(f)}({','.join([gen_type_name(t) + ' ' + n for t, n in f.arguments])});\n"


def gen_struct_definition(s: StructDeclaration) -> str:
    n = gen_type_name(s.data)
    sd = STORAGE.get_declaration_by_data(s.data)
    if not sd.is_extern():
        return f"struct {n};\ntypedef struct {n} {n};\n"
    else:
        return f"{n};\n"


def gen_struct_declaration(s: StructDeclaration) -> str:
    header = f"struct {gen_type_name(s.data)}"
    body = []
    for _, t, n in s.fields:
        body.append(f'{gen_type_name(t)} {n}')
    return header + "{" + ';'.join(body) + ";};\n"


global_additive: str = ''
curr_line_additive: str = ''

def gen_expr(expr: Expression) -> str:
    global global_additive, curr_line_additive
    if isinstance(expr, FunctionInvokeExpression):
        return f"{gen_func_name(expr.function)}({','.join(gen_expr(e) for e in expr.arguments)})"
    elif isinstance(expr, BinaryOperatorExpression):
        return f"{gen_func_name(expr.function)}({gen_expr(expr.expr1)},{gen_expr(expr.expr2)})"
    elif isinstance(expr, UnaryOperatorExpression):
        return f"{gen_func_name(expr.function)}({gen_expr(expr.expr)})"
    elif isinstance(expr, VariableExpression):
        return expr.name
    elif isinstance(expr, VariableCreationExpression):
        if expr.expr:
            return f"{gen_type_name(expr.data.type)} {expr.data.name}={gen_expr(expr.expr)}"
        else:
            return f"{gen_type_name(expr.data.type)} {expr.data.name}"
    elif isinstance(expr, ExpressionValueSetExpression):
        return f"{gen_expr(expr.to)}={gen_expr(expr.expr)}"
    elif isinstance(expr, ReturnExpression):
        return f"return {gen_expr(expr.expr)}"
    elif isinstance(expr, Constant):
        if expr.type != get_char_arr_t():
            t = expr.type
            if t == I32_T:
                return f"{expr.value}"
            elif t == UI32_T:
                return f"{expr.value}U"
            elif t == I64_T:
                return f"{expr.value}LL"
            elif t == UI64_T:
                return f"{expr.value}ULL"
            elif t == USIZE_T:
                # TODO: dynamic size
                return f"{expr.value}"
            else:
                return expr.value
        else:
            return f"({gen_type_name(get_char_arr_t())}){{{str(expr.value)},{Constant.calc_str_len(expr.value[1:-1])}}}"
    elif isinstance(expr, CastExpression):
        if expr.function:
            return f"{gen_func_name(expr.function)}({gen_expr(expr.expr)})"
        else:
            return f"({gen_type_name(expr.cast_type)})({gen_expr(expr.expr)})"
    elif isinstance(expr, StructConstructorExpression):
        return f"({gen_type_name(expr.type)}){{{','.join([gen_expr(e) for e in expr.exprs])}}}"
    elif isinstance(expr, GetterExpression):
        return f"{gen_expr(expr.expr)}.{expr.what}"
    elif isinstance(expr, VisibilityAreaExpression):
        return "{" + ';'.join([gen_expr(e) for e in expr.exprs]) + ";}"
    elif isinstance(expr, IfExpression):
        if not expr.else_body:
            return f"if({gen_expr(expr.expr)}){{{gen_expr(expr.if_body)}}}"
        else:
            return f"if({gen_expr(expr.expr)}){{{gen_expr(expr.if_body)}}}else{{{gen_expr(expr.else_body)}}}"
    elif isinstance(expr, WhileExpression):
        return f"while({gen_expr(expr.expr)}){{{gen_expr(expr.body)}}}"
    elif isinstance(expr, PointerUnpackExpression):
        return f"(*{gen_expr(expr.expr)})"
    elif isinstance(expr, PointerGetExpression):
        return f"&({gen_expr(expr.expr)})"
    elif isinstance(expr, UnsafeExpression):
        return gen_expr(expr.expr)
    # elif isinstance(expr, TypeExpression):
    #    return gen_type_name(expr.type)
    elif isinstance(expr, SizeofExpression):
        return f"sizeof({gen_type_name(expr.type)})"
    elif isinstance(expr, TypeidExpression):
        return f"{expr.type.str_hash()}U"
    elif isinstance(expr, TypestrExpression):
        n = str(expr.type)
        return f'({gen_type_name(get_char_arr_t())}){{"{n}",{len(n) - 1}}}'
    elif isinstance(expr, ArrayCreationExpression):
        n = f"A{expr.function_body.function.data.package.path.str_hash()}_{''.join([str(i) for i in expr.position])}"
        global_additive += f"const {gen_type_name(expr.exprs[0].get_out_type())} {n}[]={{{','.join([gen_expr(e) for e in expr.exprs])}}};\n"
        return f"({gen_type_name(expr.get_out_type())}){{ {n}, {len(expr.exprs)} }}"
    elif isinstance(expr, VariableDestroyExpression):
        if expr.function:
            return f'{gen_func_name(expr.function)}(&{expr.name})'
        else:
            return ''
    elif isinstance(expr, CopyExpression):
        if expr.function:
            return f'{gen_func_name(expr.function)}(&{gen_expr(expr.expr)})'
        else:
            return gen_expr(expr.expr)
    else:
        raise NotImplementedError(expr)


def gen_function_declaration(f: FunctionDeclaration) -> str:
    global curr_line_additive
    header = gen_function_definition(f)[:-2]
    body: List[str] = []
    for expr in f.body.expressions:
        gen = gen_expr(expr)
        if curr_line_additive:
            body.append(curr_line_additive)
            curr_line_additive = ''
        body.append(gen)
    return header + "{" + ';'.join(body) + ";};\n"


def gen_c_code(storage: GlobalStorage):
    global STORAGE, global_additive
    global_additive = ''
    STORAGE = storage

    _generated_structs: List[Union[StructData, AppliedStructData]] = []

    struct_definitions: List[str] = []
    function_definitions: List[str] = []
    struct_declarations: List[str] = []
    function_declarations: List[str] = []
    for s in storage.struct_declarations:
        if not s.is_extern():
            if not s.is_template():
                struct_definitions.append(gen_struct_definition(s))
            else:
                for a in storage.applied_struct_declarations[s]:
                    struct_definitions.append(gen_struct_definition(a))
    for f in storage.function_declarations:
        if not f.is_extern():
            if not f.is_template():
                function_definitions.append(gen_function_definition(f))
            else:
                for a in storage.applied_function_declarations[f]:
                    function_definitions.append(gen_function_definition(a))

    # with generation order
    for s in storage.struct_declarations:
        if not s.is_extern():
            if not s.is_template():
                if s.data not in _generated_structs:
                    for _, t, _ in s.fields:
                        # struct A { A* a; }
                        if t.data != s.data and t.data not in _generated_structs and t.data not in BUILD_IN_PACK.struct_datas:
                            decl = STORAGE.get_declaration_by_data(t.data)
                            struct_declarations.append(gen_struct_declaration(decl))
                            _generated_structs.append(t.data)
                    struct_declarations.append(gen_struct_declaration(s))
                    _generated_structs.append(s.data)
            else:
                for a in storage.applied_struct_declarations[s]:
                    if a.data not in _generated_structs:
                        for _, t, _ in a.fields:
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

    main_f: Optional[FunctionDeclaration] = None
    for i in storage.function_declarations:
        if i.data.name == "main":
            main_f = i
            break
    header = "#include \"all.h\"\n"
    main_f_str = f"\nint main(){{return {gen_func_name(main_f.data)}();}}"

    return header + ''.join(struct_definitions) + ''.join(struct_declarations) + global_additive + ''.join(
        function_definitions) + ''.join(function_declarations) + main_f_str
