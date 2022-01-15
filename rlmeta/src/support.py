class VM:

    def __init__(self, code, rules):
        self.code = code
        self.rules = rules

    def run(self, start_rule, stream):
        self.action = SemanticAction(None)
        self.pc = self.rules[start_rule]
        self.call_backtrack_stack = []
        self.stream, self.stream_rest = (stream, None)
        self.pos, self.pos_rest = (0, tuple())
        self.scope, self.scope_rest = (None, None)
        self.latest_fail_message, self.latest_fail_pos = (None, tuple())
        self.memo = {}
        while True:
            result = self.pop_arg()(self)
            if result:
                return result

    def pop_arg(self):
        code = self.code[self.pc]
        self.pc += 1
        return code

def PUSH_SCOPE(vm):
    vm.scope_rest = (vm.scope, vm.scope_rest)
    vm.scope = {}

def POP_SCOPE(vm):
    vm.scope, vm.scope_rest = vm.scope_rest

def BACKTRACK(vm):
    vm.call_backtrack_stack.append((
        vm.pop_arg(), vm.stream, vm.stream_rest, vm.pos, vm.pos_rest, vm.scope, vm.scope_rest
    ))

def COMMIT(vm):
    vm.call_backtrack_stack.pop()
    vm.pc = vm.pop_arg()

def CALL(vm):
    CALL_(vm, vm.pop_arg())

def CALL_(vm, pc):
    key = (pc, vm.pos_rest+(vm.pos,))
    if key in vm.memo:
        if vm.memo[key][0] is None:
            FAIL_(vm, vm.memo[key][1])
        else:
            vm.action, vm.stream, vm.stream_rest, vm.pos, vm.pos_rest = vm.memo[key]
    else:
        vm.call_backtrack_stack.append((vm.pc, key))
        vm.pc = pc

def RETURN(vm):
    if not vm.call_backtrack_stack:
        return vm.action
    vm.pc, key = vm.call_backtrack_stack.pop()
    vm.memo[key] = (vm.action, vm.stream, vm.stream_rest, vm.pos, vm.pos_rest)

def MATCH(vm):
    object_description = vm.pop_arg()
    fn = vm.pop_arg()
    MATCH_(vm, fn, ("expected {}", object_description))

def MATCH_(vm, fn, message):
    if vm.pos >= len(vm.stream) or not fn(vm.stream[vm.pos]):
        FAIL_(vm, message)
    else:
        vm.action = SemanticAction(vm.stream[vm.pos])
        vm.pos += 1
        return True

def MATCH_CALL_RULE(vm):
    if MATCH_(vm, lambda x: x in vm.rules, ("expected rule name",)):
        CALL_(vm, vm.rules[vm.action.value])

def LIST_START(vm):
    vm.scope_rest = (vm.scope, vm.scope_rest)
    vm.scope = []

def LIST_APPEND(vm):
    vm.scope.append(vm.action)

def LIST_END(vm):
    vm.action = SemanticAction(vm.scope, lambda self: [x.eval(self.runtime) for x in self.value])
    vm.scope, vm.scope_rest = vm.scope_rest

def BIND(vm):
    vm.scope[vm.pop_arg()] = vm.action

def ACTION(vm):
    vm.action = SemanticAction(vm.scope, vm.pop_arg())

def PUSH_STREAM(vm):
    if vm.pos >= len(vm.stream) or not isinstance(vm.stream[vm.pos], list):
        FAIL_(vm, ("expected list",))
    else:
        vm.stream_rest = (vm.stream, vm.stream_rest)
        vm.pos_rest = vm.pos_rest + (vm.pos,)
        vm.stream = vm.stream[vm.pos]
        vm.pos = 0

def POP_STREAM(vm):
    if vm.pos < len(vm.stream):
        FAIL_(vm, ("expected end of list",))
    else:
        vm.stream, vm.stream_rest = vm.stream_rest
        vm.pos, vm.pos_rest = vm.pos_rest[-1], vm.pos_rest[:-1]
        vm.pos += 1

def FAIL(vm):
    FAIL_(vm, (vm.pop_arg(),))

def FAIL_(vm, fail_message):
    fail_pos = vm.pos_rest+(vm.pos,)
    if fail_pos >= vm.latest_fail_pos:
        vm.latest_fail_message = fail_message
        vm.latest_fail_pos = fail_pos
    call_backtrack_entry = tuple()
    while vm.call_backtrack_stack:
        call_backtrack_entry = vm.call_backtrack_stack.pop()
        if len(call_backtrack_entry) == 7:
            break
        else:
            vm.memo[call_backtrack_entry[1]] = (None, fail_message)
    if len(call_backtrack_entry) != 7:
        raise MatchError(
            vm.latest_fail_message[0].format(*vm.latest_fail_message[1:]),
            vm.latest_fail_pos[-1],
            vm.stream
        )
    (vm.pc, vm.stream, vm.stream_rest, vm.pos, vm.pos_rest, vm.scope, vm.scope_rest) = call_backtrack_entry

class SemanticAction(object):

    def __init__(self, value, fn=lambda self: self.value):
        self.value = value
        self.fn = fn

    def eval(self, runtime):
        self.runtime = runtime
        return self.fn(self)

    def bind(self, name, value, continuation):
        self.runtime = self.runtime.set(name, value)
        return continuation()

    def lookup(self, name):
        if name in self.value:
            return self.value[name].eval(self.runtime)
        else:
            return self.runtime[name]

class MatchError(Exception):

    def __init__(self, message, pos, stream):
        Exception.__init__(self)
        self.message = message
        self.pos = pos
        self.stream = stream

class Grammar(object):

    def run(self, rule, stream, runtime={}):
        return Runtime(self, dict(runtime, **{
            "label": Counter(),
            "indentprefix": "    ",
            "list": list,
            "dict": dict,
            "add": lambda x, y: x.append(y),
            "get": lambda x, y: x[y],
            "set": lambda x, y, z: x.__setitem__(y, z),
            "len": len,
            "repr": repr,
            "join": join,
        })).run(rule, stream)

class Runtime(dict):

    def __init__(self, grammar, values):
        dict.__init__(self, dict(values, run=self.run))
        self.grammar = grammar

    def set(self, key, value):
        return Runtime(self.grammar, dict(self, **{key: value}))

    def run(self, rule, stream):
        return VM(self.grammar.code, self.grammar.rules).run(rule, stream).eval(self)

class Counter(object):

    def __init__(self):
        self.value = 0

    def __call__(self):
        result = self.value
        self.value += 1
        return result

def splice(depth, item):
    if depth == 0:
        return [item]
    else:
        return concat([splice(depth-1, subitem) for subitem in item])

def concat(lists):
    return [x for xs in lists for x in xs]

def join(items, delimiter=""):
    return delimiter.join(
        join(item, delimiter) if isinstance(item, list) else str(item)
        for item in items
    )

def indent(text, prefix="    "):
    return "".join(prefix+line for line in text.splitlines(True))

def compile_chain(grammars, source):
    import sys
    import pprint
    for grammar, rule in grammars:
        try:
            source = grammar().run(rule, source)
        except MatchError as e:
            MARKER = "\033[0;31m<ERROR POSITION>\033[0m"
            if isinstance(e.stream, str):
                stream_string = e.stream[:e.pos] + MARKER + e.stream[e.pos:]
            else:
                stream_string = pprint.pformat(e.stream)
            sys.exit("ERROR: {}\nPOSITION: {}\nSTREAM:\n{}".format(
                e.message,
                e.pos,
                indent(stream_string)
            ))
    return source
