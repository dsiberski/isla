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
import queue
from typing import Optional, List, Tuple, cast, Union, Set, Dict

from grammar_graph.gg import GrammarGraph

from isla.derivation_tree import DerivationTree
from isla.type_defs import CanonicalGrammar, Path
from test_helpers import canonical # TODO: this should not come from the helpers!!!

from collections import deque


def insert_tree(
        grammar, # TODO: what is its type
        in_tree: DerivationTree,
        tree: DerivationTree,
        graph: Optional[GrammarGraph] = None,
        methods: Optional[int] = 0,  # TODO: decide how to encode/use
        predicate: Optional[str] = None # TODO: mostly call methods on subtree ?
) -> List[DerivationTree]:
    canonical_grammar = canonical(grammar)
    results = queue.Queue(3) # deque has no empty attribute
    start_nodes = deque() # enables fast FIFO
    start_nodes.append(tree)

    # insert into open nodes
    # TODO: this should not be needed
    # if tree.is_open():
    #     open_nodes = path_empty_nodes(tree, in_tree.value)
    #     result = [tree.replace_path(path, in_tree) for path in open_nodes]
    #     results.put(result)

    if graph is None:
        graph = GrammarGraph.from_grammar(grammar) # TODO: might need different parameter here or graph non-optional

    inserted_node = graph.get_node(in_tree.value)

    # start with the shortest path to a possible insertion point TODO: non-trivial path
    path = [node.symbol for node in graph.shortest_path(graph.root, inserted_node)]
    # remove last element from path since we want to find an insertion point
    path.pop()
    # remove <start> from path since we already start there
    path.remove('<start>')


    while True:
        if results.empty():
            try:
                # step 0: get (new) start_node from list and calc new path, repeat steps 1-2 while nodes in start_nodes list
                subtree = start_nodes.popleft() # TODO: decide in which order to traverse subtrees
            except IndexError:
                # all possible direct insertions of the current in_tree have been done
                # step 4: extend in_tree by adding parent, <new_parent> != <old_parent, set start_node = <start>
                subtree = tree
                in_tree = extend_in_tree(in_tree) # TODO: implement, lower priority, do I need to compute multiple trees?
                # TODO: since a node mmight have different viable parents
                # step 4.1: repeat step 1-3
                # step 5: terminate if in_tree.type = <start> # TODO: this will change with predicates!
                if in_tree.value == "<start>": # TODO: should I use tree.type instead of "<start>" ?q
                    break

            # step 1: follow path, add siblings to start-nodes list
            # TODO: save derivation_tree path for insertion using "replace path" function
            new_start_nodes = []
            for node in path:
                new_start_nodes.extend(subtree.children)
                subtree = traverse_shortest_path(subtree, node)
                # TODO: step 1.1: if stuck, check if children in path or empty children, middle priority
                try:
                    new_start_nodes.remove(subtree)
                except ValueError:
                    pass
                # step 1.2: add children to start_nodes list
                start_nodes.extend([new_start_nodes]) # TODO: filter this for predicates, lower priority


            # step 2: found end of path -> check for possible expansions
            parent_type = path[len(path) - 1]
            # step 2.1: check if expansion fits in_tree + old children # TODO: matching algorithm, high priority
            possible_rules = canonical_grammar.get(parent_type)
            new_children = list()
            for rule in possible_rules:
                if parent_type in rule and in_tree.value in rule:
                    # step 2.1.1: collect children's and insert's type and match with rules for parent type
                    new_children = match_rule(rule, in_tree, subtree)

            # step 2.2: insert if True for each expansion that fits
            new_subtree = DerivationTree(parent_type, new_children) # TODO: id, low priority

            new_tree = tree.replace_path(tree.find_node(subtree), new_subtree) # TODO: identify path more efficiently?
            results.put(new_tree)

        else:
            # return calculated results
            yield results.get(timeout=60)  # ensure it will not block forever, deque also has no empty attribute


def match_rule(rule, in_tree, parent):
    # TODO: cannot add multiple children of same type
    new_children = []

    for item in rule:
        if item == parent.value:
            new_children.append(parent)

        elif item == in_tree.value:
            new_children.append(in_tree)

        else:
            new_children.append(DerivationTree(item, ()))  # TODO: fix id

    return new_children



def traverse_shortest_path(tree, node):
    for child in tree.children:
        if child.value == node:
            return child
    return # TODO: stuck error?


def extend_in_tree(tree):
    raise NotImplementedError


def path_empty_nodes(tree: DerivationTree, value: str) -> List[Path]:
    """
    Traverses the original tree recursively through open nodes to find empty nodes.
    Returns list of all paths leading to empty nodes of the same type as the inserted tree.
    """
    path_list = []
    def traverse_recursively(node: DerivationTree, node_value: str, path: List):
        if node.children is None and node.value == node_value:
            # this should never append an empty path, since all trees' root is <start> and value cannot be <start>
            path_list.append(path)
            return
        if node.children is None:
            return

        child_count = 0
        for child in node.children:
            if child.is_open():
                # add child to the path and call the function recursively on child
                current_path = path.copy()
                current_path.append(child_count)
                traverse_recursively(child, node_value, current_path)
            child_count = child_count + 1
        return

    traverse_recursively(tree, value, [])
    return path_list


def create_new_tree(old_tree: DerivationTree, tree_to_insert: DerivationTree, node_id: int, possible_rules,
                    direct: bool = False, expand: bool = False, parent: str = None) \
        -> DerivationTree:
    """Returns tree where tree_to_insert has been inserted as position-th child at node node_id."""
    path = old_tree.find_node(node_id)
    subtree = old_tree.get_subtree(path)

    if direct and not old_tree.children:
        new_subtree = tree_to_insert  # TODO: probably move this down to else and do checking there for more complex insertion
    elif expand and parent is not None:
        new_subtree = expand_node(subtree, tree_to_insert, possible_rules, parent)
    else:
        new_subtree = insert_into_parent(subtree, tree_to_insert, possible_rules)

    return old_tree.replace_path(path, new_subtree)


def insert_into_parent(old_tree: DerivationTree, tree_to_insert: DerivationTree, rule: List[str]) \
        -> DerivationTree:
    """Returns tree where tree_to_insert has been inserted as nth child into the tree."""

    new_children = []

    for item in rule:
        if item == tree_to_insert.value:
            new_children.append(tree_to_insert)

        elif item == old_tree.value:
            new_children.append(old_tree)

        else:
            new_children.append(DerivationTree(item, ()))  # TODO: fix id

    if tree_to_insert.is_open is True:  # TODO: does this cover all options? does not with in regard to grammar rules
        is_open = True
    elif tree_to_insert.is_open is False and old_tree.is_open is False:
        is_open = False
    else:
        is_open = None

    return DerivationTree(old_tree.value, new_children, is_open=is_open)  # TODO: fix id

def insert_into_empty_node(original_tree: DerivationTree, path, inserted_tree: DerivationTree):
    return original_tree.replace_path(path, inserted_tree)

def expand_node(old_node: DerivationTree, tree_to_insert: DerivationTree, rule: List[str], parent: str) \
        -> DerivationTree:
    """creates new parent for tree to insert and expands the old node"""  # TODO: this function does not work as intended
    new_tree_to_insert = DerivationTree(parent, [tree_to_insert])  # TODO: this might cause the trouble

    # TODO: extra function for rule matching
    new_children = []

    for item in rule:
        if item == parent:
            new_children.append(new_tree_to_insert)

        elif item == old_node.value:
            new_children.append(old_node)

        else:
            new_children.append(DerivationTree(item, ()))  # TODO: fix id

    if tree_to_insert.is_open is True:  # TODO: does this cover all options? does not with in regard to grammar rules
        is_open = True
    elif tree_to_insert.is_open is False and old_node.is_open is False:
        is_open = False
    else:
        is_open = None

    return DerivationTree(parent, new_children, is_open=is_open)  # TODO: fix id


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


def identify_insertion_points(tree: DerivationTree, parent_types: List[str], insert_type: str):
    """Checks all nodes for possible insertion points in DFS order and return the corresponding node ids as a list."""
    # TODO: might return path as well
    nodes = deque()  # use deque because of O(1) runtime for pop and append.
    nodes.append(tree)
    parent_nodes = []
    same_type_nodes = []

    while nodes:
        current_node = nodes.pop()
        if current_node.children is not None:
            new_nodes = reversed(list(current_node.children))
            nodes.extend(new_nodes)
        if current_node is not None:  # TODO: is this necessary
            if current_node.value in parent_types:
                parent_nodes.append(current_node.id)
            if current_node.value == insert_type:
                same_type_nodes.append(current_node.id)

    return parent_nodes, same_type_nodes


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
