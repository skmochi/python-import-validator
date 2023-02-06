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
    library_whitelist = [LibraryWhitelist(**x) for x in obj['library']]
    buildin_whitelist = [BuildinWhitelist(**x) for x in obj['buildinFunc']]
    return library_whitelist, buildin_whitelist


@dataclasses.dataclass
class LibraryWhitelist:
    name: str
    subs: list
    asname: str = None

@dataclasses.dataclass
class BuildinWhitelist:
    name: str

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


@dataclasses.dataclass
class AttributeData:
    libname: str = None
    attrs: list[str] = None


class CustomVisitor(ast.NodeVisitor):
    def __init__(self):
        self.attributes = []
        self.num_FunctionDef = 0
        self.call_info: list[CallInfo] = list()
        self.whitelist, self.buildin_whitelist = load_whitelist(filepath=WHITELIST_FILEPATH)

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
        from name import subs
        """
        raise ValueError("import is bannd!!")
        # TODO: 必要かよくわからん
        # self.generic_visit(node)

    def visit_Call(self, node):
        # 組み込み関数
        # print(vars(node.func))
        # sum([1,2])
        # {'id': 'sum', 'ctx': <ast.Load object at 0x10d738100>, 'lineno': 5, 'col_offset': 0, 'end_lineno': 5, 'end_col_offset': 3}
        # np.sum([1,2])
        # print(vars(node.func))
        # {'value': <ast.Name object at 0x10d765cd0>, 'attr': 'sum', 'ctx': <ast.Load object at 0x10d4dd100>, 'lineno': 6, 'col_offset': 0, 'end_lineno': 6, 'end_col_offset': 6}
        
        # 組み込み関数か否か
        if hasattr(node.func, "id") and not hasattr(node.func, "attr"):
            is_builtin_func = True
        else:
            is_builtin_func = False
        
        # 組み込み関数のバリデーション
        if is_builtin_func:
            user_builtin_func: str = node.func.id
            if user_builtin_func not in [x.name for x in self.buildin_whitelist]:
                raise ValueError(f"組み込み関数「{user_builtin_func}」は許可されていません")
            return

        # # 以下、組み込み関数以外のバリデーション
        # # A.B.C.method()のパターンの呼び出しは許可リストの存在しないので弾く
        # if not hasattr(node.func.value, "id"):
        #     raise ValueError("call1: 許可されていないメソッドの呼び出しです")

        # d = CallInfo(parent=node.func.value.id, attr=node.func.attr)
        # # このdが許可リスト内にあるか確認する(name or asnameが一致していればok)
        # _pass = [x for x in self.whitelist if d.parent in (x.asname, x.name)]
        # for x in _pass:
        #     if d.attr not in x.subs:
        #         raise ValueError("This method is banned.")
        # TODO: 必要かよくわからん
        self.generic_visit(node)

    # def visit_ClassDef(self, node):
    #     raise ValueError("Class is banned.")
    #     self.generic_visit(node)

    # def visit_AsyncFunctionDef(self, node):
    #     raise ValueError("AsyncDef is banned.")
    #     self.generic_visit(node)

    # def visit_FunctionDef(self, node):
    #     self.num_FunctionDef += 1
    #     print(node.name) # 関数名
    #     print(vars(node.args.args[0])) # 引数
    #     # {'name': 'main', 'args': <ast.arguments object at 0x104ce9f70>, 'body': [<ast.Return object at 0x104ce9e20>], 'decorator_list': [], 'returns': None, 'type_comment': None, 'lineno': 8, 'col_offset': 0, 'end_lineno': 9, 'end_col_offset': 10}
    #     if node.name != "nodeai_main":
    #         raise ValueError("関数は「nodeai_main」のみ許可されています")
    #     if len(node.args.args) != 1:
    #         raise ValueError("nodeai_main関数の引数は1つのみ許可されています")
    #     self.generic_visit(node)

    def visit_Attribute(self, node):
        self.attributes.append(node)
        self.generic_visit(node)


    def attr_checker(self):
        ads: list[AttributeData] = []
        for x in self.attributes:
            print("--------------------------------")
            attrs: list[str] = []
            print(x)
            print(vars(x))
            ad = AttributeData()
            # 以下を再帰的に実行する
            # 多分必ずvalueはある
            if hasattr(x, "value") and isinstance(x.value, ast.Name):
                ad.libname = x.value.id
                attrs.append(x.attr)
                print(ad.libname)
                # このattributeをvalueとしてもつ親のattributeを検索し、そのattrを取得
                for y in self.attributes:
                    if hasattr(y, "value") and x.value == y:
                        attrs.append(y.attr)
                        break  # 親は一つしかないため
            ad.attrs = attrs
            ads.append(ad)
        print("ads: ", ads)



    def additional_validation(self):
        if self.num_FunctionDef != 1:
            raise ValueError("関数「nodeai_main」が必要です")

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
# sum([1, 2])
# np.sum([1, 2])
# numpy.round(1)
# def nodeai_main(df):
#     return
def nodeai_main(df):
    pd.shape = pandas.compat._optional.import_optional_dependency
    r = pd.shape("requests")
    np.arange(6).reshape(2, 3)
    return
"""

code = """
# a = sum(1,1)
pd.shape = pandas.compat._optional.import_optional_dependency
# r = pd.shape("requests")
# np.arange(6).reshape(2, 3)
"""

tree = ast.parse(code)
# print(vars(tree.body[-1].value.func.value))  # ast.FunctionDef


visitor = CustomVisitor()
visitor.visit(tree)  # def visitXXX()を全て実行
visitor.attr_checker()
# visitor.additional_validation()
