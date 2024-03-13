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
from isla.helpers import is_nonterminal
from test_helpers import canonical # TODO: this should not come from the helpers!!!

from collections import deque


def insert_tree(
        grammar, # TODO: what is its type
        in_tree: DerivationTree,
        old_tree: DerivationTree,
        graph: Optional[GrammarGraph] = None,
        predicate: Optional[str] = None, # TODO: mostly call methods on subtree ?
        max_num_solutions: Optional[int] = None
) -> List[DerivationTree]:
    canonical_grammar = canonical(grammar)
    results = queue.Queue(3) # deque has no empty attribute
    start_nodes = deque() # enables fast FIFO
    start_nodes.append(old_tree)
    sorted_parents = possible_parent_types(canonical_grammar)

    original_in_tree = in_tree # TODO: safekeeping for original inserted tree, fix later
    solution_count = 0
    # substituted_tree = None # TODO: do I want/need this here?
    in_trees = [in_tree]

    # insert into open nodes
    # TODO: this should not be needed
    # if old_tree.is_open():
    #     open_nodes = path_empty_nodes(old_tree, in_tree.value)
    #     result = [old_tree.replace_path(path, in_tree) for path in open_nodes]
    #     results.put(result)

    if graph is None:
        graph = GrammarGraph.from_grammar(grammar) # TODO: might need different parameter here or graph non-optional

    inserted_node = graph.get_node(in_tree.value)

    # start with the shortest path to a possible insertion point TODO: non-trivial path
    #path = [node.symbol for node in graph.shortest_path(graph.root, inserted_node)]
    # remove last element from path since we want to find an insertion point
    #path.pop()
    # remove <start> from path since we already start there
    #path.remove('<start>')

    while True:
        if max_num_solutions and solution_count > max_num_solutions:
            break
        if results.empty():
            try:
                # step 0: get (new) start_node from list and calc new path, repeat steps 1-2 while nodes in start_nodes list
                subtree = start_nodes.popleft() # TODO: decide in which order to traverse subtrees

            except IndexError:
                # all possible direct insertions of the current in_tree have been done
                # step 4: extend in_tree by adding parent, <new_parent> != <old_parent, set start_node = <start>
                # step 4.1: repeat step 1-3
                # TODO: only initialize sorted_parents once here, figure out syntax (try...except...)
                subtree = old_tree
                in_parents = sorted_parents.get(in_tree.value)
                in_trees = extend_tree(canonical_grammar, in_tree, in_parents) # TODO: do I need to compute multiple trees?

                # step 5: terminate if in_tree.value = <start> / old_tree.value # TODO: this will change with predicates!
                in_tree = in_trees[0]
                if in_tree.value == old_tree.value:

                    break
                pass

            # step 1: follow path, add siblings to start-nodes list
            for in_tree in in_trees:
                # step 1.1: calculate path
                path = get_path(subtree, in_tree, graph)

                if path: # TODO: do I want to test this here like this?
                    substituted_tree = walk_path(subtree, path, start_nodes)

                    if substituted_tree:
                        print(substituted_tree.value)
                        # step 2: found end of path -> try to insert tree
                        new_tree = insert_merged_tree(in_tree, substituted_tree, old_tree, path, canonical_grammar)

                        if new_tree:
                            if valid_result(new_tree, old_tree, original_in_tree):
                                results.put(new_tree)
                                solution_count = solution_count + 1

        else:
            # return calculated results
            yield results.get(timeout=60)  # ensure it will not block forever, deque also has no empty attribute


def match_rule(rule, in_tree, sibling=DerivationTree("", ())):
    # TODO: cannot add multiple siblings of same type, rename this function since it does not return complete tree?
    new_children = []
    new_sibling = None

    if sibling and sibling.children: # TODO: do I want to check this here like this?
        if in_tree.value == sibling.value:
            siblings = list(sibling.children)
            new_sibling = siblings[0] # TODO: find out why pop() does not work
            sibling = None

    for item in rule:
        # TODO: fix that a sibling is only inserted once, try to fix syntax stuff?
        if new_sibling is not None and item == new_sibling.value:
            new_children.append(new_sibling)
            new_sibling = None # TODO: workaround, fix that it works with multiple children instead
            # TODO: if it does not accommodate all siblings, do not return anything -> no valid result; medium priority

        elif sibling is not None and item == sibling.value:
            new_children.append(sibling)

        elif item == in_tree.value:
            new_children.append(in_tree)

        elif not is_nonterminal(item):
            new_children.append(DerivationTree(item, ()))  # TODO: fix id? low priority
            # TODO: should this be None or () ? None might indicate open node, while () indicates closed node?
        else:
            new_children.append(DerivationTree(item, None))

    return new_children


def get_path(subtree, in_tree, graph):
    original_node = graph.get_node(subtree.value)
    inserted_node = graph.get_node(in_tree.value)
    try:
        path = [node.symbol for node in graph.shortest_non_trivial_path(original_node, inserted_node)]

        children = []
        for child in subtree.children:
            children.append(child.value)

        if path[0] not in children:
            path.pop(0)

        if len(path) > 1:  # TODO: does this make sense?
            path.pop()

    except IndexError:
        path = []
        pass

    return path


def walk_path(substituted_tree, path, start_nodes):
    for node in path:
        parent = substituted_tree  # TODO: this does not end in the parent, but the substituted_tree; high priority
        if substituted_tree:
            substituted_tree = traverse_shortest_path(substituted_tree, node)
        # TODO: step 1.1: if stuck, check if children in path or empty children, middle priority

        # step 1.2: add substituted tree and sibling to start nodes
        if parent:
            try:
                start_nodes.remove(parent)
            except ValueError:
                pass

            if parent.children:
                for child in parent.children:
                    if is_nonterminal(child.value):
                        # step 1.2: add children to start_nodes list
                        start_nodes.append(child)

    return substituted_tree

def traverse_shortest_path(tree, node):
    if tree.children: # TODO: should I test this here?
        for child in tree.children:
            if child.value == node:
                return child
    return None # TODO: stuck error? low priority, None is fine for now this result is later checked against None


def insert_merged_tree(in_tree, substituted_tree, old_tree, path, canonical_grammar):
    parent_type = path[len(path) - 1]
    # step 2.1: check if expansion fits in_tree + old children # TODO: matching algorithm, medium priority
    possible_rules = canonical_grammar.get(parent_type)
    new_children = list()
    # TODO: this is recursive insertion currently, do I have to consider parallel insertion?

    new_tree = None
    for rule in possible_rules:
        if parent_type in rule and in_tree.value in rule:
            # TODO: should be fine because recursion, parent_type both on the left and right side of rule
            # step 2.1.1: collect children's and insert's type and match with rules for parent type
            new_children = match_rule(rule, in_tree, substituted_tree)
            # step 2.2: insert if True for each expansion that fits
            new_subtree = DerivationTree(parent_type, new_children)  # TODO: id, low priority
            new_tree = old_tree.replace_path(old_tree.find_node(substituted_tree),
                                             new_subtree)  # TODO: identify path more efficiently?

    return new_tree


def valid_result(new_tree, old_tree, original_in_tree):
    # TODO: fix algorithm later on instead of this workaround,
    #  since it only tests for individual characters/words, not structures
    #  low priority
    is_valid_result = True

    for word in str(old_tree).split():
        if word not in str(new_tree):
            is_valid_result = False

    if len(str(new_tree)) < len(str(old_tree)) + len(str(original_in_tree)):
        is_valid_result = False

    if not str(original_in_tree) in str(new_tree):
        is_valid_result = False

    return is_valid_result

def extend_tree(grammar, tree: DerivationTree, parents: List[str]) -> List[DerivationTree]:
    # TODO: seems to have made code a lot slower
    # returns list of new trees of parent value with tree as a subtree
    try:
        parents.remove(tree.value)
    except ValueError:
        pass
    for parent in parents:
        possible_rules = grammar.get(parent)
        rule = possible_rules[0]
        ext_trees = []

        # TODO: only uses last rule containing in_tree currently, do I want more analysis (shortest rule?), low priority
        for item in possible_rules:
            if tree.value in item:
                rule = item
        children = match_rule(rule, tree)
        ext_trees.append(DerivationTree(parent, children))

    return ext_trees




# def path_empty_nodes(tree: DerivationTree, value: str) -> List[Path]:
#     """
#     Traverses the original tree recursively through open nodes to find empty nodes.
#     Returns list of all paths leading to empty nodes of the same type as the inserted tree.
#     """
#     path_list = []
#     def traverse_recursively(node: DerivationTree, node_value: str, path: List):
#         if node.children is None and node.value == node_value:
#             # this should never append an empty path, since all trees' root is <start> and value cannot be <start>
#             path_list.append(path)
#             return
#         if node.children is None:
#             return
#
#         child_count = 0
#         for child in node.children:
#             if child.is_open():
#                 # add child to the path and call the function recursively on child
#                 current_path = path.copy()
#                 current_path.append(child_count)
#                 traverse_recursively(child, node_value, current_path)
#             child_count = child_count + 1
#         return
#
#     traverse_recursively(tree, value, [])
#     return path_list



def possible_parent_types(grammar: CanonicalGrammar) -> Dict:
    """Reverse sorts the grammar, and return all possible parents for the in tree"""
    sorted_parents = dict()

    for parent in grammar:
        for children in grammar[parent]:
            for child in children:
                if child not in sorted_parents:
                    sorted_parents[child] = [parent]
                elif not parent in sorted_parents[child]:
                    sorted_parents[child].append(parent)

    return sorted_parents

