from typing import Optional, Set, Callable, Generator, Tuple, List

import z3
from fuzzingbook.Grammars import unreachable_nonterminals
from z3 import Symbol

from input_constraints.type_defs import Path, ParseTree, Grammar


def traverse_tree(tree: ParseTree, action: Callable[[ParseTree], None]) -> None:
    node, children = tree
    action(tree)
    for child in children:
        traverse_tree(child, action)


def get_path_of_subtree(tree: ParseTree, subtree: ParseTree, path: Path = tuple()) -> Optional[Path]:
    current_subtree = get_subtree(path, tree)
    if current_subtree is subtree:
        return path

    node, children = current_subtree
    if not children:
        return None

    for idx in range(len(children)):
        child_result = get_path_of_subtree(tree, subtree, path + (idx,))
        if child_result is not None:
            return child_result

    return None


def delete_unreachable(grammar: Grammar) -> None:
    for unreachable in unreachable_nonterminals(grammar):
        del grammar[unreachable]


def replace_tree_path(in_tree: ParseTree, path: Path, replacement_tree: ParseTree) -> ParseTree:
    """Returns a symbolic input with a new tree where replacement_tree has been inserted at `path`"""

    def recurse(_tree, _path):
        node, children = _tree

        if not _path:
            return replacement_tree

        head = _path[0]
        new_children = (children[:head] +
                        [recurse(children[head], _path[1:])] +
                        children[head + 1:])

        return node, new_children

    return recurse(in_tree, path)


def is_after(path_1: Path, path_2: Path) -> bool:
    return not is_before(path_1, path_2) and \
           not is_prefix(path_1, path_2) and \
           not is_prefix(path_2, path_1)


def is_prefix(path_1: Path, path_2: Path) -> bool:
    if not path_1:
        return True

    if not path_2:
        return False

    car_1, *cdr_1 = path_1
    car_2, *cdr_2 = path_2

    if car_1 != car_2:
        return False
    else:
        return is_prefix(cdr_1, cdr_2)


def is_before(path_1: Path, path_2: Path) -> bool:
    if not path_1 or not path_2:
        # Note: (1,) is not before (1,0), since it's a prefix!
        # Also, (1,) cannot be before ().
        # But (1,0) would be before (1,1).
        return False

    car_1, *cdr_1 = path_1
    car_2, *cdr_2 = path_2

    if car_1 < car_2:
        return True
    elif car_2 < car_1:
        return False
    else:
        return is_before(tuple(cdr_1), tuple(cdr_2))


def get_subtree(path: Path, tree: ParseTree) -> ParseTree:
    """Access a subtree based on `path` (a list of children numbers)"""
    node, children = tree

    if not path:
        return tree

    return get_subtree(path[1:], children[path[0]])


def next_path(path: Path, tree: ParseTree) -> Optional[Path]:
    """Returns the next path in the tree; does not proceed towards leaves!"""
    if not path:
        return None

    node, children = get_subtree(path[:-1], tree)
    if len(children) > path[-1] + 1:
        return path[:-1] + (path[-1] + 1,)
    else:
        return next_path(path[:-1], tree)


def prev_path_complete(path: Path, tree: ParseTree) -> Optional[Path]:
    """
    Returns the previous path in the tree. Repeated calls result in an iterator over
    the paths in the tree (in reverse order), unlike next_path.
    """
    if not path:
        return None

    if path[-1] - 1 >= 0:
        new_path = path[:-1] + (path[-1] - 1,)
        # Proceed right-most leave
        _, children = get_subtree(new_path, tree)
        while children:
            new_path = new_path + (len(children) - 1,)
            _, children = get_subtree(new_path, tree)

        return new_path
    else:
        return path[:-1]


def reverse_tree_iterator(start_path: Path, tree: ParseTree) -> Generator[Tuple[Path, ParseTree], None, None]:
    curr_path = prev_path_complete(start_path, tree)
    while curr_path is not None:
        yield curr_path, get_subtree(curr_path, tree)
        curr_path = prev_path_complete(curr_path, tree)


def get_symbols(formula: z3.BoolRef) -> Set[Symbol]:
    result: Set[Symbol] = set()

    def recurse(elem: z3.ExprRef):
        op = elem.decl()
        if z3.is_const(elem) and op.kind() == z3.Z3_OP_UNINTERPRETED:
            if op.range() != z3.StringSort():
                raise NotImplementedError(
                    f"This class was developed for String symbols only, found {op.range()}")

            result.add(op.name())

        for child in elem.children():
            recurse(child)

    recurse(formula)
    return result


def dfs(tree: ParseTree, action=print):
    node, children = tree
    action(tree)
    for child in children:
        dfs(child, action)


def geometric_sequence(length: int, base: float = 1.1) -> List[int]:
    return list(map(lambda x: 1.1 ** x, range(0, length)))
