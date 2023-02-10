from typing import List, Union, Tuple, Optional, Any, Dict
import traceback
import re
from fuzzywuzzy import fuzz
import settings as st

settings = st.SettingsSwitch()

# TODO: add numbers as template parameters

def hash_faq6(s):
    hash = 0

    if isinstance(s, str):
        for i in s:
            hash += ord(i)
            hash += (hash << 10) & 0xFFFFFFFF
            hash ^= hash >> 6
    elif isinstance(s, list):
        for el in s:
            for i in el:
                hash += ord(i)
                hash += (hash << 10) & 0xFFFFFFFF
                hash ^= hash >> 6
    else:
        raise ValueError

    hash += (hash << 3) & 0xFFFFFFFF
    hash ^= hash >> 11
    hash += (hash << 15) & 0xFFFFFFFF
    return hash & 0xFFFFFFFF


def pos_hash(pos: Tuple[int, int, int, int]):
    return hash_faq6([str(i) for i in pos])


def log_error(e: 'AnalyzerException', package: 'Package',
              object: Optional[Union['FunctionDeclaration', 'StructDeclaration']] = None):
    print("AnalyzerException at")
    lines = package.get_source_fragment(e.pos()[1], e.pos()[3], e.pos()[0], e.pos()[2])
    fragment = f'\t{e.pos()[0] - 1}--> ' + lines[0]
    for i, l in enumerate(lines[1:]):
        fragment += f'\n\t{e.pos()[0] + i}--> ' + l
    if object is not None:
        print(f"\t{e.str_pos()} -> {str(object)} -> {e.what()}")
    else:
        print(f"\t{e.str_pos()} -> {str(package.path)} -> {e.what()}")
    print(fragment)


def gen_variable_name(pos):
    return f'GEN{pos[0]}{pos[1]}{pos[2]}{pos[3]}'


def packages_by_path(path: 'Path', trace_from: 'Package') -> List['Package']:
    packs = set()

    def _get_package(path: Path):
        if trace_from.path == path:
            return trace_from
        for p in trace_from.other_packages:
            if p.path == path:
                return p
        return None

    p = _get_package(path)
    if p:
        packs.add(p)
    p = _get_package(trace_from.path + path)
    if p:
        packs.add(p)
    for i in trace_from.imports:
        p = _get_package(i + path)
        if p:
            packs.add(p)
    return list(packs)


def functions_by_path(path: 'Path', current_package: 'Package') -> List['FunctionData']:
    packs = packages_by_path(path, current_package)
    functions = []
    for p in packs:
        functions += p.function_datas
    return functions


def structs_by_path(path: 'Path', current_package: 'Package') -> List['StructData']:
    packs = packages_by_path(path, current_package)

    structs = []
    for p in packs:
        structs += p.struct_datas
    return structs


MIN_SAME_RATIO = 67


def find_same_functions(name: str, current_package: 'Package') -> List['FunctionData']:
    same_list: List['FunctionData'] = []
    functions = functions_by_path(Path([]), current_package)
    for f in functions:
        if fuzz.ratio(name, f.name) >= MIN_SAME_RATIO:
            same_list.append(f)

    return same_list


def find_same_structs(name: str, package: 'Package') -> List['StructData']:
    same_list: List['StructData'] = []
    structs = structs_by_path(Path([]), package)
    for s in structs:
        if fuzz.ratio(name, s.name) >= MIN_SAME_RATIO:
            same_list.append(s)
    return same_list


def find_function(package: 'Package', path: 'Path', name: str, templates: List['TypeData'],
                  arg_types: List['TypeData'], allow_auto_pack=settings.get_current().allow_auto_pack):
    # TODO: fix cast
    fi = FunctionImage(name, arg_types, templates)

    functions = functions_by_path(path, package)

    if allow_auto_pack:
        functions_1 = []
        for f in functions:
            if f.name == fi.name and len(f.arg_types) == len(fi.arg_types):

                ts: List[TypeData] = [i.copy() for i in arg_types]
                for t, ft in zip(ts, f.arg_types):
                    if t.pointer_level + 1 == ft.pointer_level if ft.pointer_level is not None else ft.raw.pointer_level:
                        t.pointer_level += 1
                        t.raw.pointer_level += 1
                        t.gen_hash()

                new_fi = FunctionImage(name, ts, templates)
                if f == new_fi:
                    functions_1.append(f)
        return functions_1
    else:
        ret = []
        for f in functions:
            if f == fi:
                ret.append(f)
        return ret


class VisibilityStack:
    def __init__(self):
        self.levels: List[List[VariableData]] = []

    def push_level(self):
        self.levels.append([])

    def pop_level(self):
        return self.levels.pop(-1)

    def take_level(self):
        return self.levels[-1][:]

    def register_variable(self, v: 'VariableData'):
        if v not in self.levels[-1]:
            self.levels[-1].append(v)
        else:
            raise KeyError

    def find_variable(self, name) -> Optional['VariableData']:
        for level in reversed(self.levels):
            for v in level:
                if v.name == name:
                    return v
        return None

    def destroy_variable(self, name):
        for v in self.levels[-1]:
            if v.name == name:
                self.levels[-1].remove(v)
                return
        raise ValueError

    def clear(self):
        self.levels.clear()


class PrintColor:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class AnalyzerException(Exception):
    def __init__(self, text: str = None, position: Optional[Tuple[int, int, int, int]] = None, *args):
        super().__init__(text, position, *args)

    def what(self) -> str:
        # print(traceback.format_exc())
        return self.args[0] if self.args[0] is not None else '[no text]'

    def str_pos(self):
        return f"line {self.args[1][0] + 1}:{self.args[1][1]}"

    def pos(self):
        return self.args[1]


class Path:
    def __init__(self, nodes: List[str]):
        self.nodes = nodes.copy()

    def get_nodes(self) -> List[str]:
        return self.nodes[:]

    def __hash__(self):
        return hash_faq6(["path"] + self.nodes)

    def str_hash(self):
        return str(hash(self))

    def __add__(self, other):
        if isinstance(other, Path):
            return Path(self.nodes + other.nodes)
        else:
            raise ValueError

    def __str__(self):
        return f'{":".join(self.nodes)}'

    def __eq__(self, other):
        if isinstance(other, Path):
            return hash(self) == hash(other)
        else:
            raise ValueError(other)


class BadTemplateException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class RawType:
    def __init__(self, path: Path, name: str, pointer_level: int, template_types: List['RawType'],
                 src_pack: Optional['Package'] = None, position: Optional[Tuple[int, int, int, int]] = None, is_const: bool = False):
        self.name = name
        self.pointer_level = pointer_level
        self.templates: List['RawType'] = template_types
        self.path = path
        self.hash = 0
        self.gen_hash()
        
        self.is_const = is_const

        self.position = position
        self.src_pack = src_pack

    def gen_hash(self):
        self.hash = hash_faq6(["rawtype", self.path.str_hash(), self.name] + [i.str_hash() for i in
                                                                              self.templates])

    def is_constant(self):
        return self.is_const

    def has_any_template(self, templates: List['RawType']):
        return any([self.has_template(t) for t in templates])

    def has_template(self, template: 'RawType'):
        t = self.copy()
        t.templates = []
        t.gen_hash()
        if t == template:
            return True
        for t in self.templates:
            if t == template:
                return True
            if t.has_template(template):
                return True
        return False

    def is_pointer(self):
        return self.pointer_level != 0

    def str_hash(self):
        return str(self.hash)

    def __eq__(self, other):
        if isinstance(other, RawType):
            return self.hash == other.hash
        else:
            raise ValueError(type(other))

    def is_template(self):
        return len(self.templates) > 0

    def __str__(self):
        if self.is_template():
            return f"{self.path}:{self.name}<{', '.join([str(i) for i in self.templates])}>{'*' * self.pointer_level}"
        else:
            return f"{self.path}:{self.name}{'*' * self.pointer_level}"

    def __hash__(self):
        return self.hash

    def copy(self):
        return RawType(self.path, self.name, self.pointer_level, self.templates, self.src_pack, self.position)


class FunctionImage:
    def __init__(self, name: str, arg_types: List[RawType], templates: List['TypeData']):
        self.name = name
        self.arg_types = arg_types
        self.templates = templates


class StructImage:
    def __init__(self, name: str, templates: List[RawType]):
        self.name = name
        self.templates = templates


class Data:
    def update_types(self):
        raise NotImplementedError


class TypeData(Data):

    def __init__(self, data: Optional[Union['StructData']], trace_package: Optional['Package'],
                 raw_type: Optional[RawType], template_types: Optional[List['TypeData']],
                 pointer_level: Optional[int], is_const: bool):
        self.data = data
        self.templates = template_types
        self.raw = raw_type
        self.trace_package = trace_package
        self.pointer_level = pointer_level
        self.hash = 0
        self.is_mut = False
        self.is_const = is_const

        if not self.is_raw():
            self.raw = RawType(Path([]), self.data.name, self.pointer_level,
                               [i.raw for i in self.templates], self.data.package)

        self.gen_hash()

    def is_constant(self):
        return self.is_const
    
    def is_mutable(self):
        return not self.is_const and self.is_mut

    def set_mutable(self):
        self.is_mut = True

    def set_immutable(self):
        self.is_mut = False

    def is_pointer(self):
        return self.pointer_level != 0

    def gen_hash(self):
        if not self.is_raw():
            self.hash = hash_faq6(["type", self.data.str_hash(), str(self.pointer_level)])
        else:
            self.hash = self.raw.hash

    def str_hash(self):
        return str(self.hash)

    @staticmethod
    def new_raw(src_package: 'Package', raw_type: 'RawType'):
        if not isinstance(raw_type, RawType):
            raise ValueError(str(raw_type), type(raw_type))
        return TypeData(None, src_package, raw_type, None, None, raw_type.is_const)

    @staticmethod
    def new_data(data: Union['StructData'], pointer_level: int, template_types: List['TypeData'], is_const: bool):
        if not isinstance(data, StructData):
            raise StateException(data)
        return TypeData(data, None, None, template_types, pointer_level, is_const)

    @staticmethod
    def new_raw_templates(raw_type: RawType, templates: Dict[RawType, 'TypeData']) -> 'TypeData':
        nt = []

        for t in raw_type.templates:
            nt.append(TypeData.new_raw_templates(t, templates))

        raw_type = raw_type.copy()
        raw_type.gen_hash()

        if raw_type in templates:
            td = templates[raw_type].copy()

            td.raw.pointer_level += raw_type.pointer_level
            td.pointer_level = td.raw.pointer_level

            if td.raw.templates and nt:
                raise StateException

            td.raw.templates = td.raw.templates if td.raw.templates else [t.raw for t in nt]
            td.templates = td.templates if td.templates else nt
            td.gen_hash()
        else:
            raw_type.templates = [t.raw for t in nt]
            td = TypeData(None, raw_type.src_pack, raw_type, nt, None, raw_type.is_const)

        return td

    def is_raw(self) -> bool:
        return self.data is None or self.templates is None or self.pointer_level is None

    def make_not_raw(self):
        if self.is_raw():
            self.pointer_level = self.raw.pointer_level
            structs = structs_by_path(self.raw.path, self.trace_package)
            si = StructImage(self.raw.name, self.raw.templates)

            c = structs.count(si)
            if c == 0:
                same = find_same_structs(self.raw.name, self.raw.src_pack)
                if same:
                    text = f"type {str(self.raw)} isn't defined. Do you mean: {', '.join([str(i) for i in same])}?"
                else:
                    text = f"type {str(self.raw)} isn't defined"
                raise AnalyzerException(text, self.raw.position)
            if c > 1:
                # TODO: fix text
                raise AnalyzerException(f"lot of structs for {str(self.raw)}", self.raw.position)

            i = structs.index(si)
            self.data = structs[i]

            if not self.templates:
                templates = []
                for t in self.raw.templates:
                    td = TypeData.new_raw(self.data.package, t)
                    td.make_not_raw()
                    templates.append(td)
                self.templates = templates

            if self.data.is_template():
                self.data = self.data.apply_template(self.templates)
                try:
                    self.data.package.register(self.data)
                except KeyError:
                    pass

            self.gen_hash()

    def is_valid(self) -> bool:
        if self.is_raw():
            self.make_not_raw()
        if not settings.get_current().allow_pointer_of_pointer:
            if self.pointer_level > 1:
                raise AnalyzerException(f"pointer of pointer not allowed", self.raw.position)
        return True

    def update_types(self):
        self.is_valid()

    def __eq__(self, other):
        if isinstance(other, TypeData):
            if other.is_const and other.pointer_level != 0 and not self.is_const:
                return False
            return self.hash == other.hash
        elif isinstance(other, RawType):
            return self.raw == other
        else:
            raise ValueError(other)

    def __str__(self):
        if not self.is_raw():
            if self.data.is_template() or isinstance(self.data, AppliedStructData):
                return f"{'const ' if self.is_const else ''}{self.data.package.path}:{self.data.name}<{', '.join([str(i) for i in self.templates])}>{'*' * self.pointer_level}"
            else:
                return f"{'const ' if self.is_const else ''}{self.data.package.path}:{self.data.name}{'*' * self.pointer_level}"
        else:
            return str(self.raw)

    def copy(self):
        return TypeData(self.data, self.trace_package, self.raw.copy(), self.templates, self.pointer_level, self.is_const)


class FunctionData(Data):
    def __init__(self, package: 'Package', type_: Union[TypeData, RawType], name: str,
                 arg_types: List[Union[RawType, TypeData]],
                 template_types: List[RawType], is_safe: bool = True):
        self.type: Union[RawType, TypeData] = type_
        self.is_safe = is_safe

        self.name = name
        self.arg_types: List[Union[RawType, TypeData]] = arg_types

        self.template_types = template_types
        self.package = package
        self.hash = 0
        self.gen_hash()

    def gen_hash(self):
        self.hash = self.hash = hash_faq6(
            ["function", self.package.path.str_hash(), self.name, str(len(self.template_types))] +
            [i.str_hash() for i in self.arg_types] +
            [str(i.pointer_level if i.pointer_level is not None else i.raw.pointer_level) for i in self.arg_types])

    def __hash__(self):
        return self.hash

    def str_hash(self):
        return str(self.hash)

    def update_types(self):
        self.type.update_types()
        for i, t in enumerate(self.arg_types):
            if isinstance(t, TypeData):
                t.update_types()

    def apply_template(self, templates: List[TypeData]) -> 'AppliedFunctionData':
        if len(templates) == len(self.template_types):
            templates_dict = {}
            for i, j in zip(self.template_types, templates):
                templates_dict[i] = j
            if isinstance(self.type, RawType):
                new_type = TypeData.new_raw_templates(self.type, templates_dict)
            else:
                new_type = self.type
            new_arg_types = []

            for i, t in enumerate(self.arg_types):
                if isinstance(t, RawType):
                    t = TypeData.new_raw_templates(t, templates_dict)
                    new_arg_types.append(t)
                else:
                    new_arg_types.append(t)

            f = AppliedFunctionData(self.package, new_type, self.name, new_arg_types, templates, self)
            f.update_types()
            f.gen_hash()
            return f
        else:
            raise BadTemplateException

    def try_generate_template(self, arg_types: List[TypeData]) -> List[TypeData]:
        if len(self.arg_types) == len(arg_types):
            templates: Dict[RawType, TypeData] = {}

            def recursive(t: Union[TypeData, RawType], o: TypeData):
                if isinstance(t, RawType) and t in self.template_types:
                    if t not in templates:
                        if t.pointer_level == 0:
                            templates[t] = o
                        else:
                            c = o.copy()
                            delta = t.pointer_level
                            if c.pointer_level - delta < 0:
                                raise BadTemplateException
                            else:
                                c.pointer_level -= delta
                                c.raw.pointer_level -= delta
                            templates[t] = c
                    else:
                        if templates[t] != o:
                            raise BadTemplateException
                else:
                    tc = t.raw.copy() if isinstance(t, TypeData) else t.copy()
                    tc.templates = []
                    tc.gen_hash()

                    oc = o.raw.copy()
                    oc.templates = []
                    oc.path = Path([])  # <- костыль
                    oc.gen_hash()
                    # TODO: fix if pathes are different in raw but type the same returns false
                    if tc != oc:
                        raise BadTemplateException
                    if t.templates:
                        for i, j in zip(t.templates, o.templates):
                            recursive(i, j)

            for a, other_a in zip(self.arg_types, arg_types):
                recursive(a, other_a)

            return list(templates.values())
        else:
            raise ValueError

    def __eq__(self, other):
        if isinstance(other, FunctionData):
            return self.hash == other.hash
        elif isinstance(other, FunctionImage):
            if self.name == other.name:
                if len(self.template_types) == len(other.templates):
                    if self.is_template():
                        try:
                            f = self.apply_template(other.templates)
                        except BadTemplateException:
                            return False
                    else:
                        f = self
                    return f.arg_types == other.arg_types
                elif len(other.templates) == 0:  # if implicit templates
                    try:
                        self.try_generate_template(other.arg_types)
                        return True
                    except BadTemplateException:
                        return False
                    except ValueError:
                        return False
                else:
                    return False
            else:
                return False
        else:
            raise ValueError

    def is_template(self):
        return len(self.template_types) > 0

    def __str__(self):
        if self.is_template():
            return f"{str(self.package.path)}:{self.name}" \
                   f"<{','.join([str(i) for i in self.template_types])}>" \
                   f"({','.join([str(i) for i in self.arg_types])})"
        else:
            return f"{str(self.package.path)}:{self.name}" \
                   f"({','.join([str(i) for i in self.arg_types])})"


class AppliedFunctionData(FunctionData):
    def __init__(self, package: 'Package', type: TypeData, name: str, arg_types: List[TypeData],
                 applied_template_types: List[TypeData], src_func: FunctionData):
        self.applied_templates = applied_template_types
        self.src_function = src_func
        super().__init__(package, type, name, arg_types, [], src_func.is_safe)

    def gen_hash(self):
        self.hash = self.hash = hash_faq6(
            ["templated-function", self.package.path.str_hash(), self.name] +
            [i.str_hash() for i in self.arg_types] + [i.str_hash() for i in self.applied_templates] +
            [str(i.pointer_level if i.pointer_level is not None else i.raw.pointer_level) for i in self.arg_types])

    def __eq__(self, other):
        if isinstance(other, AppliedFunctionData):
            return self.src_function == other.src_function and self.applied_templates == other.applied_templates
        elif isinstance(other, FunctionData):
            return self.src_function == other
        else:
            raise ValueError


class StructData(Data):
    def __init__(self, package: 'Package', typename: str, template_types: List[RawType], is_extern: bool = False):
        self.package = package
        self.name = typename
        self.template_types = template_types

        # TODO: add template to hash and to __eq__?
        self.hash = 0
        self.gen_hash()

    def gen_hash(self):
        self.hash = hash_faq6(["struct", self.package.path.str_hash(), self.name])

    def __hash__(self):
        return self.hash

    def str_hash(self):
        return str(self.hash)

    def __str__(self):
        if self.is_template():
            return f"{self.package.path}:{self.name}[{','.join([str(i) for i in self.template_types])}]"
        else:
            return f"{self.package.path}:{self.name}"

    def __eq__(self, other):
        if isinstance(other, StructData):
            return self.hash == other.hash
        elif isinstance(other, StructImage):
            return self.name == other.name and len(self.template_types) == len(other.templates)
        else:
            raise ValueError(other)

    def is_template(self):
        return len(self.template_types) > 0

    def apply_template(self, templates: List[TypeData]) -> 'AppliedStructData':
        return AppliedStructData(self.package, self.name, self, templates)

    def update_types(self):
        pass


class AppliedStructData(StructData):
    def __init__(self, package: 'Package', typename: str, src_sd: StructData, applied_templates: List[TypeData]):
        self.src_sd = src_sd
        self.applied_templates = applied_templates
        super().__init__(package, typename, [a.raw for a in applied_templates])

    def gen_hash(self):
        self.hash = hash_faq6(
            ["applied-struct", self.src_sd.str_hash()] + [t.str_hash() for t in self.applied_templates])

    def __eq__(self, other):
        if isinstance(other, AppliedStructData):
            return self.src_sd == other.src_sd and self.applied_templates == other.applied_templates
        elif isinstance(other, StructData):
            return self.src_sd == other
        else:
            raise ValueError(other)

    def __str__(self):
        return f"{self.src_sd.package.path}:{self.src_sd.name}[{','.join([f'{str(t)}={str(a)}' for t, a in zip(self.src_sd.template_types, self.applied_templates)])}]"


class VariableData(Data):
    def __init__(self, type: TypeData, name: str):
        self.name = name
        self.type = type

        self.hash = hash_faq6(["variable", name])

    def __hash__(self):
        return self.hash

    def str_hash(self):
        return str(self.hash)

    def __eq__(self, other):
        if isinstance(other, VariableData):
            return self.name == other.name
        else:
            raise ValueError(other)

    def update_types(self):
        self.type.update_types()


class GlobalStorage:
    def __init__(self):
        self.function_declarations: List[FunctionDeclaration] = []
        self.struct_declarations: List[StructDeclaration] = []

        self.applied_function_declarations: Dict[FunctionDeclaration, List[AppliedFunctionDeclarationContainer]] = {}
        self.applied_struct_declarations: Dict[StructDeclaration, List[AppliedStructDeclaration]] = {}

        self.all_packages: List[Package] = []

        self._late_create_casts: List[Tuple['Package', RawType, Tuple[RawType, str], 'FunctionBody']] = []

    def add_package(self, p: 'Package'):
        for i in self.all_packages:
            i.other_packages.append(p)
        p.other_packages = self.all_packages[:]
        self.all_packages.append(p)
        p.storage = self

    def get_declaration_by_data(self, data: Data) -> Union['FunctionDeclaration', 'StructDeclaration']:
        if isinstance(data, StructData):
            for i in self.struct_declarations:
                if i.data == data:
                    return i
        elif isinstance(data, FunctionData):
            for i in self.function_declarations:
                if i.data == data:
                    return i
        else:
            raise ValueError(data)

    def register(self, v: 'Declaration'):
        if isinstance(v, AppliedStructDeclaration):
            if v not in self.applied_struct_declarations[v.src_sd]:
                self.applied_struct_declarations[v.src_sd].append(v)
            else:
                raise KeyError
        elif isinstance(v, StructDeclaration):
            if v not in self.struct_declarations:
                self.struct_declarations.append(v)
                if v.is_template():
                    self.applied_struct_declarations[v] = []
                v.data.package.register(v.data)
            else:
                raise KeyError
        elif isinstance(v, AppliedFunctionDeclarationContainer):
            if v not in self.applied_function_declarations[v.src_fd]:
                self.applied_function_declarations[v.src_fd].append(v)
            else:
                raise KeyError
        elif isinstance(v, FunctionDeclaration):
            if v not in self.function_declarations:
                self.function_declarations.append(v)
                if v.is_template():
                    self.applied_function_declarations[v] = []
                v.data.package.register(v.data)
            else:
                raise KeyError
        else:
            raise ValueError

    # TODO: make normal
    def _register_cast(self, d: Tuple['Package', RawType, Tuple[RawType, str], 'FunctionBody']):
        self._late_create_casts.append(d)

    def _get_created_applied_functions(self) -> List['AppliedFunctionDeclarationContainer']:
        decls = []
        for package in self.all_packages:
            for template in package.applied_function_datas:
                declaration = self.get_declaration_by_data(template)
                for applied in package.applied_function_datas[template]:
                    found = False
                    for t in self.applied_function_declarations[declaration]:
                        if applied == t.data:
                            found = True
                            break
                    if not found:
                        a = declaration.apply_template(applied.applied_templates)
                        decls.append(a)
                        self.register(a)
        return decls

    def _get_created_applied_structs(self) -> List['AppliedStructDeclaration']:
        decls = []
        for package in self.all_packages:
            for template in package.applied_struct_datas:
                decl = self.get_declaration_by_data(template)
                for applied in package.applied_struct_datas[template]:
                    found = False
                    for t in self.applied_struct_declarations[decl]:
                        if applied == t.data:
                            found = True
                            break
                    if not found:
                        a = decl.apply_template(applied.applied_templates)
                        decls.append(a)
                        self.register(a)
        return decls

    def validate_types(self):
        for sd in self.struct_declarations:
            sd.update_types()
        for fd in self.function_declarations:
            fd.update_types()
        for sd in self.applied_function_declarations:
            sd.update_types()

    def is_valid(self) -> bool:
        for c in self._late_create_casts:
            to = TypeData.new_raw(c[0], c[1])
            try:
                to.update_types()
            except AnalyzerException as e:
                log_error(e, to.trace_package)
            d = FunctionDeclaration(c[0], c[1], f'__cast_{str(to).replace(":", "_")}', [c[2]], [], c[3])
            self.register(d)

        self.validate_types()

        valid = True
        for i in self.function_declarations:
            if not i.is_template():
                valid *= i.is_valid()

        for i in self.struct_declarations:
            valid *= i.is_valid()

        new_struct_generics = self._get_created_applied_functions()
        new_function_generics = self._get_created_applied_structs()
        while new_struct_generics or new_function_generics:
            for f in new_struct_generics:
                f.update_types()
                valid *= f.is_valid()
            new_struct_generics = self._get_created_applied_functions()

            for s in new_function_generics:
                s.update_types()
                valid *= s.is_valid()
            new_function_generics = self._get_created_applied_structs()

        return valid


class Package:
    def __init__(self, path: Path, imports: List[Path]):
        self.path = path
        self.imports: List[Path] = imports
        self.function_datas: List[FunctionData] = []
        self.struct_datas: List[StructData] = []
        self.other_packages: List[Package] = []
        self.storage: Optional[GlobalStorage] = None

        self.applied_function_datas: Dict[FunctionData, List[AppliedFunctionData]] = {}
        self.applied_struct_datas: Dict[StructData, List[AppliedStructData]] = {}

        self.sources: Optional[str] = None

    def get_source_fragment(self, start_pos: int, end_pos: int, start_line: int, end_line: int) -> List[str]:
        if self.sources is None:
            raise ValueError
        copy = self.sources[:start_pos] + PrintColor.UNDERLINE + self.sources[
                                                                 start_pos:end_pos + 1] + PrintColor.END + PrintColor.BOLD + self.sources[
                                                                                                                             end_pos + 1:]
        lines = copy.splitlines()
        lines = lines[max(start_line - 2, 0):min(end_line + 3, len(lines))]
        for i in range(len(lines)):
            lines[i] = PrintColor.BOLD + lines[i] + PrintColor.END
        return lines

    def register(self, v: Data):
        if isinstance(v, AppliedFunctionData):
            if v not in self.applied_function_datas[v.src_function]:
                self.applied_function_datas[v.src_function].append(v)
            else:
                raise KeyError(str(v))
        elif isinstance(v, FunctionData):
            if v not in self.function_datas:
                self.function_datas.append(v)
                if v.is_template():
                    self.applied_function_datas[v] = []
            else:
                raise KeyError(str(v))
        elif isinstance(v, AppliedStructData):
            if v not in self.applied_struct_datas[v.src_sd]:
                self.applied_struct_datas[v.src_sd].append(v)
            else:
                raise KeyError(str(v))
        elif isinstance(v, StructData):
            if v not in self.struct_datas:
                self.struct_datas.append(v)
                if v.is_template():
                    self.applied_struct_datas[v] = []
            else:
                raise KeyError(str(v))
        else:
            raise ValueError

    def get_function_data(self, fd: FunctionImage):
        for f in self.function_datas:
            if f == fd:
                return f
        return None

    def get_struct_data(self, name):
        for s in self.struct_datas:
            if s.name == name:
                return s
        return None


BUILD_IN_PACK = Package(Path([]), [])

VOID_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "void", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "void", []))

NOTYPE_T = TypeData.new_data(StructData(BUILD_IN_PACK, "notype", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "notype", []))

I32_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "i32", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "i32", []))
I64_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "i64", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "i64", []))
UI32_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "ui32", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "ui32", []))
UI64_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "ui64", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "ui64", []))

# SIZE_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "size", []), 0, [])
# BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "size", []))
USIZE_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "usize", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "usize", []))

F32_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "f32", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "f32", []))
F64_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "f64", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "f64", []))

CHAR_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "char", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "char", []))

BOOL_T: Optional[TypeData] = TypeData.new_data(StructData(BUILD_IN_PACK, "bool", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "bool", []))

TYPE_T = TypeData.new_data(StructData(BUILD_IN_PACK, "type", []), 0, [], False)
BUILD_IN_PACK.struct_datas.append(StructData(BUILD_IN_PACK, "type", []))

CHAR_ARR_T: Optional[TypeData] = None
ARR_T: Optional[TypeData] = None


def find_arr_t(storage: GlobalStorage):
    global ARR_T
    for p in storage.all_packages:
        if p.get_struct_data('st_arr') is not None:
            ARR_T = TypeData.new_raw(p, RawType(p.path, 'st_arr', 0,
                                                [RawType(Path([]), 'T', 0, [], BUILD_IN_PACK)], p))


def find_char_arr_t(storage: GlobalStorage):
    global CHAR_ARR_T
    for p in storage.all_packages:
        if p.get_struct_data('st_arr') is not None:
            CHAR_ARR_T = TypeData.new_raw(p, RawType(p.path, 'st_arr', 0,
                                                     [RawType(Path([]), 'char', 0, [], BUILD_IN_PACK)], p))
    if CHAR_ARR_T:
        CHAR_ARR_T.make_not_raw()


def get_arr_t():
    global ARR_T
    return ARR_T


def get_char_arr_t():
    global CHAR_ARR_T
    return CHAR_ARR_T


class Declaration:
    def update_types(self):
        raise NotImplementedError


class StructDeclaration(Declaration):
    def update_types(self):
        self.data.update_types()
        for mod, t, n in self.fields:
            if isinstance(t, TypeData):
                try:
                    t.update_types()
                except AnalyzerException as e:
                    log_error(e, self.data.package, self)

    def is_valid(self) -> bool:
        if self.is_extern() and self.is_template():
            log_error(AnalyzerException(f"can't create extern template struct", self.position), self.data.package, self)
        for _, t, _ in self.fields:
            if isinstance(t, TypeData):
                if t == NOTYPE_T:
                    log_error(AnalyzerException(f"struct field can't be var", t.raw.position), self.data.package, self)
                    return False
                if t.pointer_level == 0 and t.data not in BUILD_IN_PACK.struct_datas:
                    decl = self.data.package.storage.get_declaration_by_data(t.data)
                    if self.is_template():
                        decl = decl.apply_template(t.templates)
                    for dt, _ in decl.fields:
                        if dt.pointer_level == 0 and dt.data == self.data:
                            log_error(AnalyzerException(f"struct fields cyclic dependency", t.raw.position),
                                      self.data.package, self)
                            return False
        return True

    def __init__(self, package: Package, name: str, fields: List[Tuple[str, RawType, str]], methods: list,
                 templates: List[RawType], is_extern: bool = False,
                 position: Optional[Tuple[int, int, int, int]] = None):
        self.data = StructData(package, name, templates, is_extern)
        self.fields: List[Tuple[str, Union[TypeData, RawType], str]] = fields[:]
        for i, (mod, t, n) in enumerate(self.fields):
            if t not in templates:
                if isinstance(t, TypeData) and t == NOTYPE_T:
                    self.fields[i] = (mod, t, n)
                else:
                    if not t.has_any_template(templates):
                        self.fields[i] = (mod, TypeData.new_raw(package, t), n)
                    else:
                        self.fields[i] = (mod, t, n)

        self.position = position
        self.extern = is_extern

    def is_extern(self):
        return self.extern

    def apply_template(self, templates: List[TypeData]) -> 'AppliedStructDeclaration':
        if len(self.data.template_types) == len(templates):
            new_fields: List[Tuple[str, TypeData, str]] = self.fields[:]
            template_dict: Dict[RawType, TypeData] = {}
            for t, to in zip(self.data.template_types, templates):
                template_dict[t] = to

            for i, (mod, t, n) in enumerate(new_fields):
                if isinstance(t, RawType):
                    new_fields[i] = (mod, TypeData.new_raw_templates(t, template_dict), n)

            # TODO: methods
            s = AppliedStructDeclaration(new_fields, [], self, templates)
            s.update_types()
            return s
        else:
            raise BadTemplateException

    def is_template(self):
        return self.data.is_template()

    def __str__(self):
        return str(self.data)


class AppliedStructDeclaration(StructDeclaration):
    def __init__(self, fields: List[Tuple[str, TypeData, str]], methods: list, src_sd: StructDeclaration,
                 applied_templates: List[TypeData]):
        self.data = AppliedStructData(src_sd.data.package, src_sd.data.name, src_sd.data, applied_templates)
        self.fields = fields
        self.methods = methods
        self.src_sd = src_sd
        self.applied_templates = applied_templates
        self.extern = False

    def __str__(self):
        return f"{self.src_sd.data.package.path}:{self.src_sd.data.name}[{','.join(f'{t}={a}' for t, a in zip(self.src_sd.data.template_types, self.applied_templates))}]"


class StateException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class FunctionDeclaration(Declaration):
    def update_types(self):
        if not self.is_template():
            try:
                self.data.update_types()
            except AnalyzerException as e:
                log_error(e, self.data.package, self)
            if self.body is not None:
                self.body.update_types()

    def __init__(self, package: Package, return_type: RawType, name: str,
                 argument_declaration: List[Tuple[RawType, str]], templates: List[RawType],
                 body: Optional['FunctionBody'], is_safe: bool = True, position: Tuple[int, int, int, int] = None):

        self.position = position
        self.arguments: List[Tuple[Union[RawType, TypeData], str]] = argument_declaration

        for i, (arg, n) in enumerate(self.arguments):
            if not arg.has_any_template(templates):
                self.arguments[i] = (TypeData.new_raw(package, arg), n)

        if self.arguments:
            args_t, _ = zip(*self.arguments)
            args_t = list(args_t)
        else:
            args_t = []

        if not return_type.has_any_template(templates):
            return_type = TypeData.new_raw(package, return_type)

        self.data = FunctionData(package, return_type, name, args_t, templates, is_safe)

        self.body = body
        if body is not None:
            self.body.function = self
        else:
            if not self.is_extern():
                raise StateException

    def check_returns(self):
        if self.data.type == VOID_T:
            return True

        def check_expr(expr):
            if isinstance(expr, IfExpression):
                if expr.else_body:
                    return check_expr(expr.if_body) and check_expr(expr.else_body)
                else:
                    return check_expr(expr.if_body)
            elif isinstance(expr, WhileExpression):
                return check_expr(expr.expr)
            elif isinstance(expr, VisibilityAreaExpression):
                return check_exprs(expr.exprs)
            elif isinstance(expr, UnsafeExpression):
                return check_expr(expr.expr)
            elif isinstance(expr, ReturnExpression):
                return True

            return False

        def check_exprs(exprs):
            for e in exprs:
                if check_expr(e):
                    return True
            return False

        return check_exprs(self.body.expressions)

    def is_extern(self):
        return not self.is_template() and self.body is None

    def is_valid(self) -> bool:
        if not self.is_extern() and not self.check_returns():
            e = AnalyzerException(f"not all paths return something", self.position)
            log_error(e, self.data.package, self)
            return False

        if (self.data.name.startswith("__binary_operator") or self.data.name == "__operator_square_brackets") and len(self.arguments) != 2:
            e = AnalyzerException(f"this operator function must have only 2 arguments", self.position)
            log_error(e, self.data.package, self)
        elif self.data.name.startswith("__unary_operator") and len(self.arguments) != 1:
            e = AnalyzerException(f"this operator function must have only 1 argument", self.position)
            log_error(e, self.data.package, self)

        if self.data.name == "__copy" or self.data.name == "__destructor":
            if self.data.arg_types[0].pointer_level != 1:
                e = AnalyzerException(f"this method must have pointer argument", self.position)
                log_error(e, self.data.package, self)
                return False

            d = self.arguments[0][0].data
            if d and d.package != self.data.package:
                p = str(d.package.path)
                e = AnalyzerException(f"this method must be declarated in package {p if p else '[build-in]'}", self.position)
                log_error(e, self.data.package, self)
                return False

        if self.data.type == NOTYPE_T:
            raise StateException
        for t in self.data.arg_types:
            if t == NOTYPE_T:
                raise StateException
        if not self.is_extern():
            if self.body.is_valid():
                self.body.simplify()
                self.body.paste_copies_destructors()
                return True
            else:
                return False
        else:
            return True

    def is_template(self):
        return self.data.is_template()

    def get_arguments_as_variables(self) -> List[VariableData]:
        if self.is_template():
            raise StateException
        v = []
        for type, name in self.arguments:
            v.append(VariableData(type, name))
        return v

    def apply_template(self, templates: List[TypeData]) -> 'AppliedFunctionDeclarationContainer':
        if self.is_extern():
            raise StateException
        try:
            temp_dict: Dict[RawType, TypeData] = {}
            for t, to in zip(self.data.template_types, templates):
                temp_dict[t] = to

            new_data = self.data.apply_template(templates)
            new_arguments: List[Tuple[TypeData, str]] = []
            for i, (_, n) in enumerate(self.arguments):
                new_arguments.append((new_data.arg_types[i], n))
            new_body = FunctionBody()
            for e in self.body.expressions:
                new_e: Expression = e.copy()
                new_e.replace_template(temp_dict)
                new_body.add_expression(new_e)

            return AppliedFunctionDeclarationContainer(self.data.package, new_data.type, self.data.name, new_arguments,
                                                       new_body, templates, self)

        except BadTemplateException as e:
            raise e

    def __str__(self):
        return str(self.data)

class AppliedFunctionDeclarationContainer(FunctionDeclaration):
    def __init__(self, package: Package, return_type: TypeData, name: str,
                 argument_declaration: List[Tuple[TypeData, str]],
                 body: 'FunctionBody', applied_templates: List[TypeData], src_fd: FunctionDeclaration):
        # super().__init__(package, return_type, name, argument_declaration, [], body)
        # TODO: fix
        self.position = src_fd.position
        self.arguments = argument_declaration

        if argument_declaration:
            a_types, _ = zip(*argument_declaration)
            a_types = list(a_types)
        else:
            a_types = []
        self.data = AppliedFunctionData(package, return_type, name, a_types, applied_templates, src_fd.data)

        self.body = body
        self.body.function = self

        self.src_fd = src_fd

    def __str__(self):
        return f"{self.data.package.path}:{self.data.name}" \
               f"[{', '.join([f'{temp}={type}' for temp, type in zip(self.src_fd.data.template_types, self.data.applied_templates)])}]" \
               f"({', '.join([str(i) for i in self.src_fd.data.arg_types])})"


class FunctionBody:
    def __init__(self):
        self.expressions: List[Expression] = []
        self.function: Optional[FunctionDeclaration] = None
        self.visibility_stack = VisibilityStack()

    def is_valid(self) -> bool:
        if not self.function.data.is_safe:
            settings.switch_unsafe()
        valid = True
        if self.function.is_template():
            raise StateException
        self.visibility_stack.clear()
        self.visibility_stack.push_level()

        args = self.function.get_arguments_as_variables()
        for i in args:
            self.visibility_stack.register_variable(i)
        for expr in self.expressions:
            try:
                expr.check_valid()
            except AnalyzerException as e:
                valid = False
                log_error(e, self.function.data.package, self.function)

        settings.switch_safe()
        return valid

    def simplify(self):
        exprs = []

        for expr in self.expressions:
            l, e = expr.get_simplified()
            exprs += l + [e]

        self.expressions = exprs

    def paste_copies_destructors(self):
        self.visibility_stack.clear()
        self.visibility_stack.push_level()

        args = self.function.get_arguments_as_variables()
        for i in args:
            self.visibility_stack.register_variable(i)

        def gen_destructor(v: VariableData):
            d = VariableDestroyExpression(v.name)
            d.set_body(self)
            d.try_find_function()
            return d

        def gen_copy(expr):
            e = CopyExpression(expr, expr.position)
            e.set_body(self)
            e.try_find_function()
            return e

        def check_need_copy(expr: Expression):
            return isinstance(expr, VariableExpression) or \
                   isinstance(expr, GetterExpression) or \
                   isinstance(expr, PointerUnpackExpression) or \
                   isinstance(expr, UnsafeExpression) and check_need_copy(expr.expr)

        def recursive(expr, parent_exprs_list):
            # after simplification only
            if isinstance(expr, FunctionInvokeExpression):
                for i, arg in enumerate(expr.arguments):
                    recursive(arg, parent_exprs_list)
                    if check_need_copy(arg):
                        expr.arguments[i] = gen_copy(arg)

            elif isinstance(expr, BinaryOperatorExpression):
                recursive(expr.expr1, parent_exprs_list)
                recursive(expr.expr2, parent_exprs_list)

                if check_need_copy(expr.expr1):
                    expr.expr1 = gen_copy(expr.expr1)
                if check_need_copy(expr.expr2):
                    expr.expr2 = gen_copy(expr.expr2)

            elif isinstance(expr, UnaryOperatorExpression):
                recursive(expr.expr, parent_exprs_list)
                if check_need_copy(expr.expr):
                    expr.expr = gen_copy(expr.expr)

            #elif isinstance(expr, CastExpression):
            #    recursive(expr.expr, parent_exprs_list)

            #elif isinstance(expr, StructConstructorExpression):
            #    for expr in expr.exprs:
            #        recursive(expr, parent_exprs_list)

            #elif isinstance(expr, GetterExpression):
            #    pass

            #elif isinstance(expr, ArrayCreationExpression):
            #    pass

            elif isinstance(expr, VariableCreationExpression):
                self.visibility_stack.register_variable(expr.data)

                if not expr.expr:
                    return
                recursive(expr.expr, parent_exprs_list)

                name = f"ASSIGN_{gen_variable_name(expr.position)}"

                var = VariableCreationExpression(name, expr.expr, expr.expr.get_out_type().raw, expr.position)
                var.set_body(expr.function_body)
                var.update_types()

                index = parent_exprs_list.index(expr)
                parent_exprs_list.insert(index, var)

                v = VariableExpression(name, expr.position)
                v.set_body(expr.function_body)
                v.type = expr.expr.get_out_type()
                expr.expr = gen_copy(v)

            elif isinstance(expr, ExpressionValueSetExpression):
                recursive(expr.expr, parent_exprs_list)
                name = f"ASSIGN_{gen_variable_name(expr.position)}"

                var = VariableCreationExpression(name, expr.expr, expr.expr.get_out_type().raw, expr.position)
                var.set_body(expr.function_body)
                var.update_types()

                index = parent_exprs_list.index(expr)
                parent_exprs_list.insert(index, var)

                v = VariableExpression(name, expr.position)
                v.set_body(expr.function_body)
                v.type = expr.expr.get_out_type()
                expr.expr = gen_copy(v)

            elif isinstance(expr, UnsafeExpression):
                recursive(expr.expr, parent_exprs_list)

            elif isinstance(expr, IfExpression):
                recursive(expr.if_body, parent_exprs_list)
                if expr.else_body:
                    recursive(expr.else_body, parent_exprs_list)

            elif isinstance(expr, WhileExpression):
                recursive(expr.body, parent_exprs_list)

            elif isinstance(expr, VisibilityAreaExpression):
                self.visibility_stack.push_level()
                for e in expr.exprs[:]:
                    recursive(e, expr.exprs)
                need_delete = self.visibility_stack.take_level()
                for v in need_delete[::-1]:
                    expr.exprs.append(gen_destructor(v))
                self.visibility_stack.pop_level()

            elif isinstance(expr, ReturnExpression):
                #recursive(expr.expr, parent_exprs_list)

                need_delete = []
                for l in self.visibility_stack.levels[::-1]:
                    need_delete += l

                index = parent_exprs_list.index(expr)
                if isinstance(expr.expr, VariableExpression):
                    not_delete: VariableData = self.visibility_stack.find_variable(expr.expr.name)
                    need_delete.remove(not_delete)

                    prev = parent_exprs_list[index-1]
                    if prev and isinstance(prev, VariableCreationExpression) and prev.name == expr.expr.name and \
                            isinstance(prev.expr, CopyExpression):
                        index -= 1
                        parent_exprs_list.remove(prev)
                        expr.expr = prev.expr.expr

                while len(parent_exprs_list) != index:
                    parent_exprs_list.pop(-1)

                for v in need_delete[::-1]:
                    parent_exprs_list.append(gen_destructor(v))

                parent_exprs_list.append(expr)

        for e in self.expressions[:]:
            recursive(e, self.expressions)

    def update_types(self):
        for expr in self.expressions:
            try:
                expr.update_types()
            except AnalyzerException as e:
                log_error(e, self.function.data.package, self.function)

    def add_expression(self, expr: 'Expression'):
        expr.set_body(self)
        self.expressions.append(expr)


class Expression:
    def __init__(self, position: Optional[Tuple[int, int, int, int]] = None):
        self.function_body: Optional[FunctionBody] = None
        self.position = position

    def get_out_type(self):
        raise NotImplementedError

    def check_valid(self):
        raise NotImplementedError

    def set_body(self, body: FunctionBody):
        self.function_body = body

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        raise NotImplementedError

    def update_types(self):
        raise NotImplementedError

    def copy(self):
        raise NotImplementedError

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        raise NotImplementedError


# TODO: MethodInvokeExpr because priority of using method of object package

class FunctionInvokeExpression(Expression):
    def update_types(self):
        for i in self.arguments:
            i.update_types()
        for i in self.templates:
            i.update_types()

    def __init__(self, path: Path, name: str, arguments: List[Expression], templates: List[RawType],
                 position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.name = name
        self.arguments = arguments
        self.templates = [TypeData.new_raw(t.src_pack, t) for t in templates]
        self.path = path

        self.function: Optional[Union[FunctionData, AppliedFunctionData]] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        for i in self.arguments:
            i.set_body(body)

    def get_out_type(self):
        if self.function is None:
            self.check_valid()

        t = self.function.type
        t.set_immutable()
        return t

    def gen_arg_auto_pack(self, types_may_be: List[TypeData]):
        for i, t_arg in enumerate(types_may_be):
            arg = self.arguments[i]
            for _ in range(t_arg.pointer_level - arg.get_out_type().pointer_level):
                p = PointerGetExpression(arg, arg.position)
                p.set_body(self.function_body)
                p.calc_type()
                self.arguments[i] = p

    def check_valid(self):
        for arg in self.arguments:
            arg.check_valid()
        if self.function is None:
            self._find_function()
            if self.function is None:
                same_functions = find_same_functions(self.name, self.function_body.function.data.package)
                if not self.is_template():
                    text = f"function {self.name}({', '.join([str(i.get_out_type()) for i in self.arguments])}) doesn't exists"
                else:
                    text = f"function {self.name}[{', '.join([str(i) for i in self.templates])}]" \
                           f"({', '.join([str(i.get_out_type()) for i in self.arguments])}) doesn't exists"
                if same_functions:
                    text += f". Do you mean: {', '.join([str(i) for i in same_functions])}?"
                raise AnalyzerException(text, self.position)
            if settings.curr_is_safe() and not self.function.is_safe:
                raise AnalyzerException(f"can't use unsafe {self.name}[{', '.join([str(i) for i in self.templates])}]"
                                        f"({', '.join([str(i.get_out_type()) for i in self.arguments])}) in safe code",
                                        self.position)
            if settings.get_current().allow_auto_pack:
                self.gen_arg_auto_pack(self.function.arg_types)
                for arg in self.arguments:
                    arg.check_valid()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        for i, t in enumerate(self.templates):
            self.templates[i] = TypeData.new_raw_templates(t.raw, template2type)
        for a in self.arguments:
            a.replace_template(template2type)

    def copy(self):
        new_arguments = []
        for a in self.arguments:
            new_arguments.append(a.copy())
        return FunctionInvokeExpression(self.path, self.name, new_arguments, [t.raw for t in self.templates],
                                        self.position)

    def is_template(self):
        return len(self.templates) > 0

    def _find_function(self):
        arg_types = [i.get_out_type() for i in self.arguments]
        funcs = find_function(self.function_body.function.data.package, self.path, self.name, self.templates,
                              arg_types)
        if len(funcs) > 1:
            fit = []
            functions = functions_by_path(self.path, self.function_body.function.data.package)
            fi = FunctionImage(self.name, arg_types, self.templates)
            for i in functions:
                if i == fi:
                    fit.append(i)
            raise AnalyzerException(
                f"it isn't possible to determine current function, variants: {', '.join([str(i) for i in fit])}",
                self.position)
        elif len(funcs) == 1:
            f = funcs[0]
            if self.is_template():
                self.function = f.apply_template(self.templates)
                try:
                    self.function.package.register(self.function)
                except KeyError:
                    pass
            else:
                if f.is_template():
                    temps = f.try_generate_template(arg_types)
                    try:
                        self.function = f.apply_template(temps)
                    except BadTemplateException:
                        raise AnalyzerException(f"can't generate template for function {str(f)}", self.position)
                    try:
                        self.function.package.register(self.function)
                    except KeyError:
                        pass
                else:
                    self.function = f
        else:
            self.function = None

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        lines = []
        new_args = []
        for arg in self.arguments:
            l, a = arg.get_simplified()
            lines += l
            new_args.append(a)

        expr = FunctionInvokeExpression(self.path, self.name, new_args, [t.raw for t in self.templates], self.position)
        expr.set_body(self.function_body)
        expr.function = self.function

        if self.get_out_type() != VOID_T:
            name = gen_variable_name(self.position)

            var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
            var.set_body(self.function_body)
            var.update_types()

            return lines + [var], VariableExpression(name, self.position)
        else:
            return lines, expr


_op_to_text = {
    '+': 'plus',
    '-': 'minus',
    '*': 'times',
    '/': 'divide',
    '%': 'mod',
    '&': 'and',
    '|': 'or',
    '^': 'xor',
    '<<': 'lshift',
    '>>': 'rshift',
    '<': 'less',
    '>': 'greater',
    '<=': 'less_equals',
    '>=': 'greater_equals',
    '==': 'equals',
    '!=': 'not_equals',
    '!': 'not',
    '[]': 'square_brackets',
}

def operator_to_text(op):
    return _op_to_text[op]


class BinaryOperatorExpression(Expression):
    def update_types(self):
        self.expr1.update_types()
        self.expr2.update_types()

    def __init__(self, expr1: Expression, expr2: Expression, operator: str,
                 position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.expr1: Expression = expr1
        self.expr2: Expression = expr2
        self.operator: str = operator

        self.function: Optional[FunctionData] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr1.set_body(body)
        self.expr2.set_body(body)

    def gen_pack(self, types_may_be: Tuple[TypeData, TypeData]):
        for i, t_arg in enumerate(types_may_be):
            arg = self.expr1 if i == 0 else self.expr2
            for _ in range(t_arg.pointer_level - arg.get_out_type().pointer_level):
                p = PointerGetExpression(arg, arg.position)
                p.set_body(self.function_body)
                p.calc_type()
                if i == 0:
                    self.expr1 = p
                else:
                    self.expr2 = p

    def _try_find_function(self):
        if self.function is None:
            self.function = self.find_operator_function()
            if self.function is None:
                # TODO: fix text
                raise AnalyzerException(
                    f"function __binary_operator_{_op_to_text[self.operator]}({self.expr1.get_out_type()}, {self.expr2.get_out_type()}) doesn't exists",
                    self.position)
            else:
                if self.function.is_template():
                    temps = self.function.try_generate_template([self.expr1.get_out_type(), self.expr2.get_out_type()])
                    self.function = self.function.apply_template(temps)
                    try:
                        self.function.package.register(self.function)
                    except KeyError:
                        pass

    def get_out_type(self):
        self._try_find_function()
        t = self.function.type
        t.set_immutable()
        return t

    def check_valid(self):
        self.expr1.check_valid()
        self.expr2.check_valid()
        self._try_find_function()
        # TODO: not always recheck
        self.gen_pack((self.function.arg_types[0], self.function.arg_types[1]))
        self.expr1.check_valid()
        self.expr2.check_valid()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr1.replace_template(template2type)
        self.expr2.replace_template(template2type)

    def copy(self):
        return BinaryOperatorExpression(self.expr1.copy(), self.expr2.copy(), self.operator, self.position)

    def find_operator_function(self) -> Optional[FunctionData]:
        funcs = find_function(self.function_body.function.data.package, Path([]),
                              f'__binary_operator_{_op_to_text[self.operator]}', [],
                              [self.expr1.get_out_type(), self.expr2.get_out_type()], )
        if funcs:
            # TODO: check if lot
            return funcs[0]
        return None

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l1, e1 = self.expr1.get_simplified()
        l2, e2 = self.expr2.get_simplified()

        name = gen_variable_name(self.position)
        expr = BinaryOperatorExpression(e1, e2, self.operator, self.position)
        expr.set_body(self.function_body)
        expr.function = self.function

        var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        var.set_body(self.function_body)
        var.update_types()

        return l1 + l2 + [var], VariableExpression(name, self.position)


class UnaryOperatorExpression(Expression):
    def update_types(self):
        self.expr.update_types()

    def __init__(self, expr: Expression, operator: str, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.expr: Expression = expr
        self.operator: str = operator

        self.function: Optional[FunctionData] = None

    def gen_pack(self, type_may_be: TypeData):
        t_arg = type_may_be
        arg = self.expr
        for _ in range(t_arg.pointer_level - arg.get_out_type().pointer_level):
            p = PointerGetExpression(arg, arg.position)
            p.set_body(self.function_body)
            p.calc_type()
            self.expr = p

    def _try_find_function(self):
        if self.function is None:
            self.function = self.find_operator_function()
            if self.function is None:
                # TODO: fix text
                raise AnalyzerException(
                    f"function __unary_operator_{_op_to_text[self.operator]}({self.expr.get_out_type()}) doesn't exists",
                    self.position)
            else:
                if self.function.is_template():
                    temps = self.function.try_generate_template([self.expr.get_out_type()])
                    self.function = self.function.apply_template(temps)
                    try:
                        self.function.package.register(self.function)
                    except KeyError:
                        pass

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def get_out_type(self):
        self._try_find_function()
        t = self.function.type
        t.set_immutable()
        return t

    def check_valid(self):
        self.expr.check_valid()
        self._try_find_function()
        # TODO: not always recheck
        self.gen_pack(self.function.arg_types[0])
        self.expr.check_valid()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def copy(self):
        return UnaryOperatorExpression(self.expr.copy(), self.operator, self.position)

    def find_operator_function(self) -> Optional[FunctionData]:
        funcs = find_function(self.function_body.function.data.package, Path([]),
                              f'__unary_operator_{_op_to_text[self.operator]}', [],
                              [self.expr.get_out_type()])
        if funcs:
            # TODO: check if lot
            return funcs[0]
        return None

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        name = gen_variable_name(self.position)

        expr = UnaryOperatorExpression(e, self.operator, self.position)
        expr.set_body(self.function_body)
        expr.function = self.function

        var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        var.set_body(self.function_body)
        var.update_types()

        return l + [var], VariableExpression(name, self.position)


class VariableExpression(Expression):
    def update_types(self):
        pass

    def __init__(self, name, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.name = name
        self.type: Optional[TypeData] = None

    def _get_type(self):
        v: VariableData = self.function_body.visibility_stack.find_variable(self.name)
        if v is not None:
            self.type = v.type
        else:
            raise AnalyzerException(f"variable with name {self.name} doesn't exists", self.position)

    def get_out_type(self):
        if self.type is None:
            self._get_type()
        self.type.set_mutable()
        return self.type

    def check_valid(self):
        if self.type is None:
            self._get_type()
        if self.type == NOTYPE_T:
            raise StateException

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        pass

    def copy(self):
        return VariableExpression(self.name, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        c = self.copy()
        c.set_body(self.function_body)
        c.update_types()
        return [], c


class VariableCreationExpression(Expression):
    def __init__(self, name: str, expr: Optional[Expression] = None, required_type: RawType = NOTYPE_T.raw,
                 position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.expr = expr
        self.name = name
        self.raw_type = required_type

        if required_type != NOTYPE_T.raw:
            self.type: Optional[TypeData] = TypeData.new_raw(required_type.src_pack, required_type)
            self.data: Optional[VariableData] = VariableData(self.type, self.name)
        else:
            self.type = None
            self.data = None

        self.template_dict: Optional[Dict[RawType, TypeData]] = None

    def update_types(self):
        if self.expr:
            self.expr.update_types()
        if self.type is not None:
            self.type.update_types()
            self.data = VariableData(self.type, self.name)
        if self.data:
            self.data.update_types()

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        if self.expr is not None:
            self.expr.set_body(body)

    def check_valid(self):
        if self.expr is None:
            if self.data is None or self.data.type is None:
                raise AnalyzerException(f"can't calculate type of variable {self.name}: you must specify type",
                                        self.position)
            if not settings.get_current().allow_creation_uninited_vars:
                raise AnalyzerException(f"can't create uninited variable in safe",
                                        self.position)
            if self.data.type.pointer_level != 0:
                raise AnalyzerException(f"can't create empty pointer var {self.data.name}",
                                        self.position)
        else:
            self.expr.check_valid()
            if self.data is None:
                t: TypeData = self.expr.get_out_type().copy()
                t.is_const = self.raw_type.is_const
                self.data = VariableData(t, self.name)
                self.data.update_types()
            if not settings.get_current().allow_pointer_variables:
                if self.data.type.pointer_level != 0:
                    raise AnalyzerException(f"pointer type of variables isn't allowed in safe", self.position)
            if self.data.type == NOTYPE_T:
                self.data.type = self.expr.get_out_type()
            else:
                if self.data.type != self.expr.get_out_type():
                    raise AnalyzerException(f"type of variable {self.data.name} ({self.data.type}) doesn't match with "
                                            f"type of expression ({self.expr.get_out_type()})", self.position)
        try:
            self.function_body.visibility_stack.register_variable(self.data)
        except KeyError:
            raise AnalyzerException(f"variable with name {self.data.name} already exists in this scope", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        if self.type:
            self.type = TypeData.new_raw_templates(self.type.raw, template2type)
        if self.expr:
            self.expr.replace_template(template2type)

    def get_out_type(self):
        raise StateException

    def copy(self):
        if self.expr:
            return VariableCreationExpression(self.name, self.expr.copy(), self.type.raw if self.type else NOTYPE_T.raw,
                                              self.position)
        else:
            return VariableCreationExpression(self.name, None, self.type.raw if self.type else NOTYPE_T.raw,
                                              self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        if self.expr:
            l, e = self.expr.get_simplified()

            if l and isinstance(l[-1], VariableCreationExpression):
                var = l.pop(-1)
                p = var.expr
                if isinstance(e, PointerUnpackExpression):
                    p = PointerUnpackExpression(p, p.position)
                    p.set_body(self.function_body)
                expr = VariableCreationExpression(self.name, p, self.expr.get_out_type().raw, self.position)
            else:
                expr = VariableCreationExpression(self.name, e, self.expr.get_out_type().raw, self.position)

            expr.set_body(self.function_body)
            expr.update_types()
            return l, expr
        else:
            c = self.copy()
            c.set_body(self.function_body)
            c.update_types()
            return [], c


class ExpressionValueSetExpression(Expression):
    def update_types(self):
        self.expr.update_types()
        self.to.update_types()

    def __init__(self, to: Expression, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)

        self.to = to
        self.expr = expr

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.to.set_body(body)
        self.expr.set_body(body)

    def check_valid(self):
        self.to.check_valid()
        self.expr.check_valid()

        if self.to.get_out_type() == self.expr.get_out_type():
            if not self.to.get_out_type().is_mutable():
                if self.to.get_out_type().is_constant():
                    text = f"can't set value to constant expression"
                else:
                    text = f"can't set value to immutable expression"
                raise AnalyzerException(text, self.to.position)
        else:
            raise AnalyzerException(
                f"expressions types don't match ({self.to.get_out_type()} and {self.expr.get_out_type()})",
                self.position)

    def get_out_type(self):
        raise StateException

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.to.replace_template(template2type)
        self.expr.replace_template(template2type)

    def copy(self):
        return ExpressionValueSetExpression(self.to.copy(), self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l1, e1 = self.to.get_simplified()
        l2, e2 = self.expr.get_simplified()

        if l2 and isinstance(l2[-1], VariableCreationExpression):
            var = l2.pop(-1)
            p = var.expr
            if isinstance(e2, PointerUnpackExpression):
                p = PointerUnpackExpression(p, p.position)
                p.set_body(self.function_body)
            expr = ExpressionValueSetExpression(e1, p, self.position)
        else:
            expr = ExpressionValueSetExpression(e1, e2, self.position)

        expr.set_body(self.function_body)
        expr.update_types()
        return l1 + l2, expr


class ReturnExpression(Expression):
    def update_types(self):
        self.expr.update_types()

    def __init__(self, expr: Optional[Expression] = None, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        if self.expr is not None:
            self.expr.set_body(body)

    def get_out_type(self):
        raise StateException

    def check_valid(self):
        if self.expr:
            self.expr.check_valid()

            if self.function_body.function.data.type != self.expr.get_out_type():
                raise AnalyzerException(f"function return type ({self.function_body.function.data.type}) doesn't "
                                        f"match with expression type ({self.expr.get_out_type()})", self.position)
        else:
            if self.function_body.function.data.type != VOID_T:
                raise AnalyzerException(f"can't return {VOID_T} from function with return type "
                                        f"{self.function_body.function.data.type}", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def copy(self):
        return ReturnExpression(self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        expr = ReturnExpression(e, self.position)
        expr.set_body(self.function_body)
        expr.update_types()
        return l, expr


class Constant(Expression):
    def update_types(self):
        self.type, self.value = self.process_value(self.src_value)

    def __init__(self, value: str, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.type: Optional[TypeData] = None
        self.src_value = value
        self.value = None

    @staticmethod
    def calc_str_len(value: str):
        # +1 because \00 at the end
        return len(value) + 1 - value.count("\\a") - \
               value.count("\\b") - \
               value.count("\\e") - \
               value.count("\\f") - \
               value.count("\\n") - \
               value.count("\\r") - \
               value.count("\\t") - \
               value.count("\\v") - \
               value.count("\\\\") - \
               value.count("\\'") - \
               value.count("\\\"") - \
               len(re.findall(r'\\[0-7]{3}', value)) * 3 - \
               len(re.findall(r'\\x[0-9abcdefABCDEF]{2}', value)) * 3 - \
               len(re.findall(r'\\u[0-9]{4}', value)) * 4 - \
               len(re.findall(r'\\U[0-9]{8}', value)) * 3

    def process_value(self, value: str) -> Tuple[TypeData, Any]:
        global CHAR_ARR_T
        if CHAR_ARR_T is None:
            find_char_arr_t(self.function_body.function.data.package.storage)
        if re.match(r'^((\d+\.\d+)|(\.\d+))(f32|f64)?$', value):
            if 'f64' in value:
                t = F64_T.copy()
            else:
                t = F32_T.copy()
            t.raw.position = self.position
            return t, re.search(r'(\d+\.\d+)|(\.\d+)', value).group(0)
        elif re.match(
                r'^((0[xX][0-9a-fA-F]+)|(0[bB][01]+)|(0[oO][0-7]+)|(\d+))(i32|f32|i64|f64|ui32|ui64|usize)?$',
                value):
            v = re.search(r'(0[xX][0-9a-fA-F]+)|(0[bB][01]+)|(0[oO][0-7]+)|(\d+)', value).group(0)
            if 'x' in v or 'X' in v:
                v = str(int(v[2:], 16))
            elif 'b' in v or 'B' in v:
                v = str(int(v[2:], 2))
            elif 'o' in v or 'O' in v:
                v = str(int(v[2:], 8))

            if 'f32' in value:
                t = F32_T.copy()
            elif 'f64' in value:
                t = F64_T.copy()
            elif 'ui32' in value:
                t = UI32_T.copy()
            elif 'ui64' in value:
                t = UI64_T.copy()
            elif 'i64' in value:
                t = I64_T.copy()
            elif 'usize' in value:
                t = USIZE_T.copy()
            # elif 'size' in value:
            #    t = SIZE_T.copy()
            else:
                t = I32_T.copy()

            t.raw.position = self.position
            return t, v
        elif re.match(r'^".*"$', value):
            t = CHAR_ARR_T.copy()
            t.raw.position = self.position
            return t, value
        elif re.match(r"^'.+'$", value):
            t = CHAR_T.copy()
            t.raw.position = self.position
            return t, value
        elif re.match(r'^false|true$', value):
            t = BOOL_T.copy()
            t.raw.position = self.position
            return t, value
        else:
            raise NotImplementedError

    def get_out_type(self):
        self.type.set_immutable()
        return self.type

    def check_valid(self):
        pass

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        pass

    def copy(self):
        return Constant(self.src_value, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        c = self.copy()
        c.set_body(self.function_body)
        c.update_types()
        return [], c


class CastExpression(Expression):
    def update_types(self):
        self.expr.update_types()
        self.cast_type.update_types()

    def __init__(self, type_to: RawType, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        self.cast_type = TypeData.new_raw(type_to.src_pack, type_to)
        self.expr = expr
        self.function: Optional[FunctionData] = None
        super().__init__(position)

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def _find_function(self):
        functions = functions_by_path(Path([]), self.function_body.function.data.package)
        # TODO: make __cast_function normal name generation
        fi = FunctionImage(f'__cast_{str(self.cast_type).replace(":", "_")}', [self.expr.get_out_type()],
                           [])
        if fi in functions:
            self.function = functions[functions.index(fi)]
        else:
            self.function = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def get_out_type(self):
        self._try_find_function()
        if self.function:
            t = self.function.type
        else:
            t = self.cast_type
        t.set_immutable()
        return t

    def check_valid(self):
        self.expr.check_valid()
        self._try_find_function()

        if self.expr.get_out_type().pointer_level != 0 and self.cast_type.pointer_level != 0:
            if settings.get_current().allow_pointer_casts:
                if not self.expr.get_out_type().pointer_level == self.cast_type.pointer_level:
                    raise AnalyzerException(f"pointers levels aren't the same", self.position)
            else:
                raise AnalyzerException(f"pointers casts aren't allowed in safe", self.position)
        else:
            if self.function is None:
                raise AnalyzerException(
                    f'function __cast_{str(self.cast_type).replace(":", "_")}({self.expr.get_out_type()}) doesn\'t exists',
                    self.position
                )

    def _try_find_function(self):
        if self.function is None:
            self._find_function()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.cast_type = TypeData.new_raw_templates(self.cast_type.raw, template2type)
        self.expr.replace_template(template2type)

    def copy(self):
        return CastExpression(self.cast_type.raw, self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        name = gen_variable_name(self.position)
        expr = CastExpression(self.cast_type.raw, e, self.position)

        var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        var.set_body(self.function_body)
        var.update_types()

        return l + [var], VariableExpression(name, self.position)


class StructConstructorExpression(Expression):
    def __init__(self, type: RawType, init_exprs: List[Expression],
                 position: Optional[Tuple[int, int, int, int]] = None):
        self.type = TypeData.new_raw(type.src_pack, type)
        self.exprs = init_exprs
        super().__init__(position)

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        for e in self.exprs:
            e.set_body(body)

    def get_out_type(self):
        self.type.set_immutable()
        return self.type

    def check_valid(self):
        for e in self.exprs:
            e.check_valid()
        if self.type.data:
            sd = self.type.data.package.storage.get_declaration_by_data(self.type.data)
            if sd.is_template():
                sd = sd.apply_template(self.type.templates)

            if len(self.exprs) == len(sd.fields):
                for expr, (mod, t, n) in zip(self.exprs, sd.fields):
                    if expr.get_out_type() != t:
                        # TODO : fix text
                        raise AnalyzerException(
                            f"wrong expression type in constructor of {str(self.type)} ({t} != {expr.get_out_type()})",
                            expr.position)
            else:
                raise AnalyzerException(f"wrong count of arguments for type {str(self.type)}", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.type = TypeData.new_raw_templates(self.type.raw, template2type)
        for e in self.exprs:
            e.replace_template(template2type)

    def update_types(self):
        self.type.update_types()
        for e in self.exprs:
            e.update_types()

    def copy(self):
        return StructConstructorExpression(self.type.raw, [e.copy() for e in self.exprs], self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        lines = []
        exprs = []

        for e in self.exprs:
            l, e = e.get_simplified()
            lines += l
            exprs.append(e)

        name = gen_variable_name(self.position)
        expr = StructConstructorExpression(self.type.raw, exprs, self.position)
        expr.set_body(self.function_body)
        expr.update_types()

        var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        var.set_body(self.function_body)
        var.update_types()

        return lines + [var], VariableExpression(name, self.position)


class GetterExpression(Expression):
    def __init__(self, from_: Expression, what: str, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = from_
        self.what = what

        self.type: Optional[TypeData] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def gen_unpack(self):
        for i in range(self.expr.get_out_type().pointer_level):
            self.expr = PointerUnpackExpression(self.expr, self.position)
            self.expr.set_body(self.function_body)
            self.expr.calc_type()

    def get_type(self):
        expr_type: TypeData = self.expr.get_out_type()

        if expr_type.data:
            if expr_type.is_pointer():
                if settings.get_current().allow_auto_unpack:
                    self.gen_unpack()
                    expr_type = self.expr.get_out_type()
                else:
                    raise AnalyzerException(f"to get field value type ({str(expr_type)}) mustn't be pointer",
                                            self.position)
            sd = expr_type.data.package.storage.get_declaration_by_data(expr_type.data)

            if sd is not None:
                if isinstance(expr_type.data, AppliedStructData):
                    sd = sd.apply_template(expr_type.data.applied_templates)
                    sd.update_types()

                mods, types, names = zip(*sd.fields)
                if self.what in names:
                    i = names.index(self.what)
                    m = mods[i]
                    t = types[i]

                    if m == 'internal' and self.function_body.function.data.package != sd.data.package:
                        raise AnalyzerException(f"can't get access to {m} field of {expr_type}", self.position)

                    self.type = t.copy()
                    self.type.is_const = expr_type.is_constant()
            else:
                self.type = None
        else:
            self.type = None

    def get_out_type(self):
        if self.type is None:
            self.get_type()
            if self.type is None:
                raise StateException
        self.type.set_mutable()
        return self.type

    def check_valid(self):
        self.expr.check_valid()
        if self.type is None:
            self.get_type()
            if self.type is None:
                raise AnalyzerException(f"type {str(self.expr.get_out_type())} hasn't field {self.what}", self.position)
            if self.type.pointer_level != 0 and not settings.get_current().allow_struct_pointers_using:
                raise AnalyzerException(f"can't use pointer field in safe", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()
        # TODO: check self.type?

    def copy(self):
        return GetterExpression(self.expr.copy(), self.what, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        expr = GetterExpression(e, self.what, self.position)
        expr.set_body(self.function_body)
        expr.type = self.type
        return l, expr


class VisibilityAreaExpression(Expression):
    def __init__(self, expressions: List[Expression], position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.exprs = expressions

    def get_out_type(self):
        raise StateException

    def check_valid(self):
        self.function_body.visibility_stack.push_level()
        for e in self.exprs:
            e.check_valid()
        self.function_body.visibility_stack.pop_level()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        for e in self.exprs:
            e.replace_template(template2type)

    def update_types(self):
        for e in self.exprs:
            e.update_types()

    def copy(self):
        return VisibilityAreaExpression([e.copy() for e in self.exprs], self.position)

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        for e in self.exprs:
            e.set_body(body)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        exprs = []

        for e in self.exprs:
            l, e = e.get_simplified()
            exprs += l
            exprs.append(e)

        expr = VisibilityAreaExpression(exprs, self.position)
        expr.set_body(self.function_body)
        expr.update_types()
        return [], expr


class IfExpression(Expression):
    def __init__(self, expr: Expression, if_body: VisibilityAreaExpression,
                 else_body: Optional[VisibilityAreaExpression],
                 position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr
        self.if_body = if_body
        self.else_body = else_body

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)
        self.if_body.set_body(body)
        if self.else_body:
            self.else_body.set_body(body)

    def get_out_type(self):
        raise NotImplementedError

    def check_valid(self):
        self.expr.check_valid()
        self.if_body.check_valid()
        if self.else_body:
            self.else_body.check_valid()
        if self.expr.get_out_type() != BOOL_T:
            raise AnalyzerException(f"expression in if statement must have type {str(BOOL_T)}", self.expr.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)
        self.if_body.replace_template(template2type)
        if self.else_body:
            self.else_body.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()
        self.if_body.update_types()
        if self.else_body:
            self.else_body.update_types()

    def copy(self):
        return IfExpression(self.expr.copy(), self.if_body.copy(), self.else_body.copy() if self.else_body else None,
                            self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l1, e1 = self.expr.get_simplified()
        _, if_body = self.if_body.get_simplified()

        _, else_body = self.else_body.get_simplified() if self.else_body else (None, None)

        expr = IfExpression(e1, if_body, else_body, self.position)
        expr.set_body(self.function_body)
        expr.update_types()

        return l1, expr


class WhileExpression(Expression):
    def __init__(self, expr: Expression, body: VisibilityAreaExpression,
                 position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr
        self.body = body

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)
        self.body.set_body(body)

    def get_out_type(self):
        raise StateException

    def check_valid(self):
        self.expr.check_valid()
        self.body.check_valid()
        if self.expr.get_out_type() != BOOL_T:
            raise AnalyzerException(f"expression in while statement must have type {str(BOOL_T)}", self.expr.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)
        self.body.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()
        self.body.update_types()

    def copy(self):
        return WhileExpression(self.expr.copy(), self.body.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        # var a = cond
        # while a {
        #   a = cond
        # }

        name = gen_variable_name(self.expr.position)
        l1, e1 = self.expr.get_simplified()

        cl1, ce1 = l1[:-1], l1[-1].expr  # l1[-1] is VariableCreationExpression
        s = ExpressionValueSetExpression(VariableExpression(name, self.expr.position), ce1, self.expr.position)
        s.set_body(self.function_body)
        s.update_types()

        _, body = self.body.get_simplified()
        body: VisibilityAreaExpression = body
        new_body = VisibilityAreaExpression(body.exprs + cl1 + [s], body.position)
        new_body.set_body(self.function_body)
        new_body.update_types()

        return l1, WhileExpression(e1, new_body, self.position)


class PointerGetExpression(Expression):
    def __init__(self, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr
        self.type: Optional[TypeData] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def get_out_type(self):
        if self.type is None:
            self.calc_type()
        self.type.set_immutable()
        return self.type

    def calc_type(self):
        t: TypeData = self.expr.get_out_type()
        self.type = TypeData.new_data(t.data, t.pointer_level + 1, t.templates, t.is_const)
        self.type.is_mut = t.is_mut

    def check_valid(self):
        self.expr.check_valid()
        self.calc_type()
        # TODO: may be wrong state after get_out_type

        if not self.type.is_mut:
            raise AnalyzerException(f"can't get pointer of immutable expression", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()

    def copy(self):
        return PointerGetExpression(self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        expr = PointerGetExpression(e, self.position)
        expr.set_body(self.function_body)
        expr.update_types()
        return l, expr


class PointerUnpackExpression(Expression):
    def __init__(self, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr
        self.type: Optional[TypeData] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def get_out_type(self):
        if self.type is None:
            self.calc_type()
        self.type.set_mutable()
        return self.type

    def calc_type(self):
        t: TypeData = self.expr.get_out_type()
        self.type = TypeData.new_data(t.data, t.pointer_level - 1, t.templates, t.is_const)

    def check_valid(self):
        self.expr.check_valid()
        self.calc_type()
        if self.type.pointer_level < 0:
            raise AnalyzerException(f"can't unpack non-pointer expression", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()

    def copy(self):
        return PointerUnpackExpression(self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        l, e = self.expr.get_simplified()

        #name = gen_variable_name(self.position)
        expr = PointerUnpackExpression(e, self.position)
        expr.set_body(self.function_body)
        expr.update_types()
        return l, expr
        #var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        #var.set_body(self.function_body)
        #var.update_types()

        #return l + [var], VariableExpression(name, self.position)


'''class TypeExpression(Expression):
    def __init__(self, type: RawType, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.type = TypeData.new_raw(type.src_pack, type)

    def get_out_type(self):
        t = TYPE_T.copy()
        t.raw = t.raw.copy()
        t.raw.position = self.position
        return t

    def check_valid(self):
        pass

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.type = TypeData.new_raw_templates(self.type.raw, template2type)

    def update_types(self):
        self.type.update_types()

    def copy(self):
        return TypeExpression(self.type.raw, self.position)
'''


class UnsafeExpression(Expression):
    def __init__(self, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.expr = expr

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def get_out_type(self):
        return self.expr.get_out_type()

    def check_valid(self):
        if settings.curr_is_safe():
            settings.switch_unsafe()
            self.expr.check_valid()
            settings.switch_safe()
        else:
            raise AnalyzerException(f"can't put unsafe under unsafe", self.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()

    def copy(self):
        return UnsafeExpression(self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        if isinstance(self.expr, VisibilityAreaExpression):
            _, e = self.expr.get_simplified()

            expr = UnsafeExpression(e, self.position)
            expr.set_body(self.function_body)
            expr.update_types()
            return [], expr
        elif isinstance(self.expr, FunctionInvokeExpression) and self.expr.get_out_type() == VOID_T:
            l, e = self.expr.get_simplified()
            unsafe_area = VisibilityAreaExpression(l + [e], self.position)

            expr = UnsafeExpression(unsafe_area, self.position)
            expr.set_body(self.function_body)
            expr.update_types()
            return [], expr
        else:
            name = gen_variable_name(self.position)
            var = VariableCreationExpression(name, None, self.expr.get_out_type().raw, self.position)
            var.set_body(self.function_body)
            var.update_types()

            l, e = self.expr.get_simplified()
            s = ExpressionValueSetExpression(VariableExpression(name, self.position), e, self.position)
            unsafe_area = VisibilityAreaExpression(l + [s], self.position)

            expr = UnsafeExpression(unsafe_area, self.position)
            expr.set_body(self.function_body)
            expr.update_types()

            v = VariableExpression(name, self.position)
            v.set_body(self.function_body)
            v.update_types()

            return [var, expr], v


# TODO: сделать для Expression
class SizeofExpression(Expression):
    def __init__(self, type: RawType, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.type: TypeData = TypeData.new_raw(type.src_pack, type)

    def get_out_type(self):
        t = USIZE_T.copy()
        t.raw.position = self.position
        return t

    def check_valid(self):
        pass

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.type = TypeData.new_raw_templates(self.type.raw, template2type)

    def update_types(self):
        self.type.update_types()

    def copy(self):
        return SizeofExpression(self.type.raw, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        c = self.copy()
        c.set_body(self.function_body)
        c.update_types()

        return [], c


class TypeidExpression(Expression):
    def __init__(self, obj: Union[RawType, Expression], position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.obj = obj
        self.type: Optional[TypeData] = None
        if isinstance(self.obj, RawType):
            self.type = TypeData.new_raw(self.obj.src_pack, self.obj)

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        if isinstance(self.obj, Expression):
            self.obj.set_body(body)

    def get_out_type(self):
        t = UI32_T.copy()
        t.raw.position = self.position
        return t

    def check_valid(self):
        if isinstance(self.obj, Expression):
            self.obj.check_valid()
            self.type = self.obj.get_out_type()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        if isinstance(self.obj, Expression):
            self.obj.replace_template(template2type)
        if self.type:
            self.type = TypeData.new_raw_templates(self.type.raw, template2type)

    def update_types(self):
        if isinstance(self.obj, Expression):
            self.obj.update_types()
        if self.type:
            self.type.update_types()

    def copy(self):
        return TypeidExpression(self.obj, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        c = self.copy()
        c.set_body(self.function_body)
        c.type = self.type
        return [], c


class TypestrExpression(Expression):
    def __init__(self, obj: Union[RawType, Expression], position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.obj = obj
        self.type: Optional[TypeData] = None
        if isinstance(self.obj, RawType):
            self.type = TypeData.new_raw(self.obj.src_pack, self.obj)

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        if isinstance(self.obj, Expression):
            self.obj.set_body(body)

    def get_out_type(self):
        if get_char_arr_t() is None:
            find_char_arr_t(self.function_body.function.data.package.storage)
        t = CHAR_ARR_T.copy()
        t.raw.position = self.position
        return t

    def check_valid(self):
        if isinstance(self.obj, Expression):
            self.obj.check_valid()
            self.type = self.obj.get_out_type()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        if isinstance(self.obj, Expression):
            self.obj.replace_template(template2type)
        if self.type:
            self.type = TypeData.new_raw_templates(self.type.raw, template2type)

    def update_types(self):
        if isinstance(self.obj, Expression):
            self.obj.update_types()
        if self.type:
            self.type.update_types()

    def copy(self):
        return TypestrExpression(self.obj, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        c = self.copy()
        c.set_body(self.function_body)
        c.type = self.type

        return [], c


class ArrayCreationExpression(Expression):
    def __init__(self, exprs: List[Expression], position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.exprs = exprs

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        for e in self.exprs:
            e.set_body(body)

    def get_out_type(self):
        if ARR_T is None:
            find_arr_t(self.function_body.function.data.package.storage)
        if self.exprs:
            t: TypeData = self.exprs[0].get_out_type()
            ret = ARR_T.copy()

            ret.raw.templates = [t.raw]
            ret.templates = [t]
            ret.update_types()

            return ret
        else:
            raise AnalyzerException(f"can't calculate type of empty array", self.position)

    def check_valid(self):
        for e in self.exprs:
            e.check_valid()
        if self.exprs:
            t = self.exprs[0].get_out_type()
            for e in self.exprs:
                if e.get_out_type() != t:
                    raise AnalyzerException(f"types of values in array are different (first is {t})", e.position)

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        for e in self.exprs:
            e.replace_template(template2type)

    def update_types(self):
        for e in self.exprs:
            e.update_types()

    def copy(self):
        return ArrayCreationExpression([e.copy() for e in self.exprs], self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        lines = []
        exprs = []

        for e in self.exprs:
            l, e = e.get_simplified()
            lines += l
            exprs.append(e)

        name = gen_variable_name(self.position)

        expr = ArrayCreationExpression(exprs, self.position)
        var = VariableCreationExpression(name, expr, self.get_out_type().raw, self.position)
        var.set_body(self.function_body)
        var.update_types()

        v = VariableExpression(name, self.position)
        v.set_body(self.function_body)
        v.update_types()

        return lines + [var], v


class VariableDestroyExpression(Expression):
    def __init__(self, var_name: str, position: Optional[Tuple[int, int, int, int]] = None):
        super().__init__(position)
        self.name = var_name
        self.function: Optional[FunctionData] = None

    def _find_function(self, v: VariableData):
        path = v.type.data.package.path

        type = v.type.copy()
        type.pointer_level += 1
        type.raw.pointer_level += 1
        type.gen_hash()

        arg_types = [type]

        funcs = find_function(self.function_body.function.data.package, path, "__destructor", [], arg_types,
                              allow_auto_pack=False)
        if len(funcs) > 1:
            fit = []
            functions = functions_by_path(path, self.function_body.function.data.package)
            fi = FunctionImage("__destructor", arg_types, [])
            for i in functions:
                if i == fi:
                    fit.append(i)
            raise AnalyzerException(
                f"it isn't possible to determine current function, variants: {', '.join([str(i) for i in fit])}",
                self.position)
        elif len(funcs) == 1:
            f = funcs[0]

            if f.is_template():
                temps = f.try_generate_template(arg_types)
                try:
                    self.function = f.apply_template(temps)
                except BadTemplateException:
                    raise AnalyzerException(f"can't generate template for function {str(f)}", self.position)
                try:
                    self.function.package.register(self.function)
                except KeyError:
                    pass
            else:
                self.function = f
        else:
            self.function = None

    def get_out_type(self):
        raise StateException

    def try_find_function(self):
        v = self.function_body.visibility_stack.find_variable(self.name)
        if v.type.pointer_level == 0 and self.function is None:
            self._find_function(v)

    def check_valid(self):
        v = self.function_body.visibility_stack.find_variable(self.name)
        if v is None:
            raise AnalyzerException(f"can't destroy non-existent variable {self.name}", self.position)
        else:
            try:
                self.function_body.visibility_stack.destroy_variable(self.name)
            except ValueError:
                raise AnalyzerException(f"can't destroy up-leveled variable {self.name}", self.position)
        self.try_find_function()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        pass

    def update_types(self):
        pass

    def copy(self):
        return VariableExpression(self.name, self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        raise StateException


class CopyExpression(Expression):
    def __init__(self, expr: Expression, position: Optional[Tuple[int, int, int, int]] = None):
        #if not (isinstance(expr, VariableExpression) or isinstance(expr, GetterExpression)):
        #    raise ValueError

        super().__init__(position)
        self.expr = expr
        self.function: Optional[FunctionData] = None

    def set_body(self, body: FunctionBody):
        super().set_body(body)
        self.expr.set_body(body)

    def _find_function(self):
        type: TypeData = self.expr.get_out_type().copy()
        type.pointer_level += 1
        type.raw.pointer_level += 1
        type.gen_hash()

        path = type.data.package.path

        arg_types = [type]

        funcs = find_function(self.function_body.function.data.package, path, "__copy", [], arg_types,
                              allow_auto_pack=False)

        if len(funcs) > 1:
            fit = []
            functions = functions_by_path(path, self.function_body.function.data.package)
            fi = FunctionImage("__copy", arg_types, [])
            for i in functions:
                if i == fi:
                    fit.append(i)
            raise AnalyzerException(
                f"it isn't possible to determine current function, variants: {', '.join([str(i) for i in fit])}",
                self.position)
        elif len(funcs) == 1:
            f = funcs[0]

            if f.is_template():
                temps = f.try_generate_template(arg_types)
                try:
                    self.function = f.apply_template(temps)
                except BadTemplateException:
                    raise AnalyzerException(f"can't generate template for function {str(f)}", self.position)
                try:
                    self.function.package.register(self.function)
                except KeyError:
                    pass
            else:
                self.function = f
        else:
            self.function = None

    def try_find_function(self):
        if self.expr.get_out_type().pointer_level == 0 and self.function is None:
            self._find_function()

    def get_out_type(self):
        if self.function:
            return self.function.type
        else:
            return self.expr.get_out_type()

    def check_valid(self):
        self.expr.check_valid()

        self.try_find_function()

    def replace_template(self, template2type: Dict[RawType, TypeData]):
        self.expr.replace_template(template2type)

    def update_types(self):
        self.expr.update_types()

    def copy(self):
        return VariableExpression(self.expr.copy(), self.position)

    def get_simplified(self) -> Tuple[List['Expression'], 'Expression']:
        return [], self
