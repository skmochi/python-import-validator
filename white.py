from dataclasses import dataclass

@dataclass
class Person:
    rootlib: str
    age: int


p = Person('Mike', 20)
print(p)

# もちろん個別にアクセスできる
# print(p.name)
print(p.age)