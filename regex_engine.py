from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union, List, Tuple, Dict, Set
from collections import deque
import sys
import time

sys.setrecursionlimit(50000)

MAX_STATES = 50000
MAX_BACKTRACK_STEPS = 200000
STATE_COUNT_LIMIT = 10000

IGNORECASE = 2
MULTILINE = 8


class RegexError(Exception):
    pass


class CatastrophicBacktrackError(RegexError):
    pass


@dataclass(frozen=True)
class Token:
    type: int
    value: str = ""
    pos: int = 0


(
    CHAR, DOT, STAR, PLUS, QUESTION, OR, LPAREN, RPAREN, LBRACKET, RBRACKET,
    CARET, DOLLAR, BACKREF, LBRACE, RBRACE, COMMA, COLON, EQUAL, EXCLAIM, LESS,
    GREAT, P, GREATER
) = range(23)


class Tokenizer:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0
        self.tokens: List[Token] = []

    def peek(self, offset: int = 0) -> Optional[str]:
        p = self.pos + offset
        if p < len(self.pattern):
            return self.pattern[p]
        return None

    def advance(self) -> str:
        ch = self.pattern[self.pos]
        self.pos += 1
        return ch

    def at_end(self) -> bool:
        return self.pos >= len(self.pattern)

    def handle_escape(self) -> Token:
        start_pos = self.pos
        self.advance()
        if self.at_end():
            raise RegexError(f"Trailing backslash at position {start_pos}")
        ch = self.advance()

        special_classes = {
            "d": "\\d", "w": "\\w", "s": "\\s",
            "D": "\\D", "W": "\\W", "S": "\\S",
            "b": "\\b", "B": "\\B", "n": "\n",
            "t": "\t", "r": "\r",
        }
        if ch in special_classes:
            return Token(type=CHAR, value=special_classes[ch], pos=start_pos)

        if ch.isdigit():
            num = ch
            while not self.at_end() and self.peek().isdigit():
                num += self.advance()
            return Token(type=BACKREF, value=num, pos=start_pos)

        specials = ".*+?|()[]{}^$\\-=!,<:"
        if ch in specials:
            return Token(type=CHAR, value=ch, pos=start_pos)
        return Token(type=CHAR, value=ch, pos=start_pos)

    def handle_character_class(self) -> List[Token]:
        start_pos = self.pos
        tokens = [Token(type=LBRACKET, value="[", pos=start_pos)]
        self.advance()

        if not self.at_end() and self.peek() == "^":
            tokens.append(Token(type=CARET, value="^", pos=self.pos))
            self.advance()

        if not self.at_end() and self.peek() == "]":
            tokens.append(Token(type=CHAR, value="]", pos=self.pos))
            self.advance()

        while not self.at_end() and self.peek() != "]":
            if self.peek() == "\\":
                tokens.append(self.handle_escape())
            else:
                ch = self.advance()
                if ch == "-" and not self.at_end() and self.peek() != "]" and tokens and tokens[-1].type == CHAR:
                    tokens.append(Token(type=CHAR, value="-", pos=self.pos))
                    if not self.at_end() and self.peek() != "]":
                        if self.peek() == "\\":
                            tokens.append(self.handle_escape())
                        else:
                            next_ch = self.advance()
                            tokens.append(Token(type=CHAR, value=next_ch, pos=self.pos))
                else:
                    tokens.append(Token(type=CHAR, value=ch, pos=self.pos))

        if self.at_end():
            raise RegexError(f"Unterminated character class at position {self.pos}")
        self.advance()
        tokens.append(Token(type=RBRACKET, value="]", pos=self.pos))
        return tokens

    def tokenize(self) -> List[Token]:
        while not self.at_end():
            ch = self.peek()
            start_p = self.pos

            if ch == "\\":
                self.tokens.append(self.handle_escape())
            elif ch == ".":
                self.tokens.append(Token(type=DOT, value=".", pos=start_p))
                self.advance()
            elif ch == "*":
                self.tokens.append(Token(type=STAR, value="*", pos=start_p))
                self.advance()
            elif ch == "+":
                self.tokens.append(Token(type=PLUS, value="+", pos=start_p))
                self.advance()
            elif ch == "?":
                self.tokens.append(Token(type=QUESTION, value="?", pos=start_p))
                self.advance()
            elif ch == "|":
                self.tokens.append(Token(type=OR, value="|", pos=start_p))
                self.advance()
            elif ch == "(":
                self.tokens.append(Token(type=LPAREN, value="(", pos=start_p))
                self.advance()
                if not self.at_end() and self.peek() == "?":
                    self.advance()
                    if not self.at_end() and self.peek() == ":":
                        self.tokens.append(Token(type=COLON, value=":", pos=self.pos))
                        self.advance()
                    elif not self.at_end() and self.peek() == "=":
                        self.tokens.append(Token(type=EQUAL, value="=", pos=self.pos))
                        self.advance()
                    elif not self.at_end() and self.peek() == "!":
                        self.tokens.append(Token(type=EXCLAIM, value="!", pos=self.pos))
                        self.advance()
                    elif not self.at_end() and self.peek() == "P":
                        self.tokens.append(Token(type=P, value="P", pos=self.pos))
                        self.advance()
                        if not self.at_end() and self.peek() == "<":
                            self.tokens.append(Token(type=LESS, value="<", pos=self.pos))
                            self.advance()
                            name = ""
                            while not self.at_end() and self.peek() != ">":
                                name += self.advance()
                            if name:
                                self.tokens.append(Token(type=CHAR, value=name, pos=self.pos))
                            if not self.at_end() and self.peek() == ">":
                                self.tokens.append(Token(type=GREATER, value=">", pos=self.pos))
                                self.advance()
                    elif not self.at_end() and self.peek() == "<":
                        self.tokens.append(Token(type=LESS, value="<", pos=self.pos))
                        self.advance()
                        if not self.at_end() and self.peek() == "=":
                            self.tokens.append(Token(type=EQUAL, value="=", pos=self.pos))
                            self.advance()
                        elif not self.at_end() and self.peek() == "!":
                            self.tokens.append(Token(type=EXCLAIM, value="!", pos=self.pos))
                            self.advance()
            elif ch == ")":
                self.tokens.append(Token(type=RPAREN, value=")", pos=start_p))
                self.advance()
            elif ch == "[":
                self.tokens.extend(self.handle_character_class())
            elif ch == "^":
                self.tokens.append(Token(type=CARET, value="^", pos=start_p))
                self.advance()
            elif ch == "$":
                self.tokens.append(Token(type=DOLLAR, value="$", pos=start_p))
                self.advance()
            elif ch == "{":
                self.tokens.append(Token(type=LBRACE, value="{", pos=start_p))
                self.advance()
                while not self.at_end() and self.peek() != "}":
                    if self.peek() == ",":
                        self.tokens.append(Token(type=COMMA, value=",", pos=self.pos))
                        self.advance()
                    elif self.peek().isdigit():
                        num = ""
                        while not self.at_end() and self.peek().isdigit():
                            num += self.advance()
                        self.tokens.append(Token(type=CHAR, value=num, pos=self.pos))
                    else:
                        self.advance()
                if not self.at_end() and self.peek() == "}":
                    self.tokens.append(Token(type=RBRACE, value="}", pos=self.pos))
                    self.advance()
            else:
                self.tokens.append(Token(type=CHAR, value=ch, pos=start_p))
                self.advance()

        return self.tokens


class ASTNode:
    pass


@dataclass
class CharNode(ASTNode):
    value: str


@dataclass
class DotNode(ASTNode):
    pass


@dataclass
class CharClassNode(ASTNode):
    ranges: List[Tuple[str, str]]
    negate: bool = False


@dataclass
class ConcatNode(ASTNode):
    left: ASTNode
    right: ASTNode


@dataclass
class AltNode(ASTNode):
    left: ASTNode
    right: ASTNode


@dataclass
class StarNode(ASTNode):
    child: ASTNode
    greedy: bool = True


@dataclass
class PlusNode(ASTNode):
    child: ASTNode
    greedy: bool = True


@dataclass
class QuestionNode(ASTNode):
    child: ASTNode
    greedy: bool = True


@dataclass
class RepeatNode(ASTNode):
    child: ASTNode
    min: int
    max: int
    greedy: bool = True


@dataclass
class CaptureGroupNode(ASTNode):
    child: ASTNode
    group_num: int
    group_name: Optional[str] = None


@dataclass
class NonCaptureGroupNode(ASTNode):
    child: ASTNode


@dataclass
class LookaheadNode(ASTNode):
    child: ASTNode
    positive: bool


@dataclass
class LookbehindNode(ASTNode):
    child: ASTNode
    positive: bool


@dataclass
class BackRefNode(ASTNode):
    group_num: int


@dataclass
class AssertionNode(ASTNode):
    kind: str


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.group_counter = 0
        self.group_name_map: Dict[str, int] = {}
        self.has_backref = False
        self.has_assertion = False
        self.has_lookaround = False
        self.has_non_greedy = False

    def peek(self, offset: int = 0) -> Optional[Token]:
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return None

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def parse(self) -> ASTNode:
        result = self.parse_alternation()
        if not self.at_end():
            tok = self.peek()
            raise RegexError(f"Unexpected token at position {tok.pos}")
        return result

    def parse_alternation(self) -> ASTNode:
        left = self.parse_concatenation()
        while not self.at_end() and self.peek().type == OR:
            self.advance()
            right = self.parse_concatenation()
            left = AltNode(left=left, right=right)
        return left

    def parse_concatenation(self) -> ASTNode:
        terms: List[ASTNode] = []
        while not self.at_end():
            tok = self.peek()
            if tok.type in (RPAREN, OR):
                break
            terms.append(self.parse_assertion_or_term())

        if not terms:
            return CharNode(value="")
        result = terms[0]
        for t in terms[1:]:
            result = ConcatNode(left=result, right=t)
        return result

    def parse_assertion_or_term(self) -> ASTNode:
        tok = self.peek()
        if tok.type == CARET:
            self.has_assertion = True
            self.advance()
            return AssertionNode(kind="start")
        if tok.type == DOLLAR:
            self.has_assertion = True
            self.advance()
            return AssertionNode(kind="end")
        if tok.type == CHAR and tok.value == "\\b":
            self.has_assertion = True
            self.advance()
            return AssertionNode(kind="word_boundary")
        if tok.type == CHAR and tok.value == "\\B":
            self.has_assertion = True
            self.advance()
            return AssertionNode(kind="non_word_boundary")
        return self.parse_quantified()

    def parse_quantified(self) -> ASTNode:
        node = self.parse_atom()
        if not self.at_end():
            tok = self.peek()
            if tok.type == STAR:
                self.advance()
                greedy = True
                if not self.at_end() and self.peek().type == QUESTION:
                    self.advance()
                    greedy = False
                    self.has_non_greedy = True
                return StarNode(child=node, greedy=greedy)
            elif tok.type == PLUS:
                self.advance()
                greedy = True
                if not self.at_end() and self.peek().type == QUESTION:
                    self.advance()
                    greedy = False
                    self.has_non_greedy = True
                return PlusNode(child=node, greedy=greedy)
            elif tok.type == QUESTION:
                self.advance()
                greedy = True
                if not self.at_end() and self.peek().type == QUESTION:
                    self.advance()
                    greedy = False
                    self.has_non_greedy = True
                return QuestionNode(child=node, greedy=greedy)
            elif tok.type == LBRACE:
                return self.parse_brace_repeat(node)
        return node

    def parse_brace_repeat(self, node: ASTNode) -> ASTNode:
        self.advance()
        min_val = None
        max_val = None

        if not self.at_end() and self.peek().type == CHAR and self.peek().value.isdigit():
            min_val = int(self.advance().value)

        if not self.at_end() and self.peek().type == COMMA:
            self.advance()
            if not self.at_end() and self.peek().type == CHAR and self.peek().value.isdigit():
                max_val = int(self.advance().value)
        else:
            max_val = min_val

        while not self.at_end() and self.peek().type != RBRACE:
            self.advance()
        if not self.at_end():
            self.advance()

        greedy = True
        if not self.at_end() and self.peek().type == QUESTION:
            self.advance()
            greedy = False
            self.has_non_greedy = True

        if min_val is None:
            min_val = 0
        if max_val is None:
            max_val = -1

        return RepeatNode(child=node, min=min_val, max=max_val, greedy=greedy)

    def parse_atom(self) -> ASTNode:
        tok = self.peek()

        if tok.type == DOT:
            self.advance()
            return DotNode()

        if tok.type == CHAR:
            self.advance()
            if tok.value in ("\\d", "\\w", "\\s", "\\D", "\\W", "\\S"):
                return CharNode(value=tok.value)
            return CharNode(value=tok.value)

        if tok.type == BACKREF:
            self.has_backref = True
            num = int(tok.value)
            self.advance()
            return BackRefNode(group_num=num)

        if tok.type == LBRACKET:
            return self.parse_character_class()

        if tok.type == LPAREN:
            return self.parse_group()

        raise RegexError(f"Unexpected token at position {tok.pos}")

    def parse_character_class(self) -> ASTNode:
        self.advance()
        negate = False
        if not self.at_end() and self.peek().type == CARET:
            negate = True
            self.advance()

        ranges: List[Tuple[str, str]] = []
        while not self.at_end() and self.peek().type != RBRACKET:
            tok = self.advance()
            first = tok.value

            if not self.at_end() and self.peek().type == CHAR and self.peek().value == "-":
                self.advance()
                if not self.at_end() and self.peek().type != RBRACKET:
                    last = self.advance().value
                    ranges.append((first, last))
                else:
                    ranges.append((first, first))
                    ranges.append(("-", "-"))
            else:
                ranges.append((first, first))

        if not self.at_end() and self.peek().type == RBRACKET:
            self.advance()

        return CharClassNode(ranges=ranges, negate=negate)

    def parse_group(self) -> ASTNode:
        self.advance()
        non_capture = False
        lookahead_positive = None
        lookbehind_positive = None
        group_name = None

        if not self.at_end() and self.peek().type == P:
            self.advance()
            if not self.at_end() and self.peek().type == LESS:
                self.advance()
                if not self.at_end() and self.peek().type == CHAR:
                    group_name = self.advance().value
                if not self.at_end() and self.peek().type == GREATER:
                    self.advance()

        if not self.at_end() and self.peek().type == COLON:
            non_capture = True
            self.advance()
        elif not self.at_end() and self.peek().type == EQUAL:
            lookahead_positive = True
            self.advance()
        elif not self.at_end() and self.peek().type == EXCLAIM:
            lookahead_positive = False
            self.advance()
        elif not self.at_end() and self.peek().type == LESS:
            self.advance()
            if not self.at_end() and self.peek().type == EQUAL:
                lookbehind_positive = True
                self.advance()
            elif not self.at_end() and self.peek().type == EXCLAIM:
                lookbehind_positive = False
                self.advance()

        child = self.parse_alternation()

        if not self.at_end() and self.peek().type == RPAREN:
            self.advance()

        if lookahead_positive is not None:
            self.has_assertion = True
            self.has_lookaround = True
            return LookaheadNode(child=child, positive=lookahead_positive)
        if lookbehind_positive is not None:
            self.has_assertion = True
            self.has_lookaround = True
            return LookbehindNode(child=child, positive=lookbehind_positive)
        if non_capture:
            return NonCaptureGroupNode(child=child)

        self.group_counter += 1
        node = CaptureGroupNode(child=child, group_num=self.group_counter, group_name=group_name)
        if group_name is not None:
            self.group_name_map[group_name] = self.group_counter
        return node


@dataclass
class NFAState:
    id: int
    transitions: Dict[str, List[NFAState]] = field(default_factory=dict)
    epsilon: List[NFAState] = field(default_factory=list)
    is_final: bool = False
    capture_start: Optional[int] = None
    capture_end: Optional[int] = None
    assertion: Optional[str] = None
    backref: Optional[int] = None
    lookahead_nfa: Optional["NFA"] = None
    lookahead_positive: bool = True
    lookbehind_nfa: Optional["NFA"] = None
    lookbehind_positive: bool = True


class NFA:
    def __init__(self, start: NFAState, end: NFAState):
        self.start = start
        self.end = end


class NFAStateCounter:
    def __init__(self):
        self.count = 0

    def new(self) -> NFAState:
        if self.count >= STATE_COUNT_LIMIT:
            raise RegexError(f"Too many NFA states (limit: {STATE_COUNT_LIMIT})")
        s = NFAState(id=self.count)
        self.count += 1
        return s


def add_epsilon(from_state: NFAState, to_state: NFAState):
    if to_state not in from_state.epsilon:
        from_state.epsilon.append(to_state)


def add_transition(from_state: NFAState, char: str, to_state: NFAState):
    if char not in from_state.transitions:
        from_state.transitions[char] = []
    if to_state not in from_state.transitions[char]:
        from_state.transitions[char].append(to_state)


def build_nfa(node: ASTNode, counter: NFAStateCounter) -> NFA:
    if isinstance(node, CharNode):
        start = counter.new()
        end = counter.new()
        add_transition(start, node.value, end)
        return NFA(start, end)

    if isinstance(node, DotNode):
        start = counter.new()
        end = counter.new()
        add_transition(start, "__DOT__", end)
        return NFA(start, end)

    if isinstance(node, CharClassNode):
        start = counter.new()
        end = counter.new()
        for r in node.ranges:
            a, b = r
            if len(a) == 1 and len(b) == 1:
                key = f"__CC{'N' if node.negate else ''}__{a}__{b}__"
            else:
                key = f"__CC{'N' if node.negate else ''}__{a}__{a}__"
            add_transition(start, key, end)
        return NFA(start, end)

    if isinstance(node, ConcatNode):
        left_nfa = build_nfa(node.left, counter)
        right_nfa = build_nfa(node.right, counter)
        add_epsilon(left_nfa.end, right_nfa.start)
        return NFA(left_nfa.start, right_nfa.end)

    if isinstance(node, AltNode):
        start = counter.new()
        end = counter.new()
        left_nfa = build_nfa(node.left, counter)
        right_nfa = build_nfa(node.right, counter)
        add_epsilon(start, left_nfa.start)
        add_epsilon(start, right_nfa.start)
        add_epsilon(left_nfa.end, end)
        add_epsilon(right_nfa.end, end)
        return NFA(start, end)

    if isinstance(node, StarNode):
        start = counter.new()
        end = counter.new()
        child_nfa = build_nfa(node.child, counter)
        if node.greedy:
            add_epsilon(start, child_nfa.start)
            add_epsilon(child_nfa.end, child_nfa.start)
            add_epsilon(child_nfa.end, end)
            add_epsilon(start, end)
        else:
            add_epsilon(start, end)
            add_epsilon(start, child_nfa.start)
            add_epsilon(child_nfa.end, end)
            add_epsilon(child_nfa.end, child_nfa.start)
        return NFA(start, end)

    if isinstance(node, PlusNode):
        start = counter.new()
        end = counter.new()
        child_nfa = build_nfa(node.child, counter)
        add_epsilon(start, child_nfa.start)
        if node.greedy:
            add_epsilon(child_nfa.end, child_nfa.start)
            add_epsilon(child_nfa.end, end)
        else:
            add_epsilon(child_nfa.end, end)
            add_epsilon(child_nfa.end, child_nfa.start)
        return NFA(start, end)

    if isinstance(node, QuestionNode):
        start = counter.new()
        end = counter.new()
        child_nfa = build_nfa(node.child, counter)
        if node.greedy:
            add_epsilon(start, child_nfa.start)
            add_epsilon(child_nfa.end, end)
            add_epsilon(start, end)
        else:
            add_epsilon(start, end)
            add_epsilon(start, child_nfa.start)
            add_epsilon(child_nfa.end, end)
        return NFA(start, end)

    if isinstance(node, RepeatNode):
        if node.max == -1:
            prefix = build_exact_n(node.child, node.min, counter)
            start = counter.new()
            end = counter.new()
            add_epsilon(start, prefix.start)
            add_epsilon(prefix.end, end)
            child_nfa = build_nfa(node.child, counter)
            if node.greedy:
                add_epsilon(prefix.end, child_nfa.start)
                add_epsilon(child_nfa.end, child_nfa.start)
                add_epsilon(child_nfa.end, end)
            else:
                add_epsilon(prefix.end, child_nfa.start)
                add_epsilon(child_nfa.end, end)
                add_epsilon(child_nfa.end, child_nfa.start)
            return NFA(start, end)
        else:
            total_min = node.min
            total_max = node.max
            parts = []
            for _ in range(total_min):
                parts.append(build_nfa(node.child, counter))
            for _ in range(total_max - total_min):
                parts.append(build_nfa(QuestionNode(child=node.child, greedy=node.greedy), counter))
            if not parts:
                s = counter.new()
                e = counter.new()
                add_epsilon(s, e)
                return NFA(s, e)
            result = parts[0]
            for p in parts[1:]:
                add_epsilon(result.end, p.start)
                result = NFA(result.start, p.end)
            return result

    if isinstance(node, CaptureGroupNode):
        child_nfa = build_nfa(node.child, counter)
        child_nfa.start.capture_start = node.group_num
        child_nfa.end.capture_end = node.group_num
        return child_nfa

    if isinstance(node, NonCaptureGroupNode):
        return build_nfa(node.child, counter)

    if isinstance(node, LookaheadNode):
        start = counter.new()
        end = counter.new()
        child_nfa = build_nfa(node.child, counter)
        start.lookahead_nfa = child_nfa
        start.lookahead_positive = node.positive
        add_epsilon(start, end)
        return NFA(start, end)

    if isinstance(node, LookbehindNode):
        start = counter.new()
        end = counter.new()
        child_nfa = build_nfa(node.child, counter)
        start.lookbehind_nfa = child_nfa
        start.lookbehind_positive = node.positive
        add_epsilon(start, end)
        return NFA(start, end)

    if isinstance(node, BackRefNode):
        start = counter.new()
        end = counter.new()
        start.backref = node.group_num
        add_epsilon(start, end)
        return NFA(start, end)

    if isinstance(node, AssertionNode):
        start = counter.new()
        end = counter.new()
        start.assertion = node.kind
        add_epsilon(start, end)
        return NFA(start, end)

    raise RegexError(f"Unknown AST node: {type(node)}")


def build_exact_n(child: ASTNode, n: int, counter: NFAStateCounter) -> NFA:
    if n == 0:
        start = counter.new()
        end = counter.new()
        add_epsilon(start, end)
        return NFA(start, end)
    first = build_nfa(child, counter)
    result = first
    for _ in range(n - 1):
        next_nfa = build_nfa(child, counter)
        add_epsilon(result.end, next_nfa.start)
        result = NFA(result.start, next_nfa.end)
    return result


def collect_state_map(start: NFAState) -> Dict[int, NFAState]:
    state_map: Dict[int, NFAState] = {}
    queue = deque([start])
    visited = set()
    while queue:
        s = queue.popleft()
        if s.id in visited:
            continue
        visited.add(s.id)
        state_map[s.id] = s
        for ep in s.epsilon:
            if ep.id not in visited:
                queue.append(ep)
        for char, targets in s.transitions.items():
            for t in targets:
                if t.id not in visited:
                    queue.append(t)
    return state_map


def is_word_char(ch: Optional[str]) -> bool:
    if ch is None or ch == "":
        return False
    return ch.isalnum() or ch == "_"


def matches_special(special: str, ch: str) -> bool:
    if special == "__DOT__":
        return ch != "\n"
    if special == "\\d":
        return ch.isdigit()
    if special == "\\w":
        return ch.isalnum() or ch == "_"
    if special == "\\s":
        return ch.isspace()
    if special == "\\D":
        return not ch.isdigit()
    if special == "\\W":
        return not (ch.isalnum() or ch == "_")
    if special == "\\S":
        return not ch.isspace()
    return False


def _matches_transition_inner(trans_char: str, ch: str) -> bool:
    if trans_char.startswith("__CC"):
        negate = trans_char.startswith("__CCN")
        parts = trans_char.split("__")
        if len(parts) >= 5:
            a = parts[2]
            b = parts[3]
            if len(a) == 1 and len(b) == 1:
                matched = (a <= ch <= b)
            else:
                matched = (ch == a or ch == b)
            return (not matched) if negate else matched
        return False
    if trans_char.startswith("__"):
        return matches_special(trans_char, ch)
    if trans_char.startswith("\\") and len(trans_char) == 2:
        return matches_special(trans_char, ch)
    return trans_char == ch


def matches_transition(trans_char: str, ch: str, flags: int = 0) -> bool:
    if trans_char.startswith("__CC") and (flags & IGNORECASE):
        negate = trans_char.startswith("__CCN")
        parts = trans_char.split("__")
        if len(parts) >= 5:
            a = parts[2]
            b = parts[3]
            def _cc_pos(c):
                if len(a) == 1 and len(b) == 1:
                    return a <= c <= b
                return c == a or c == b
            pos_orig = _cc_pos(ch)
            alt_ch = ch.lower() if ch.isupper() else ch.upper() if ch.islower() else ch
            pos_alt = _cc_pos(alt_ch) if alt_ch != ch else pos_orig
            pos_match = pos_orig or pos_alt
            return (not pos_match) if negate else pos_match
        return False
    result = _matches_transition_inner(trans_char, ch)
    if result:
        return True
    if flags & IGNORECASE:
        alt_ch = ch.lower() if ch.isupper() else ch.upper() if ch.islower() else ch
        if alt_ch != ch:
            return _matches_transition_inner(trans_char, alt_ch)
    return False


@dataclass
class BacktrackCtx:
    text: str
    state_map: Dict[int, NFAState]
    step_count: int = 0
    steps_limit: int = MAX_BACKTRACK_STEPS

    def step(self):
        self.step_count += 1
        if self.step_count > self.steps_limit:
            raise CatastrophicBacktrackError(
                f"Exceeded backtrack step limit ({self.steps_limit}). Possible ReDoS."
            )


class MatchResult:
    def __init__(self, matched: bool, start: int = 0, end: int = 0,
                 groups: Optional[Dict[int, str]] = None):
        self.matched = matched
        self.start = start
        self.end = end
        self.groups = groups or {}
        self.text = ""

    def group(self, idx: int = 0) -> Optional[str]:
        if idx == 0 and self.matched:
            return self.text[self.start:self.end]
        return self.groups.get(idx)

    def __bool__(self):
        return self.matched

    def __repr__(self):
        if not self.matched:
            return "<MatchResult: no match>"
        grps = {k: v for k, v in self.groups.items()}
        grps[0] = self.text[self.start:self.end] if self.matched else ""
        return f"<MatchResult: {grps}>"


def check_assertion_simple(kind: str, text: str, pos: int, flags: int = 0) -> bool:
    if kind == "start":
        if pos == 0:
            return True
        if flags & MULTILINE and pos > 0 and text[pos - 1] == '\n':
            return True
        return False
    if kind == "end":
        if pos == len(text):
            return True
        if flags & MULTILINE and pos < len(text) and text[pos] == '\n':
            return True
        return False
    if kind == "word_boundary":
        prev = text[pos - 1] if pos > 0 else None
        curr = text[pos] if pos < len(text) else None
        return is_word_char(prev) != is_word_char(curr)
    if kind == "non_word_boundary":
        prev = text[pos - 1] if pos > 0 else None
        curr = text[pos] if pos < len(text) else None
        return is_word_char(prev) == is_word_char(curr)
    return True


def try_match_lookahead(nfa: NFA, text: str, pos: int, state_map: Dict[int, NFAState], flags: int = 0) -> bool:
    visited: Set[Tuple[int, int]] = set()
    stack = [(nfa.start.id, pos)]

    while stack:
        sid, p = stack.pop()
        key = (sid, p)
        if key in visited:
            continue
        visited.add(key)

        state = state_map.get(sid)
        if state is None:
            continue

        if sid == nfa.end.id:
            return True

        if state.capture_start is not None or state.capture_end is not None:
            pass

        if state.assertion:
            if not check_assertion_simple(state.assertion, text, p, flags):
                continue

        if state.lookahead_nfa is not None:
            ok = try_match_lookahead(state.lookahead_nfa, text, p, collect_state_map(state.lookahead_nfa.start), flags)
            if state.lookahead_positive and not ok:
                continue
            if (not state.lookahead_positive) and ok:
                continue

        for ep in state.epsilon:
            stack.append((ep.id, p))

        if p < len(text):
            ch = text[p]
            for trans_char, targets in state.transitions.items():
                if matches_transition(trans_char, ch, flags):
                    for t in targets:
                        stack.append((t.id, p + 1))

    return False


def try_match_lookbehind(nfa: NFA, text: str, pos: int, state_map: Dict[int, NFAState], flags: int = 0) -> bool:
    for start_p in range(pos, -1, -1):
        if try_match_exact(nfa, text, start_p, pos, state_map, flags):
            return True
    return False


def try_match_exact(nfa: NFA, text: str, start_pos: int, end_pos: int,
                    state_map: Dict[int, NFAState], flags: int = 0) -> bool:
    visited: Set[Tuple[int, int]] = set()
    stack = [(nfa.start.id, start_pos)]

    while stack:
        sid, p = stack.pop()
        key = (sid, p)
        if key in visited:
            continue
        visited.add(key)

        if len(visited) > MAX_STATES:
            return False

        state = state_map.get(sid)
        if state is None:
            continue

        if sid == nfa.end.id and p == end_pos:
            return True

        if state.assertion:
            if not check_assertion_simple(state.assertion, text, p, flags):
                continue

        for ep in state.epsilon:
            stack.append((ep.id, p))

        if p < len(text):
            ch = text[p]
            for trans_char, targets in state.transitions.items():
                if matches_transition(trans_char, ch, flags):
                    for t in targets:
                        stack.append((t.id, p + 1))

    return False


def backtrack_search(text: str, nfa: NFA, start_pos: int,
                     state_map: Dict[int, NFAState], flags: int = 0) -> Optional[Tuple[int, Dict[int, Tuple[int, int]]]]:
    ctx = BacktrackCtx(text=text, state_map=state_map)

    initial_groups: Dict[int, Tuple[int, int]] = {}

    best_result: Optional[Tuple[int, Dict[int, Tuple[int, int]]]] = None

    def recurse(sid: int, pos: int, groups: Dict[int, Tuple[int, int]]) -> Optional[Tuple[int, Dict[int, Tuple[int, int]]]]:
        nonlocal best_result
        ctx.step()

        if sid == nfa.end.id:
            return (pos, dict(groups))

        state = state_map.get(sid)
        if state is None:
            return None

        new_groups = dict(groups)

        if state.capture_start is not None and state.capture_start > 0:
            gn = state.capture_start
            existing = new_groups.get(gn)
            if existing:
                new_groups[gn] = (pos, existing[1])
            else:
                new_groups[gn] = (pos, pos)

        if state.capture_end is not None and state.capture_end > 0:
            gn = state.capture_end
            existing = new_groups.get(gn)
            if existing:
                new_groups[gn] = (existing[0], pos)
            else:
                new_groups[gn] = (pos, pos)

        if state.assertion:
            if not check_assertion_simple(state.assertion, text, pos, flags):
                return None

        if state.lookahead_nfa is not None:
            lm = collect_state_map(state.lookahead_nfa.start)
            ok = try_match_lookahead(state.lookahead_nfa, text, pos, lm, flags)
            if state.lookahead_positive and not ok:
                return None
            if (not state.lookahead_positive) and ok:
                return None

        if state.lookbehind_nfa is not None:
            lm = collect_state_map(state.lookbehind_nfa.start)
            ok = try_match_lookbehind(state.lookbehind_nfa, text, pos, lm, flags)
            if state.lookbehind_positive and not ok:
                return None
            if (not state.lookbehind_positive) and ok:
                return None

        if state.backref is not None:
            bn = state.backref
            if bn in new_groups:
                gs, ge = new_groups[bn]
                expected = text[gs:ge]
                advance = len(expected)
                captured = text[pos:pos + advance]
                if captured == expected or ((flags & IGNORECASE) and captured.lower() == expected.lower()):
                    for ep in state.epsilon:
                        result = recurse(ep.id, pos + advance, new_groups)
                        if result is not None:
                            return result
                return None
            else:
                for ep in state.epsilon:
                    result = recurse(ep.id, pos, new_groups)
                    if result is not None:
                        return result
                return None

        for ep in state.epsilon:
            result = recurse(ep.id, pos, new_groups)
            if result is not None:
                return result

        if pos < len(text):
            ch = text[pos]
            for trans_char, targets in state.transitions.items():
                if matches_transition(trans_char, ch, flags):
                    for t in targets:
                        result = recurse(t.id, pos + 1, new_groups)
                        if result is not None:
                            return result

        return None

    return recurse(nfa.start.id, start_pos, initial_groups)


class Regex:
    def __init__(self, pattern: str, flags: int = 0):
        self.pattern = pattern
        self.flags = flags
        tokenizer = Tokenizer(pattern)
        self.tokens = tokenizer.tokenize()
        self.parser = Parser(self.tokens)
        self.ast = self.parser.parse()
        counter = NFAStateCounter()
        self.nfa = build_nfa(self.ast, counter)
        self.nfa.end.is_final = True
        self.state_map = collect_state_map(self.nfa.start)
        self.num_groups = self.parser.group_counter
        self.group_name_map = self.parser.group_name_map
        self.needs_backtrack = (
            self.parser.has_backref
            or self.parser.has_lookaround
            or self.parser.has_non_greedy
        )

    def search(self, text: str) -> Optional[MatchResult]:
        for i in range(len(text) + 1):
            result = self._match_at(text, i)
            if result is not None:
                return result
        return None

    def match(self, text: str) -> Optional[MatchResult]:
        return self._match_at(text, 0)

    def fullmatch(self, text: str) -> Optional[MatchResult]:
        result = self._match_at(text, 0)
        if result is not None and result.end == len(text):
            return result
        return None

    def findall(self, text: str) -> List:
        results = []
        i = 0
        while i <= len(text):
            result = self._match_at(text, i)
            if result is not None:
                if self.num_groups == 0:
                    results.append(text[result.start:result.end])
                elif self.num_groups == 1:
                    results.append(result.groups.get(1, ""))
                else:
                    grp = tuple(result.groups.get(j, "") for j in range(1, self.num_groups + 1))
                    results.append(grp)
                if result.end > i:
                    i = result.end
                else:
                    i += 1
            else:
                i += 1
        return results

    def _parse_replacement(self, replacement: str, groups: Dict[int, str]) -> str:
        result = []
        i = 0
        while i < len(replacement):
            if replacement[i] == '\\' and i + 1 < len(replacement):
                next_ch = replacement[i + 1]
                if next_ch.isdigit():
                    num_str = next_ch
                    i += 2
                    while i < len(replacement) and replacement[i].isdigit():
                        num_str += replacement[i]
                        i += 1
                    num = int(num_str)
                    result.append(groups.get(num, ''))
                elif next_ch == 'g' and i + 2 < len(replacement) and replacement[i + 2] == '<':
                    i += 3
                    name = ''
                    while i < len(replacement) and replacement[i] != '>':
                        name += replacement[i]
                        i += 1
                    if i < len(replacement):
                        i += 1
                    if name.isdigit():
                        result.append(groups.get(int(name), ''))
                    else:
                        group_num = self.group_name_map.get(name)
                        if group_num is not None:
                            result.append(groups.get(group_num, ''))
                elif next_ch == '\\':
                    result.append('\\')
                    i += 2
                else:
                    result.append(next_ch)
                    i += 2
            else:
                result.append(replacement[i])
                i += 1
        return ''.join(result)

    def sub(self, replacement: str, text: str, count: int = 0) -> str:
        result = []
        pos = 0
        num_subs = 0
        while pos <= len(text):
            match_obj = None
            for i in range(pos, len(text) + 1):
                match_obj = self._match_at(text, i)
                if match_obj is not None:
                    break
            if match_obj is None:
                break
            result.append(text[pos:match_obj.start])
            groups = dict(match_obj.groups)
            groups[0] = text[match_obj.start:match_obj.end]
            result.append(self._parse_replacement(replacement, groups))
            num_subs += 1
            if match_obj.end > pos:
                pos = match_obj.end
            else:
                if pos < len(text):
                    result.append(text[pos])
                pos = match_obj.end + 1
            if count > 0 and num_subs >= count:
                break
        result.append(text[pos:])
        return ''.join(result)

    def split(self, text: str, maxsplit: int = 0) -> list:
        result = []
        pos = 0
        num_splits = 0
        while pos <= len(text):
            match_obj = None
            for i in range(pos, len(text) + 1):
                match_obj = self._match_at(text, i)
                if match_obj is not None:
                    break
            if match_obj is None:
                break
            if maxsplit > 0 and num_splits >= maxsplit:
                break
            result.append(text[pos:match_obj.start])
            for g in range(1, self.num_groups + 1):
                result.append(match_obj.groups.get(g, None))
            num_splits += 1
            if match_obj.end > pos:
                pos = match_obj.end
            else:
                if pos < len(text):
                    result.append(text[pos])
                pos = match_obj.end + 1
        result.append(text[pos:])
        return result

    def _match_at(self, text: str, start_pos: int) -> Optional[MatchResult]:
        if self.needs_backtrack:
            result = backtrack_search(text, self.nfa, start_pos, self.state_map, self.flags)
            if result is None:
                return None
            end_pos, grp_ranges = result
            str_groups: Dict[int, str] = {}
            for gn, (gs, ge) in grp_ranges.items():
                str_groups[gn] = text[gs:ge]
            mr = MatchResult(True, start_pos, end_pos, str_groups)
            mr.text = text
            return mr
        else:
            return self._nfa_simulate(text, start_pos)

    def _nfa_simulate(self, text: str, start_pos: int) -> Optional[MatchResult]:
        GroupMap = Dict[int, Tuple[int, int]]

        visited: Dict[Tuple[int, int], int] = {}
        queue: List[Tuple[int, int, GroupMap]] = []

        init: GroupMap = {}
        queue.append((self.nfa.start.id, start_pos, init))

        best_end = -1
        best_groups: GroupMap = {}

        processed_count = 0

        while queue:
            processed_count += 1
            if processed_count > MAX_STATES:
                raise CatastrophicBacktrackError(
                    f"State count exceeded limit ({MAX_STATES}). Possible ReDoS."
                )

            sid, pos, groups = queue.pop(0)

            key = (sid, pos)
            if key in visited and visited[key] >= pos:
                pass
            visited[key] = pos

            state = self.state_map.get(sid)
            if state is None:
                continue

            new_groups = dict(groups)

            if state.capture_start is not None and state.capture_start > 0:
                gn = state.capture_start
                existing = new_groups.get(gn)
                if existing:
                    new_groups[gn] = (pos, existing[1])
                else:
                    new_groups[gn] = (pos, pos)

            if state.capture_end is not None and state.capture_end > 0:
                gn = state.capture_end
                existing = new_groups.get(gn)
                if existing:
                    new_groups[gn] = (existing[0], pos)
                else:
                    new_groups[gn] = (pos, pos)

            if state.assertion:
                if not check_assertion_simple(state.assertion, text, pos, self.flags):
                    continue

            if state.lookahead_nfa is not None:
                lm = collect_state_map(state.lookahead_nfa.start)
                ok = try_match_lookahead(state.lookahead_nfa, text, pos, lm, self.flags)
                if state.lookahead_positive and not ok:
                    continue
                if (not state.lookahead_positive) and ok:
                    continue

            if sid == self.nfa.end.id:
                if pos >= best_end:
                    best_end = pos
                    best_groups = dict(new_groups)
                continue

            for ep in state.epsilon:
                queue.insert(0, (ep.id, pos, dict(new_groups)))

            if pos < len(text):
                ch = text[pos]
                for trans_char, targets in state.transitions.items():
                    if matches_transition(trans_char, ch, self.flags):
                        for t in targets:
                            queue.append((t.id, pos + 1, dict(new_groups)))

        if best_end >= 0:
            str_groups: Dict[int, str] = {}
            for gn, (gs, ge) in best_groups.items():
                str_groups[gn] = text[gs:ge]
            mr = MatchResult(True, start_pos, best_end, str_groups)
            mr.text = text
            return mr
        return None


def compile(pattern: str, flags: int = 0) -> Regex:
    return Regex(pattern, flags)


def match(pattern: str, text: str, flags: int = 0) -> Optional[MatchResult]:
    return Regex(pattern, flags).match(text)


def search(pattern: str, text: str, flags: int = 0) -> Optional[MatchResult]:
    return Regex(pattern, flags).search(text)


def fullmatch(pattern: str, text: str, flags: int = 0) -> Optional[MatchResult]:
    return Regex(pattern, flags).fullmatch(text)


def findall(pattern: str, text: str, flags: int = 0) -> List:
    return Regex(pattern, flags).findall(text)


def sub(pattern: str, replacement: str, text: str, count: int = 0, flags: int = 0) -> str:
    return Regex(pattern, flags).sub(replacement, text, count)


def split(pattern: str, text: str, maxsplit: int = 0, flags: int = 0) -> list:
    return Regex(pattern, flags).split(text, maxsplit)
