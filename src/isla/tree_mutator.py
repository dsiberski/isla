# Copyright © 2023 Dana Siberski
#
# This file is part of ISLa.
#
# ISLa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ISLa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ISLa.  If not, see <http://www.gnu.org/licenses/>.

from typing import Optional, List, Tuple, cast, Union, Set, Dict

from grammar_graph.gg import GrammarGraph

from isla.derivation_tree import DerivationTree
from isla.type_defs import CanonicalGrammar

from collections import deque


def insert_tree(
        grammar: CanonicalGrammar,
        in_tree: DerivationTree,
        tree: DerivationTree,
        graph: Optional[GrammarGraph] = None,
        methods: Optional[int] = 0,  # TODO: decide how to encode/use
        predicate: Optional[str] = None
) -> List[DerivationTree]:
    possible_parents = possible_parent_types(in_tree.value, grammar)
    insertion_points = identify_insertion_points(tree, possible_parents)

    # TODO: no children[0] -> consider all possible parents
    matching_rules = identify_rule_expansions(grammar, in_tree.value, possible_parents[0])

    result = []

    simplest_matching_rule = matching_rules[0]  # TODO: takes "shortest" rule currently, decide what else to consider

    for idx in insertion_points:
        result.append(create_new_tree(tree, in_tree, idx, simplest_matching_rule))

    return result


def create_new_tree(old_tree: DerivationTree, tree_to_insert: DerivationTree, node_id: int, possible_rules) \
        -> DerivationTree:
    """Returns tree where tree_to_insert has been inserted as position-th child at node node_id."""
    path = old_tree.find_node(node_id)
    subtree = old_tree.get_subtree(path)
    new_subtree = insert_tree_into_parent(subtree, tree_to_insert, possible_rules)

    return old_tree.replace_path(path, new_subtree)


def insert_tree_into_parent(old_tree: DerivationTree, tree_to_insert: DerivationTree, rule: List[str]) \
        -> DerivationTree:
    """Returns tree where tree_to_insert has been inserted as nth child into the tree."""

    new_children = []

    for item in rule:
        if item == tree_to_insert.value:
            new_children.append(tree_to_insert)

        elif item == old_tree.value:
            new_children.append(old_tree)

        else:
            new_children.append(DerivationTree(item, None))  # TODO: fix id

    if tree_to_insert.is_open is True:  # TODO: does this cover all options? does not with in regard to grammar rules
        is_open = True
    elif tree_to_insert.is_open is False and old_tree.is_open is False:
        is_open = False
    else:
        is_open = None

    return DerivationTree(old_tree.value, new_children, is_open=is_open)  # TODO: fix id


def possible_parent_types(root_type: str, grammar: CanonicalGrammar) -> List[str]:
    """Reverse sorts the grammar, and return all possible parents for the in tree"""
    sorted_parents = dict()

    for parent in grammar:
        for children in grammar[parent]:
            for child in children:
                if child not in sorted_parents:
                    sorted_parents[child] = [parent]
                else:
                    sorted_parents[child].append(parent)

    return sorted_parents[root_type]


def identify_insertion_points(tree: DerivationTree, parent_types: List[str]):
    """Checks all nodes for possible insertion points in DFS order and return the corresponding node ids as a list."""
    # TODO: might return path as well
    nodes = deque()  # use deque because of O(1) runtime for pop and append.
    nodes.append(tree)
    interesting_nodes = []

    while nodes:
        current_node = nodes.pop()
        if current_node is not None:
            new_nodes = reversed(list(current_node.children))
            nodes.extend(new_nodes)
            if current_node.value in parent_types:
                interesting_nodes.append(current_node.id)

    return interesting_nodes


def identify_rule_expansions(grammar: CanonicalGrammar, insert_type: str, parent_type: str) -> List[List[str]]:
    """
    Return all rule expansions that fit both the type of the tree that will be inserted and the parent node into
    which it will be inserted for direct recursive insertion. The resulting list is sorted by length of the rules, so
    in case of multiple matching option the shortest will be considered first.
    """
    matching_rules = []
    options = grammar[parent_type]

    for rule in options:
        valid_rule = True
        if insert_type not in rule:
            valid_rule = False
        if parent_type not in rule:
            valid_rule = False

        if valid_rule:
            matching_rules.append(rule)

    matching_rules.sort(key=len)  # return simplest solution first, defined by length
    return matching_rules
