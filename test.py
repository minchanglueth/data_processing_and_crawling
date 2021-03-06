# def add(a, b):
#     return a + b


# def multiply(a, b):
#     return a * b

import string
from google_spreadsheet_api.function import get_gsheet_column


class i:
    def __init__(self, j: int, a_variable: int, b_variable: int):
        self.j = j
        self.a_variable = a_variable
        self.b_variable = b_variable

    def add(self):
        return self.a_variable + self.b_variable

    def multiply(self):
        return self.a_variable * self.b_variable * self.j


class k:
    def __init__(self, j: int, a_variable: int, b_variable: int, k: int):
        self.j = j
        self.a_variable = a_variable
        self.b_variable = b_variable
        self.k = k

    def add(self):
        return self.a_variable + self.b_variable

    def multiply(self):
        return self.a_variable * self.b_variable * self.j


switch_dict = {
    1: i.add,
    2: i.multiply,
    3: i.add,
    4: i.multiply,
    5: i.add,
    6: i.multiply,
}


maddie = i(1, 4, 5)
minchan = k(2, 6, 8, 9)


def add_or_multiply(x):
    j = x.j
    a = x.a_variable
    b = x.b_variable
    # return (j, a, b)
    return switch_dict[j](x)


def func(classNames, self):
    attr = tuple([self.__dict__[i] for i in self.__dict__.keys()])
    return


import inspect

# print(inspect.signature(i).parameters.keys())


def is_a_in_x(A, X):
    for i in range(len(X) - len(A) + 1):
        if A == X[i : i + len(A)]:
            return True
    return False


if __name__ == "__main__":
    update_column_list = ["me", "and", "your", "girlfriend"]
    sheet_column_list = [
        "slumber",
        "party",
        "me",
        "and",
        "your",
        "girlfriend",
        "playing",
        "dress",
        "up",
        "on",
        "the",
        "couch",
    ]
    print(get_gsheet_column(update_column_list, sheet_column_list, "first"))
