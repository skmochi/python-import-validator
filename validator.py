"""
from A.B import X, Yの場合、
rootlib: A
subs: B, X, Y
と定義
"""

# ref: https://gist.github.com/jtpio/cb30bca7abeceae0234c9ef43eec28b4

import ast
import yaml
import dataclasses


WHITELIST_FILEPATH = "./whitelist.yaml"


# TODO: リファクタリング
class Whitelist():
    def __init__(self, filepath):
        """
        Return: [{'rootlib': 'numpy', 'subs': ['max', 'min', 'round']}]
        """
        with open(filepath) as file:
            obj = yaml.safe_load(file)
        # self.whitelist: list[dict] = obj['whitelist']
        self.whitelist = [WhitelistInfo(**x) for x in obj['whitelist']]

    def whitelist_rootlib(self) -> set[str]:
        """
        whitelistのrootlibのsetを返す
        """
        whitelist_rootlib = [x.rootlib for x in self.whitelist]
        return set(whitelist_rootlib)

    def whitelist_subs(self, rootlib) -> set:
        """
        whitelistの指定rootlibのsubsのsetを返す
        """
        whitelist_subs = [x.subs for x in self.whitelist if x.rootlib == rootlib]
        if whitelist_subs:  # もし指定rootlibがwhitelist内にあれば
            whitelist_subs:list[str] = whitelist_subs[0]
        return set(whitelist_subs)

@dataclasses.dataclass
class WhitelistInfo:
    rootlib: str
    subs: list

@dataclasses.dataclass
class ImportInfo:
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
        """
        import_info: list(dict(string)) =
        [{'rootlib': 'numpy', 'subs': None, 'asname': 'np'}, {'rootlib': 'pandas', 'subs': 'to_csv', 'asname': 'csv'}]
        """
        self.imported_rootlib: set[str] = set()
        self.imported_info: list[ImportInfo] = list()
        self.call_info: list[dict] = list()
        self.whitelist = Whitelist(filepath=WHITELIST_FILEPATH)

    def visit_Import(self, node):
        """
        import X を検出するたびに実行される関数
        バリデーションに必要なデータ構造を構築
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
            # d = {"rootlib": rootlib, "subs": subs, "asname": asname}
            d = ImportInfo(rootlib=rootlib, subs=list(subs), asname=asname)
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
        d = ImportInfo(rootlib=rootlib, subs=list(subs), asname=asname)
        self.imported_info.append(d)
        self.generic_visit(node)

    def visit_Call(self, node):
        # e.g. np.savetext -> np
        # print(node.func.value.id)
        # e.g. np.savetext -> savetext
        # print(node.func.attr)
        # parent: rootlib or subs or asname
        d = CallInfo(parent=node.func.value.id, attr=node.func.attr)
        self.call_info.append(d)
        self.generic_visit(node)

    def check_rootlib(self):
        """
        - rootlibがwhitelistにあるか確認
        """
        whitelist_rootlib = self.whitelist.whitelist_rootlib()
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
            rootlib = info.rootlib
            subs = info.subs
            whitelist_subs = self.whitelist.whitelist_subs(rootlib)
            diff = set(subs) - whitelist_subs
            if len(diff) > 0:
                raise ValueError(f"imported bannd method: {list(diff)[0]}")

    def check_calls(self):
        """
        - asnameとの整合性をチェックしつつCallされたmethodがwhitelistにあるか確認
        方針: まずはcallのrootlibを特定し、これがwhitelist_subsに含まれているかを確認する
        """
        for call_info in self.call_info:
            parent = call_info.parent
            attr = call_info.attr
            # TODO: このへん適当
            # parentがasnameと仮定して走査しrootlibを割り出す
            _rootlib_from_asname = [x.rootlib for x in self.imported_info if parent in x.asname]
            # parentがsubsと仮定して走査しrootlibを割り出す
            _rootlib_from_subs = [x.rootlib for x in self.imported_info if parent in x.subs]
            # parentがrootlibと仮定して走査しrootlibを割り出す
            _rootlib_from_rootlib = [x.rootlib for x in self.imported_info if parent in x.rootlib]
            sumset = set(_rootlib_from_asname) | set(_rootlib_from_subs) | set(_rootlib_from_rootlib)
            # これも必要かよくわからん
            if len(sumset) > 1:
                raise ValueError("asnameの命名を変えてください")
            if _rootlib_from_asname:
                for info in self.imported_info:
                    if info.asname == _rootlib_from_asname[0]:
                        rootlib = info.rootlib  # rootlibを特定
                        if attr not in self.whitelist.whitelist_subs(rootlib):
                            raise ValueError("禁止されているものが使用されています")
            if _rootlib_from_subs:
                for info in self.imported_info:
                    if info.asname == _rootlib_from_subs[0]:
                        rootlib = info.rootlib  # rootlibを特定
                        if attr not in self.whitelist.whitelist_subs(rootlib):
                            raise ValueError("禁止されているものが使用されています")
            if _rootlib_from_rootlib:
                for info in self.imported_info:
                    if info.asname == _rootlib_from_rootlib[0]:
                        rootlib = info.rootlib  # rootlibを特定
                        if attr not in self.whitelist.whitelist_subs(rootlib):
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
from pandas import to_csv as csv
# from pandas.compat._optional import import_optional_dependency

np.max("AAA")
"""

tree = ast.parse(code)
# print(vars(tree.body[-1].value.func.value))  # ast.FunctionDef


visitor = CustomVisitor()
visitor.visit(tree)  # def visitXXX()を全て実行
visitor.check_rootlib()
visitor.check_subs()
visitor.check_calls()
