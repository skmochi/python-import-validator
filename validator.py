"""
from A.B import X, Yの場合、
rootlib: A
subs: B, X, Y
と定義
"""

# ref: https://gist.github.com/jtpio/cb30bca7abeceae0234c9ef43eec28b4

import ast
import yaml


# TODO: リファクタリング
class Whitelist():
    @staticmethod
    def whitelist_rootlib() -> set[str]:
        with open('./whitelist.yaml') as file:
            obj = yaml.safe_load(file)
            whitelist = obj['whitelist']
        whitelist_rootlib = [x["rootlib"] for x in whitelist]
        return set(whitelist_rootlib)

    @staticmethod
    def whitelist_subs(rootlib) -> set[str]:
        with open('./whitelist.yaml') as file:
            obj = yaml.safe_load(file)
            whitelist = obj['whitelist']
        whitelist_subs = [x["subs"] for x in whitelist if x["rootlib"] == rootlib]
        if whitelist_subs:  # もしrootlibがあればwhitelist内にあれば
            whitelist_subs:list[str] = whitelist_subs[0]
        return set(whitelist_subs)

    def load_whitelist(file):
        """
        Return: [{'rootlib': 'numpy', 'subs': ['max', 'min', 'round']}]
        """
        with open('./whitelist.yaml') as file:
            obj = yaml.safe_load(file)
            print(obj['whitelist'])
        return obj['whitelist']


class CustomVisitor(ast.NodeVisitor):
    def __init__(self):
        """
        import_info: list(dict(string)) =
        [{'rootlib': 'numpy', 'subs': None, 'asname': 'np'}, {'rootlib': 'pandas', 'subs': 'to_csv', 'asname': 'csv'}]
        """
        self.imported_rootlib: set[str] = set()
        self.imported_info: list[dict] = list()
        self.call_info: list[dict] = list()
        self.whitelist_rootlib = ["numpy", "pandas"]
        self.whitelist_module_method = [{"numpy": ["sum"]}, {"pandas": ["sum", "max"]}]

    def visit_Import(self, node):
        """
        import X を検出するたびに実行される関数
        import rootlib
        """
        print("visit_Import")
        # import os, sys の場合、node.namesの要素は2つ
        for x in node.names:
            libname = x.name
            # import X.Y.Z のようなパターンに対応
            # rootlib: X, subs: [Y, Z] とする
            rootlib: str = libname.split(".")[0]
            subs: list[str] = libname.split(".")[1:]
            self.imported_rootlib.add(rootlib)
            asname: str | None = getattr(x, "asname", None)
            d = {"rootlib": rootlib, "subs": subs, "asname": asname}
            self.imported_info.append(d)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        from X import Y を検出するたびに実行される関数
        from rootlib import subs
        """
        print("visit_ImportFrom")
        subs = set()
        libname = node.module
        rootlib: str = libname.split(".")[0]
        self.imported_rootlib.add(rootlib)
        _subs: list[str] = libname.split(".")[1:]  # .でバラす
        subs = subs | set(_subs)
        # from X import Y のY部分をsubsに格納
        # from numpy import min, max as np の場合、node.namesはminとmaxの分の2つ
        asname = []
        for x in node.names:
            subs.add(x.name)
            _asname = getattr(x, "asname", None)
            if _asname is not None:
                asname.append(_asname)
        if len(asname) == 1:
            asname = asname[0]
        elif len(asname) == 0:
            asname = None
        else:
            # どうせpython実行時にエラーが出ると思うけど念のため確認
            raise ValueError("as nameは1つのimportで2つ以上の定義はできません")
        d = {"rootlib": rootlib, "subs": list(subs), "asname": asname}
        print(d)
        self.imported_info.append(d)
        self.generic_visit(node)

    def visit_Call(self, node):
        print("===module's method call===")
        # e.g. np.savetext -> np
        print(node.func.value.id)
        # e.g. np.savetext -> savetext
        print(node.func.attr)
        self.generic_visit(node)
        # parent: rootlib or subs or asname
        d = {"parent": node.func.value.id, "attr": node.func.attr}
        print(d)
        self.call_info.append(d)

    def check_rootlib(self):
        """
        - rootlibがwhitelistにあるか確認
        """
        whitelist_rootlib = Whitelist.whitelist_rootlib()
        diff = self.imported_rootlib - whitelist_rootlib
        if len(diff) == 0:
            return
        else:
            raise ValueError(f"imported bannd library: {list(diff)[0]}")

    def check_subs(self):
        """
        - subsがwhitelistにあるか確認
        """
        for info in self.imported_info:
            rootlib = info["rootlib"]
            subs = set(info["subs"])
            whitelist_subs = Whitelist.whitelist_subs(rootlib)
            diff = subs - whitelist_subs
            if len(diff) > 0:
                raise ValueError(f"imported bannd method: {list(diff)[0]}")

    def check_calls(self):
        """
        - asnameとの整合性をチェックしつつCallされたmethodがwhitelistにあるか確認
        方針: まずはcallのrootlibを特定し、これがwhitelist_subsに含まれているかを確認する
        """
        for info in self.call_info:
            parent = info["parent"]
            # parentがasnameと仮定して走査しrootlibを割り出す
            _rootlib_from_asname = set([x["rootlib"] for x in self.imported_info if parent in x["asname"]])
            # parentがsubsと仮定して走査しrootlibを割り出す
            _rootlib_from_subs = set([x["rootlib"] for x in self.imported_info if parent in x["subs"]])
            # parentがrootlibと仮定して走査しrootlibを割り出す
            _rootlib_from_rootlib = set([x["rootlib"] for x in self.imported_info if parent in x["rootlib"]])
            if len(_rootlib_from_asname | _rootlib_from_subs | _rootlib_from_rootlib) > 1:
                raise ValueError("asnameの命名を変えてください")
            if len(_rootlib_from_asname | _rootlib_from_subs | _rootlib_from_rootlib) == 1:
                rootlib = _rootlib_from_asname | _rootlib_from_subs | _rootlib_from_rootlib
                if parent not in Whitelist.whitelist_subs(rootlib):
                    raise ValueError("禁止されているものが使用されています")
        return



    def check_asnane_independencies(self):
        # TODO: import_info内にasname同士やrootlib, subsなどとの被りがないか確認
        # asnameの被りがあると紐付けが困難になるので弾く
        return

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
# from pandas import to_csv as csv
# from pandas.compat._optional import import_optional_dependency

np.savetext("AAA")
"""

tree = ast.parse(code)
# print(vars(tree.body[-1].value.func.value))  # ast.FunctionDef


visitor = CustomVisitor()
visitor.visit(tree)  # def visitXXX()を全て実行
visitor.check_rootlib()
visitor.check_subs()
visitor.check_calls()
