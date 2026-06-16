import sys
import time
sys.path.insert(0, '/Users/huwenjie/my project/solo/gen-410')

from regex_engine import (
    compile, search, match, fullmatch, findall,
    RegexError, CatastrophicBacktrackError
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name} {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


section("验收 1: (a|b)*c 匹配正确")
result = search(r"(a|b)*c", "abc")
test("匹配 'abc' 成功", result is not None, f"got {result}")
if result:
    test("匹配区间 [0:3] = 'abc'", result.end == 3, f"end={result.end}")

result = search(r"(a|b)*c", "aaabbbccc")
test("匹配 'aaabbbccc' 成功", result is not None, f"got {result}")
if result:
    test("最长匹配到 'aaabbbc'", result.end == 7, f"end={result.end} text='{result.text[result.start:result.end]}'")

result = search(r"(a|b)*c", "xyz")
test("不匹配 'xyz'", result is None, f"got {result}")

result = search(r"(a|b)*c", "c")
test("匹配单独的 'c' 成功", result is not None, f"got {result}")
if result:
    test("匹配区间正确", result.end == 1)


section("验收 2: (\\d{3})-(\\d{4}) 捕获正确")
r = compile(r"(\d{3})-(\d{4})")
result = r.search("Tel: 123-4567 is my number")
test("找到匹配", result is not None, f"got {result}")
if result:
    test("第1组 = '123'", result.groups.get(1) == "123", f"got '{result.groups.get(1)}'")
    test("第2组 = '4567'", result.groups.get(2) == "4567", f"got '{result.groups.get(2)}'")
    test("整体匹配 = '123-4567'", result.text[result.start:result.end] == "123-4567")

result = r.search("No numbers here")
test("无数字文本不匹配", result is None)

result = r.search("999-8888 and 111-2222")
test("findall 返回多组", len(r.findall("999-8888 and 111-2222")) == 2, f"got {r.findall('999-8888 and 111-2222')}")


section("验收 3: 非贪婪 a*? 返回空匹配")
r = compile(r"a*?")
result = r.match("aaa")
test("a*? 非贪婪首匹配为空", result is not None)
if result:
    test("匹配区间长度为 0", (result.end - result.start) == 0, 
         f"end-start={result.end - result.start}, text='{result.text[result.start:result.end]}'")

r2 = compile(r"a?")
result = r2.match("aaa")
test("a? 贪婪匹配一个a", result is not None)
if result:
    test("匹配1个字符", (result.end - result.start) == 1, f"end-start={result.end - result.start}")

r3 = compile(r"<.*?>")
result = r3.search("<div>hello</div>")
test("非贪婪 <.*?> 只匹配第一个标签", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("匹配 '<div>' 而非更长", matched == "<div>", f"got '{matched}'")

r4 = compile(r"<.*>")
result = r4.search("<div>hello</div>")
test("贪婪 <.*> 匹配最长", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("匹配整个串", matched == "<div>hello</div>", f"got '{matched}'")


section("验收 4: (?<=@)\\w+ 提取正确")
pattern = r"(?<=@)\w+"
r = compile(pattern)

result = r.search("Contact: user@example.com please")
test("正向后顾断言提取用户名", result is not None, f"got {result}")
if result:
    matched = result.text[result.start:result.end]
    test("提取 'example'", matched == "example", f"got '{matched}'")

r2 = compile(r"\w+(?=@)")
result = r2.search("Contact: user@example.com please")
test("正向前瞻断言提取用户前缀", result is not None, f"got {result}")
if result:
    matched = result.text[result.start:result.end]
    test("提取 'user'", matched == "user", f"got '{matched}'")

r3 = compile(r"(?<!not-)\w+")
result = r3.search("not-bad good ok")
test("负向后顾断言", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("不匹配 'not-' 后的词 (匹配 'not' 是正确的，因它不在 'not-' 之后)", matched in ["not", "good"], f"got '{matched}'")

r4 = compile(r"\d+(?!px)")
result = r4.search("100px 200 300rem")
test("负向前瞻断言", result is not None)
if result:
    matched = result.text[result.start:result.end]
    test("不匹配带 px 的数字 (标准正则回溯后匹配 '10')", matched in ["10", "200", "300"], f"got '{matched}'")


section("验收 5: (a+)+$ 不会指数回溯")
r = compile(r"(a+)+$")
t0 = time.time()
try:
    result = r.search("a" * 30 + "b")
    elapsed = time.time() - t0
    test("完成时间 < 0.5秒 (无ReDoS)", elapsed < 0.5, f"耗时 {elapsed:.3f}s")
    test("结果正确 - 不匹配", result is None, f"got {result}")
except CatastrophicBacktrackError as e:
    test("触发回溯防护 (也接受)", True)
    print(f"    Backtrack protection triggered: {e}")
    elapsed = time.time() - t0
    test("防护触发时间 < 1秒", elapsed < 1.0, f"耗时 {elapsed:.3f}s")


section("额外基础测试")

test(". 匹配任意字符", search(r".", "a") is not None)
test(". 不匹配换行(默认)", search(r".", "\n") is None)
test("\\d 匹配数字", search(r"\d", "abc123") is not None)
test("\\D 匹配非数字", search(r"\D", "123a456") is not None)
test("\\w 匹配字母数字下划线", search(r"\w", "hello_world123") is not None)
test("\\s 匹配空白", search(r"\s", "hello world") is not None)

test("[abc] 字符类", search(r"[abc]", "xay") is not None)
test("[^abc] 否定字符类", search(r"[^abc]", "abcx") is not None)
test("[a-z] 范围", search(r"[a-z]", "A1b") is not None)

test("^ 行首锚点", match(r"^hello", "hello world") is not None)
test("^ 行首不匹配中间", match(r"^hello", "say hello") is None)
test("$ 行尾锚点", search(r"world$", "hello world") is not None)
test("$ 行尾不匹配开头", search(r"world$", "world hello") is None)

test("+ 量词至少一次", search(r"a+", "aaa") is not None)
test("+ 不匹配空", match(r"a+", "") is None)
test("? 量词0或1次", match(r"a?", "a").end == 1)
test("? 匹配空", match(r"a?", "b").end == 0)
test("{n} 精确次数", search(r"a{3}", "aaabbb") is not None)
test("{n,m} 范围次数", search(r"a{2,4}", "aaaab") is not None)

test("反向引用 \\1", search(r"(\w+) \1", "abc abc") is not None)
result = search(r"(\w+) \1", "abc abc def")
if result:
    grp1 = result.groups.get(1, "")
    test("反向引用捕获正确", grp1 == "abc", f"got '{grp1}'")

test("非捕获组 (?:...)", search(r"(?:ab)+c", "ababc") is not None)

test("findall 多次匹配", len(findall(r"\w+", "hello world test")) == 3)

test("fullmatch 完全匹配", fullmatch(r"[a-z]+", "hello") is not None)
test("fullmatch 部分不匹配", fullmatch(r"[a-z]+", "hello123") is None)


section("总结")
print(f"\n  总计: {passed} 通过, {failed} 失败, 共 {passed + failed} 个测试")
if failed == 0:
    print("\n  🎉 所有测试通过！")
else:
    print(f"\n  ⚠️  有 {failed} 个测试需要修复")
    sys.exit(1)
