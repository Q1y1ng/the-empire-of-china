"""机位表：从 `build_hall.py` 的 `SHOTS` 读，不复制第二份。

为什么不用 import：`build_hall.py` 是脚本，顶层直接建楼；import 会跑一遍完整构建
（40 s + 可能覆盖 .blend）。所以这里用 AST 取出 `SHOTS = [...]` 这个赋值节点，
在受限命名空间里求值——只允许常量、元组/列表/字典、`dict()` 调用、负号、以及
`AX` 这一个名字（取自 `hall_data.AXIS_Y`）。超出这个白名单就报错，
而不是默默算错——以后谁给 SHOTS 加了表达式，这里会立刻炸，不会给出偏掉的站位。

用法：
    from shots_table import load_shots
    shots = load_shots()          # [(name, {loc,target,lens,...}), ...]
"""
from __future__ import annotations

import ast
import os
import sys

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GRANDHALL = os.path.join(ROOT, "tools", "grandhall")
BUILD_PY = os.path.join(GRANDHALL, "build_hall.py")


def _axis_y() -> float:
    """从 hall_data 取中轴线 y（无 bpy，可安全 import）。"""
    if GRANDHALL not in sys.path:
        sys.path.insert(0, GRANDHALL)
    import hall_data  # noqa: WPS433  (延迟 import，避免污染调用方)
    return float(hall_data.AXIS_Y)


def _eval(node, env):
    """受限求值：只认 SHOTS 里会出现的那几种节点。"""
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_eval(e, env) for e in node.elts)
    if isinstance(node, ast.List):
        return [_eval(e, env) for e in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for k, v in zip(node.keys, node.values):
            if k is None:            # **x 展开，不支持
                raise ValueError("SHOTS 里不支持 ** 展开")
            out[_eval(k, env)] = _eval(v, env)
        return out
    if isinstance(node, ast.Call):
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "dict":
            # 两种写法都认：dict(loc=..., lens=...) 与 dict([("loc", ...)])
            out = {}
            if node.args:
                if node.keywords:
                    raise ValueError("dict() 里不要混用位置参数与关键字")
                for a in node.args:
                    out.update(_eval(a, env))
            for kw in node.keywords:
                if kw.arg is None:
                    raise ValueError("dict(**x) 不支持")
                out[kw.arg] = _eval(kw.value, env)
            return out
        raise ValueError(f"SHOTS 里不支持调用 {ast.dump(fn)[:60]}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand, env)
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left, env), _eval(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        raise ValueError(f"SHOTS 里不支持运算符 {type(node.op).__name__}")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ValueError(f"SHOTS 引用了未提供的名字 {node.id!r}")
    raise ValueError(f"SHOTS 里出现不支持的语法 {type(node).__name__}")


def _find_shots_node(tree):
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "SHOTS"):
            return node.value
    raise ValueError("build_hall.py 里没找到顶层 `SHOTS = [...]`")


def load_shots(path: str = BUILD_PY):
    """返回 [(name, spec), ...]；顺带校验每个 spec 有 loc/target。"""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    node = _find_shots_node(ast.parse(src))
    shots = _eval(node, {"AX": _axis_y()})
    out = []
    for item in shots:
        if not (isinstance(item, tuple) and len(item) == 2):
            raise ValueError(f"SHOTS 项不是 (name, spec)：{item!r}")
        name, spec = item
        for key in ("loc", "target"):
            if key not in spec:
                raise ValueError(f"机位 {name!r} 缺 {key}")
        out.append((name, spec))
    return out


def groups_of(manifest_objects):
    """manifest 里出现过的 group 集合。"""
    return {o.get("group") or "hall" for o in manifest_objects}


def visible_groups(manifest_objects, spec):
    """该机位实际看得见的 group：全体减去 hide。"""
    return groups_of(manifest_objects) - set(spec.get("hide", ()))


if __name__ == "__main__":
    table = load_shots()
    for i, (name, spec) in enumerate(table, 1):
        print(f"{i:2d}. {name:12s} loc={spec['loc']} lens={spec.get('lens')} "
              f"hide={spec.get('hide', ())}")
    print(f"共 {len(table)} 个机位（AX={_axis_y()}）")
