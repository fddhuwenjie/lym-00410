import sys
import time
sys.path.insert(0, '/Users/huwenjie/my project/solo/gen-410')

from regex_engine import (
    compile, search, match, fullmatch, findall, sub, split,
    Regex, IGNORECASE, MULTILINE,
    RegexError, CatastrophicBacktrackError
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


section("Existing: (a|b)*c matching")
result = search(r"(a|b)*c", "abc")
test("match 'abc' success", result is not None, f"got {result}")
if result:
    test("match range [0:3] = 'abc'", result.end == 3, f"end={result.end}")

result = search(r"(a|b)*c", "aaabbbccc")
test("match 'aaabbbccc' success", result is not None, f"got {result}")
if result:
    test("longest match to 'aaabbbc'", result.end == 7, f"end={result.end}")

result = search(r"(a|b)*c", "xyz")
test("no match 'xyz'", result is None, f"got {result}")

result = search(r"(a|b)*c", "c")
test("match standalone 'c' success", result is not None, f"got {result}")
if result:
    test("match range correct", result.end == 1)


section("Existing: capture groups")
r = compile(r"(\d{3})-(\d{4})")
result = r.search("Tel: 123-4567 is my number")
test("found match", result is not None, f"got {result}")
if result:
    test("group 1 = '123'", result.groups.get(1) == "123", f"got '{result.groups.get(1)}'")
    test("group 2 = '4567'", result.groups.get(2) == "4567", f"got '{result.groups.get(2)}'")
    test("full match = '123-4567'", result.text[result.start:result.end] == "123-4567")

result = r.search("No numbers here")
test("no numbers no match", result is None)

result = r.search("999-8888 and 111-2222")
test("findall returns multiple groups", len(r.findall("999-8888 and 111-2222")) == 2)


section("Existing: non-greedy")
r = compile(r"a*?")
result = r.match("aaa")
test("a*? non-greedy first match empty", result is not None)
if result:
    test("match length 0", (result.end - result.start) == 0)

r2 = compile(r"a?")
result = r2.match("aaa")
test("a? greedy matches one a", result is not None)

r3 = compile(r"<.*?>")
result = r3.search("<div>hello</div>")
test("non-greedy <.*?> only first tag", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("match '<div>' not longer", matched == "<div>", f"got '{matched}'")

r4 = compile(r"<.*>")
result = r4.search("<div>hello</div>")
test("greedy <.*> longest match", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("match entire string", matched == "<div>hello</div>", f"got '{matched}'")


section("Existing: lookaround assertions")
r = compile(r"(?<=@)\w+")
result = r.search("Contact: user@example.com please")
test("positive lookbehind", result is not None, f"got {result}")
if result:
    matched = result.text[result.start:result.end]
    test("extract 'example'", matched == "example", f"got '{matched}'")

r2 = compile(r"\w+(?=@)")
result = r2.search("Contact: user@example.com please")
test("positive lookahead", result is not None, f"got {result}")
if result:
    matched = result.text[result.start:result.end]
    test("extract 'user'", matched == "user", f"got '{matched}'")


section("Existing: ReDoS protection")
r = compile(r"(a+)+$")
t0 = time.time()
try:
    result = r.search("a" * 30 + "b")
    elapsed = time.time() - t0
    test("completion time < 0.5s", elapsed < 0.5, f"took {elapsed:.3f}s")
    test("result no match", result is None, f"got {result}")
except CatastrophicBacktrackError:
    test("backtrack protection triggered", True)
    elapsed = time.time() - t0
    test("protection time < 1s", elapsed < 1.0, f"took {elapsed:.3f}s")


section("Existing: basic features")
test(". matches any char", search(r".", "a") is not None)
test(". doesn't match newline", search(r".", "\n") is None)
test("backslash-d matches digit", search(r"\d", "abc123") is not None)
test("backslash-D matches non-digit", search(r"\D", "123a456") is not None)
test("backslash-w matches word char", search(r"\w", "hello_world123") is not None)
test("backslash-s matches whitespace", search(r"\s", "hello world") is not None)
test("[abc] char class", search(r"[abc]", "xay") is not None)
test("[^abc] negated char class", search(r"[^abc]", "abcx") is not None)
test("[a-z] range", search(r"[a-z]", "A1b") is not None)
test("^ start anchor", match(r"^hello", "hello world") is not None)
test("^ no mid match", match(r"^hello", "say hello") is None)
test("$ end anchor", search(r"world$", "hello world") is not None)
test("$ no start match", search(r"world$", "world hello") is None)
test("+ at least once", search(r"a+", "aaa") is not None)
test("+ no empty match", match(r"a+", "") is None)
test("? 0 or 1", match(r"a?", "a").end == 1)
test("? match empty", match(r"a?", "b").end == 0)
test("{n} exact count", search(r"a{3}", "aaabbb") is not None)
test("{n,m} range count", search(r"a{2,4}", "aaaab") is not None)
test("backref 1", search(r"(\w+) \1", "abc abc") is not None)
test("non-capture group", search(r"(?:ab)+c", "ababc") is not None)
test("findall multiple", len(findall(r"\w+", "hello world test")) == 3)
test("fullmatch full", fullmatch(r"[a-z]+", "hello") is not None)
test("fullmatch partial no", fullmatch(r"[a-z]+", "hello123") is None)


section("findall with capture groups")
got = findall(r"\d+", "a1b22c333")
test("findall no groups returns full matches",
     got == ["1", "22", "333"], f"got {got}")

got = findall(r"(\d+)", "a1b22c333")
test("findall 1 group returns group list",
     got == ["1", "22", "333"], f"got {got}")

got = findall(r"(\d+)-(\d+)", "12-34 56-78")
test("findall 2 groups returns tuples",
     got == [("12", "34"), ("56", "78")], f"got {got}")

got = findall(r"a", "aaa")
test("findall non-overlapping", got == ["a", "a", "a"], f"got {got}")

got = findall(r"(?P<word>\w+)=(\d+)", "x=1 y=2")
test("findall named group returns group value",
     got == [("x", "1"), ("y", "2")], f"got {got}")


section("sub basic replacement")
got = sub(r"\d+", "NUM", "a1b22c333")
test("sub simple replace", got == "aNUMbNUMcNUM", f"got '{got}'")

got = sub(r"\d+", "NUM", "a1b22c333", count=2)
test("sub with count", got == "aNUMbNUMc333", f"got '{got}'")

got = sub(r"\d+", "NUM", "hello")
test("sub no match", got == "hello", f"got '{got}'")

got = sub(r"\d+", "NUM", "")
test("sub empty string", got == "", f"got '{got}'")

got = sub(r"o", "0", "foo boo")
test("sub replace all occurrences", got == "f00 b00", f"got '{got}'")


section("sub backreference replacement")
got = sub(r"(\w+) (\w+)", r"\2 \1", "hello world")
test("sub backref swap groups", got == "world hello", f"got '{got}'")

got = sub(r"(\d{4})-(\d{2})-(\d{2})", r"\2/\3/\1", "2024-01-15")
test("sub backref date reformat", got == "01/15/2024", f"got '{got}'")

r_named = compile(r"(?P<first>\w+)\s(?P<last>\w+)")
got = r_named.sub(r"\g<last>, \g<first>", "John Smith")
test("sub named backref g<name>", got == "Smith, John", f"got '{got}'")

got = sub(r"(\w+)", r"\g<1>!", "hello")
test("sub numbered backref via g", got == "hello!", f"got '{got}'")

got = sub(r"(\w+)", r"[\1]", "a b c", count=2)
test("sub with count and backref", got == "[a] [b] c", f"got '{got}'")

got = sub(r"a", "\\\\b", "a")
test("sub literal backslash in replacement", got == "\\b", f"got '{got}'")

r = compile(r"(\w+)")
got = r.sub(r"[\1]", "hello world")
test("Regex.sub method", got == "[hello] [world]", f"got '{got}'")


section("split basic")
got = split(r",", "a,b,c")
test("split by comma", got == ["a", "b", "c"], f"got {got}")

got = split(r"\s+", "hello  world   test")
test("split by whitespace", got == ["hello", "world", "test"], f"got {got}")

got = split(r"\s+", "one two three four", maxsplit=2)
test("split with maxsplit", got == ["one", "two", "three four"], f"got {got}")

got = split(r"\d+", "hello")
test("split no match", got == ["hello"], f"got {got}")

got = split(r"/", "/a/b/")
test("split at start and end", got == ["", "a", "b", ""], f"got {got}")

r = compile(r"\s+")
got = r.split("a b c")
test("Regex.split method", got == ["a", "b", "c"], f"got {got}")


section("split with captured groups")
got = split(r"(\d+)", "abc123def456ghi")
test("split preserves capture groups", got == ["abc", "123", "def", "456", "ghi"], f"got {got}")

got = split(r"(\d+)-(\d+)", "a12-34b56-78c")
test("split with multiple groups", got == ["a", "12", "34", "b", "56", "78", "c"], f"got {got}")

got = split(r"(\d+)", "a1b2c3d", maxsplit=2)
test("split with maxsplit and groups", got == ["a", "1", "b", "2", "c3d"], f"got {got}")

got = split(r"(?P<sep>[,;])", "a,b;c")
test("split with named group preserves groups", got == ["a", ",", "b", ";", "c"], f"got {got}")


section("IGNORECASE flag")
got = search(r"hello", "HELLO", IGNORECASE)
test("IGNORECASE simple letter match", got is not None, f"got {got}")

got = search(r"Hello", "hELLO", IGNORECASE)
test("IGNORECASE mixed case match", got is not None, f"got {got}")

got = search(r"[a-z]+", "HELLO", IGNORECASE)
test("IGNORECASE char class match", got is not None, f"got {got}")

got = findall(r"hello", "Hello HELLO hello", IGNORECASE)
test("IGNORECASE findall", got == ["Hello", "HELLO", "hello"], f"got {got}")

got = sub(r"hello", "hi", "Hello HELLO hello", flags=IGNORECASE)
test("IGNORECASE sub", got == "hi hi hi", f"got '{got}'")

got = search(r"(\w+) \1", "abc ABC", IGNORECASE)
test("IGNORECASE backref", got is not None, f"got {got}")

r = compile(r"hello", IGNORECASE)
got = r.search("HELLO")
test("IGNORECASE compiled regex", got is not None, f"got {got}")

got = search(r"hello", "HELLO")
test("without IGNORECASE no match", got is None, f"got {got}")

got = search(r"[^a-z]", "A", IGNORECASE)
test("IGNORECASE negated char class", got is None, f"got {got}")

got = search(r"h.llo", "HELLO", IGNORECASE)
test("IGNORECASE dot unaffected", got is not None, f"got {got}")


section("MULTILINE flag")
got = search(r"^world", "hello\nworld", MULTILINE)
test("MULTILINE ^ matches line start", got is not None, f"got {got}")

got = search(r"hello$", "hello\nworld", MULTILINE)
test("MULTILINE $ matches line end", got is not None, f"got {got}")

got = search(r"^world", "hello\nworld")
test("without MULTILINE ^ only string start", got is None, f"got {got}")

got = search(r"hello$", "hello\nworld")
test("without MULTILINE $ only string end", got is None, f"got {got}")

got = findall(r"^\w+", "hello\nworld\ntest", MULTILINE)
test("MULTILINE findall per line ^", got == ["hello", "world", "test"], f"got {got}")

got = findall(r"\w+$", "hello\nworld\ntest", MULTILINE)
test("MULTILINE findall per line $", got == ["hello", "world", "test"], f"got {got}")

r = compile(r"^\w+", MULTILINE)
got = r.findall("a\nb\nc")
test("MULTILINE compiled regex", got == ["a", "b", "c"], f"got {got}")


section("Combined IGNORECASE + MULTILINE flags")
combined = IGNORECASE | MULTILINE

got = search(r"^hello", "HELLO\nworld", combined)
test("combined ^ with case insensitive", got is not None, f"got {got}")

got = search(r"world$", "hello\nWORLD", combined)
test("combined $ with case insensitive", got is not None, f"got {got}")

got = findall(r"^hello", "Hello\nHELLO\nhello", combined)
test("combined findall", got == ["Hello", "HELLO", "hello"], f"got {got}")

got = sub(r"^hello", "hi", "Hello\nHELLO\nhello", flags=combined)
test("combined sub", got == "hi\nhi\nhi", f"got '{got}'")

got = split(r"^hello", "Hello\nHELLO\nhello", flags=combined)
test("combined split", got == ["", "\n", "\n", ""], f"got {got}")

got = search(r"(\w+) \1", "abc ABC\ndef DEF", combined)
test("combined backref with flags", got is not None, f"got {got}")


section("Named groups")
r = compile(r"(?P<first>\w+)\s(?P<last>\w+)")
result = r.search("John Smith")
test("named group match", result is not None, f"got {result}")
if result:
    test("named group value first", result.groups.get(1) == "John", f"got '{result.groups.get(1)}'")
    test("named group value last", result.groups.get(2) == "Smith", f"got '{result.groups.get(2)}'")

got = findall(r"(?P<k>\w+)=(?P<v>\d+)", "a=1 b=2")
test("named group in findall", got == [("a", "1"), ("b", "2")], f"got {got}")

r_named = compile(r"(?P<word>\w+)")
got = r_named.sub(r"[\g<word>]", "hello world")
test("named group sub with g<name>", got == "[hello] [world]", f"got '{got}'")


section("Edge cases")
got = sub(r"a*", "X", "bc")
test("sub zero-length match", got == "XbXcX", f"got '{got}'")

got = split(r",", "a,,b")
test("split consecutive delimiters", got == ["a", "", "b"], f"got {got}")

got = findall(r"a", "aaa")
test("findall overlapping pattern", got == ["a", "a", "a"], f"got {got}")

got = sub(r"(\w+)", r"[\1]", "abc")
test("sub with backref single word", got == "[abc]", f"got '{got}'")

got = search(r"\d+", "abc123", IGNORECASE)
test("IGNORECASE non-alpha unaffected", got is not None, f"got {got}")

got = search(r"^hello", "hello world", MULTILINE)
test("MULTILINE still matches string start", got is not None, f"got {got}")

got = search(r"world$", "hello world", MULTILINE)
test("MULTILINE still matches string end", got is not None, f"got {got}")


section("Summary")
print(f"\n  Total: {passed} passed, {failed} failed, {passed + failed} tests")
if failed == 0:
    print("\n  All tests passed!")
else:
    print(f"\n  {failed} tests need fixing")
    sys.exit(1)
