"""
1. import系は全て弾く(システム側で付与する方針)
2. メソッド呼び出しは許可されたlibraryとasnameの組み合わせのみ
e.g.
library: numpy
asname: np
method: min, max, round
許可パターン: {parent: np or numpy, method: [min, max, round]}
"""

# ref: https://gist.github.com/jtpio/cb30bca7abeceae0234c9ef43eec28b4

import ast
import yaml
import dataclasses


WHITELIST_FILEPATH = "./whitelist.yaml"


# TODO: リファクタリング
def load_whitelist(filepath):
    with open(filepath) as file:
        obj = yaml.safe_load(file)
    whitelist = [WhitelistInfo(**x) for x in obj['whitelist']]
    return whitelist


@dataclasses.dataclass
class WhitelistInfo:
    rootlib: str
    subs: list
    asname: str = None

@dataclasses.dataclass
class CallInfo:
    """
    e.g. -------------
    import numpy as np
    np.savetxt("text.txt")
    ------------------
    parent: np
    attr: savetext
    """
    parent: str
    attr: str


class CustomVisitor(ast.NodeVisitor):
    def __init__(self):
        self.call_info: list[CallInfo] = list()
        self.whitelist = load_whitelist(filepath=WHITELIST_FILEPATH)

    def visit_Import(self, node):
        """
        import X を検出するたびに実行される関数
        バリデーションに必要なデータ構造を構築
        """
        raise ValueError("import is bannd!!")
        # TODO: 必要かよくわからん
        # self.generic_visit(node)


    def visit_ImportFrom(self, node):
        """
        from X import Y を検出するたびに実行される関数
        from rootlib import subs
        """
        raise ValueError("import is bannd!!")
        # TODO: 必要かよくわからん
        # self.generic_visit(node)

    def visit_Call(self, node):
        # print(vars(node.func.value))
        # A.B.C.method()のパターンの呼び出しは許可リストの存在しないので弾く
        if not hasattr(node.func.value, "id"):
            raise ValueError("call1: 許可されていないメソッドの呼び出しです")
        d = CallInfo(parent=node.func.value.id, attr=node.func.attr)
        # このdが許可リスト内にあるか確認する(rootlib or asnameが一致していればok)
        # 一致するparentを検索
        _pass = [x for x in self.whitelist if d.parent in (x.asname, x.rootlib)]
        for x in _pass:
            if d.attr not in x.subs:
                raise ValueError("This method is banned.")
        # TODO: 必要かよくわからん
        # self.generic_visit(node)


code1 = """
# import numpy as np
# from pandas import to_csv as csv
# from pandas.compat._optional import import_optional_dependency
# f = np.savetext("filename")
# f = numpy.savetext("filename")
def main():
    from pandas.compat._optional import import_optional_dependency
    return
"""

code = """
from numpy import min, max as np
import numpy as np
from pandas import to_csv as csv
# from pandas.compat._optional import import_optional_dependency

np.max("AAA")
"""

code = """
# import pandas as pandas

# pandas.compat._optional.import_optional_dependency("requests")
numpy.round(1)
"""

tree = ast.parse(code)
# print(vars(tree.body[-1].value.func.value))  # ast.FunctionDef


visitor = CustomVisitor()
visitor.visit(tree)  # def visitXXX()を全て実行
