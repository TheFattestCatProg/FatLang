from ply.lex import lex, TOKEN


class Lexer(object):
    literals = "[](){},.;:=!~"
    t_ignore = ' \t'
    func_modifiers = ['copy', 'top', 'in', 'out']
    access_modifiers = ['public', 'internal']  # internal - inside of curr file

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        print(f"Lexer error: illegal character {t.value[0]}")
        t.lexer.skip(1)

    reserved = {
        'if': 'IF',
        'else': 'ELSE',
        'while': 'WHILE',
        'for': 'FOR',
        'class': 'CLASS',
        'struct': 'STRUCT',
        'package': 'PACKAGE',
        'using': 'USING',
        'return': 'RETURN',
        'var': 'VAR',
        'interface': 'INTERFACE',
        'extern': 'EXTERN',
        'operator': 'OPERATOR',
        'unsafe': 'UNSAFE',
        'sizeof': 'SIZEOF',
        'typeid': 'TYPEID',
        'typestr': 'TYPESTR',
        'const': 'CONST',
    }

    bin_ops = ['PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'AND', 'OR', 'XOR', 'LS', 'GR', 'LE', 'GE', 'NE', 'EE', 'LSHIFT', 'RSHIFT',
               'PLUSEQ', 'MINUSEQ', 'TIMESEQ', 'DIVIDEEQ', 'MODEQ', 'ANDEQ', 'OREQ', 'XOREQ', 'LSHIFTEQ', 'RSHIFTEQ']
    tokens = ['ID', 'COMMENT', 'LCOMMENT', 'ACCMOD', 'FUNCMOD', 'NUM', 'FLOAT', 'INT', 'STR', 'BOOL', 'CHAR', 'BINOP', 'MACRO'] + bin_ops + list(reserved.values())

    t_FLOAT = r'((\d+\.\d+)|(\.\d+))(f32|f64)?'
    t_INT = r'((0[xX][0-9a-fA-F]+)|(0[bB][01]+)|(0[oO][0-7]+)|(\d+))(i32|f32|i64|f64|ui32|ui64|usize)?'
    t_STR = r'("([^\\\n]|(\\.))*?")'
    t_BOOL = r'true|false'
    t_CHAR = r"'(.| (\\[abfnrtv'\"\\?]) | (\\\d+) | (\\x\d+))'"
    t_MACRO = r'\#\S+'

    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_MOD = r'%'
    t_AND = r'&'
    t_OR = r'\|'
    t_XOR = r'\^'
    t_LSHIFT = r'<<'
    t_RSHIFT = r'>>'

    t_PLUSEQ = r'\+='
    t_MINUSEQ = r'-='
    t_TIMESEQ = r'\*='
    t_DIVIDEEQ = r'/='
    t_MODEQ = r'%='
    t_ANDEQ = r'&='
    t_OREQ = r'\|='
    t_XOREQ = r'\^='
    t_LSHIFTEQ = r'<<='
    t_RSHIFTEQ = r'>>='

    t_LS = r'<'
    t_GR = r'>'
    t_LE = r'<='
    t_GE = r'>='
    t_EE = r'=='
    t_NE = r'!='

    @TOKEN(r'//.*')
    def t_COMMENT(self, t):
        pass

    @TOKEN(r'/\*(.|\n)*?\*/')
    def t_LCOMMENT(self, t):
        t.lexer.lineno += t.value.count('\n')

    @TOKEN(t_FLOAT + "|" + t_INT)
    def t_NUM(self, t):
        if '.' in t.value:
            t.type = 'FLOAT'
        else:
            t.type = 'INT'
        return t

    @TOKEN(r'[a-zA-Z_][a-zA-Z_0-9]*')
    def t_ID(self, t):
        #if t.value in self.func_modifiers: t.type = 'FUNCMOD'
        if t.value in self.access_modifiers: t.type = 'ACCMOD'
        elif t.value in ['true', 'false']: t.type = 'BOOL'
        else: t.type = self.reserved.get(t.value, 'ID')
        return t

    def build(self, **kwargs):
        self.lexer = lex(module=self, **kwargs)

    def test(self, data):
        self.lexer.input(data)
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            print(tok)
