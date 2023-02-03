# ref: https://gist.github.com/jtpio/cb30bca7abeceae0234c9ef43eec28b4

import ast

class CustomVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imported_root_module = set()
        self.import_info = list()
        """
        import_info =
        [{'ROOT_MODULE': 'numpy', 'SUB': None, 'asname': 'np'}, {'ROOT_MODULE': 'pandas', 'SUB': 'to_csv', 'asname': 'csv'}]
        """
        self.whitelist_root_module = ["numpy", "pandas"]
        self.whitelist_module_method = [{"numpy": ["sum"]}, {"pandas": ["sum", "max"]}]
    
    def visit_Import(self, node):
        """
        import ROOT_MODULE
        """
        print("visit_Import")
        # print(f"ROOT_MODULE: {node.module}")
        for x in node.names:
            root_module = x.name
            root_module = root_module.split(".")[0]
            print(f"ROOT_MODULE: {root_module}")
            self.imported_root_module.add(x.name)
            asname = getattr(x, "asname", None)
            print(f"asname     : {asname}")
            d = {"ROOT_MODULE": root_module, "SUB": None, "asname": asname}
            self.import_info.append(d)
        # self._detect_duplicated_import(node)
        # self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        from ROOT_MODULE import SUB
        """
        print("visit_ImportFrom")
        root_module = node.module
        root_module = root_module.split(".")[0]
        subs = node.module.split(".")[1:]  # .でバラす
        print(f"ROOT_MODULE: {root_module}")
        self.imported_root_module.add(node.module)
        for x in node.names:  # names: SUB
            print(f"SUB        : {x.name}")
            asname = getattr(x, "asname", None)
            print(f"asname     : {asname}")
            d = {"ROOT_MODULE": node.module, "SUB": x.name, "asname": asname}
            self.import_info.append(d)
        # self._detect_duplicated_import(node)
        # self.generic_visit(node)

    def visit_Call(self, node):
        print("===module's method call===")
        # e.g. np.savetext -> savetext
        print(node.func.attr)
        # e.g. np.savetext -> np
        print(node.func.value.id)
        self.generic_visit(node)
        d = {"asname_or_rootmodule": node.func.value.id, "attr": node.func.attr}
        print(d)

    def pp(self):
        print(self.imported_root_module)
        print(self.import_info)
        for x in self.import_info:
            if x.ROOT_MODULE not in self.whitelist_root_module:
                print("ERROR: Root_Module")
            
# code = open('./code.py', 'r')

# print(code.read())


code = """
# import numpy as np
# from pandas import to_csv as csv
from pandas.compat._optional import import_optional_dependency
f = np.savetext("filename")
f = numpy.savetext("filename")
"""

tree = ast.parse(code)
print(vars(tree.body[-1].value.func.value))  # ast.FunctionDef


visitor = CustomVisitor()
visitor.visit(tree)  # def visitXXX()を全て実行
# visitor.pp()
