from dataclasses import dataclass, field

@dataclass
class Karaage():
    name: str
    num: int

lst = []
k1 = Karaage(name="onamae1", num=1)
k2 = Karaage(name="onamae2", num=2)

lst = [k1, k2]

print(lst["onamae1"])
