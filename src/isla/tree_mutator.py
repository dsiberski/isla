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

    sorted_parents = dict()

    while True:
        if max_num_solutions and solution_count > max_num_solutions:
            break
        if results.empty():
            #start_nodes.clear() # TODO: delete
            try:
                # step 0: get (new) start_node from list and calc new path, repeat steps 1-2 while nodes in start_nodes list
                subtree = start_nodes.popleft() # TODO: decide in which order to traverse subtrees

            except IndexError:
                # all possible direct insertions of the current in_tree have been done
                # step 4: extend in_tree by adding parent, <new_parent> != <old_parent, set start_node = <start>
                # TODO: only initialize sorted_parents once here, figure out syntax (try...except...)
                subtree = old_tree
                sorted_parents = possible_parent_types(canonical_grammar)
                in_parents = sorted_parents.get(in_tree.value)
                in_trees = extend_tree(canonical_grammar, in_tree, in_parents) # TODO: do I need to compute multiple trees?
                # TODO: calculate new path!!!
                # step 4.1: repeat step 1-3
                in_tree = in_trees[0]

                if in_tree.value == old_tree.value:
                    # step 5: terminate if in_tree.value = <start> / old_tree.value # TODO: this will change with predicates!
                    break
                pass

            # step 1: follow path, add siblings to start-nodes list
            # TODO: save derivation_tree path for insertion using "replace path" function
            new_start_nodes = []

            for in_tree in in_trees:

                original_node = graph.get_node(subtree.value)
                inserted_node = graph.get_node(in_tree.value)
                try:
                    path = [node.symbol for node in graph.shortest_non_trivial_path(original_node, inserted_node)]
                    if '<start>' in path:
                        path.remove('<start>')  # TODO: properly prune path; high priority
                    # path.pop(0)
                    if len(path) > 1: # TODO: does this make sense?
                        path.pop()
                except IndexError:
                    path = []
                    pass


                substituted_tree = subtree
                if path: # TODO: do I want to test this here like this?
                    for node in path:
                        if substituted_tree and substituted_tree.children:
                            for child in substituted_tree.children:
                                if is_nonterminal(child.value):
                                    # step 1.2: add children to start_nodes list
                                    start_nodes.append(child)

                        substituted_tree = traverse_shortest_path(subtree, node)
                        # TODO: step 1.1: if stuck, check if children in path or empty children, middle priority
                        # try:
                        #     new_start_nodes.remove(subtree)
                        # except ValueError:
                        #     pass

                        # if new_start_nodes:
                        #     start_nodes.extend([new_start_nodes]) # TODO: filter this for predicates, lower priority

                    if substituted_tree:
                        # step 2: found end of path -> check for possible expansions
                        parent_type = path[len(path) - 1]
                        # step 2.1: check if expansion fits in_tree + old children # TODO: matching algorithm, medium priority
                        possible_rules = canonical_grammar.get(parent_type)
                        new_children = list()
                        # TODO: this is recursive insertion currently, do I have to consider parallel insertion?
                        for rule in possible_rules:
                            if parent_type in rule and in_tree.value in rule:
                                # TODO: should be fine because recursion, parent_type both on the left and right side of rule
                                # TODO: decide how to handle recursion cases where parent_type = in_tree.value -> reduce old node?
                                # step 2.1.1: collect children's and insert's type and match with rules for parent type
                                new_children = match_rule(rule, in_tree, substituted_tree)

                        # step 2.2: insert if True for each expansion that fits
                        new_subtree = DerivationTree(parent_type, new_children) # TODO: id, low priority
                        new_tree = old_tree.replace_path(old_tree.find_node(substituted_tree), new_subtree) # TODO: identify path more efficiently?

                        # TODO: fix algorithm later on instead of this workaround,
                        #  since it only tests for individual characters/words, not structures
                        is_in_tree = True
                        for word in str(old_tree).split():
                            if word not in str(new_tree):
                                is_in_tree = False

                        if len(str(new_tree)) < len(str(old_tree)) + len(str(original_in_tree)):
                            is_in_tree = False

                        if is_in_tree and str(original_in_tree) in str(new_tree):
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

        else:
            new_children.append(DerivationTree(item, None))  # TODO: fix id? low priority
            # TODO: should this be None or () ?

    return new_children



def traverse_shortest_path(tree, node):
    if tree.children: # TODO: should I test this here?
        for child in tree.children:
            if child.value == node:
                return child
    return None # TODO: stuck error? low priority, None is fine for now this result is later checked against None


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

        # TODO: only extends for shortest rule currently, might also add different rules? low priority
        for item in possible_rules:
            if len(item) < len(rule):
                rule = item
        children = match_rule(rule, tree)
        ext_trees.append(DerivationTree(parent, children))

    return ext_trees

    # TODO: old code
    # parent = parents[0]
    # possible_rules = grammar.get(parent)
    # rule = possible_rules[0]
    #
    # # TODO: only extends for shortest rule currently, might also add different rules? low priority
    # for item in possible_rules:
    #     if len(item) < len(rule):
    #         rule = item
    # children = match_rule(rule, tree)
    # return DerivationTree(parent, children)


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


# def create_new_tree(old_tree: DerivationTree, tree_to_insert: DerivationTree, node_id: int, possible_rules,
#                     direct: bool = False, expand: bool = False, parent: str = None) \
#         -> DerivationTree:
#     """Returns tree where tree_to_insert has been inserted as position-th child at node node_id."""
#     path = old_tree.find_node(node_id)
#     subtree = old_tree.get_subtree(path)
#
#     if direct and not old_tree.children:
#         new_subtree = tree_to_insert  # TODO: probably move this down to else and do checking there for more complex insertion
#     elif expand and parent is not None:
#         new_subtree = expand_node(subtree, tree_to_insert, possible_rules, parent)
#     else:
#         new_subtree = insert_into_parent(subtree, tree_to_insert, possible_rules)
#
#     return old_tree.replace_path(path, new_subtree)
#
#
# def insert_into_parent(old_tree: DerivationTree, tree_to_insert: DerivationTree, rule: List[str]) \
#         -> DerivationTree:
#     """Returns tree where tree_to_insert has been inserted as nth child into the tree."""
#
#     new_children = []
#
#     for item in rule:
#         if item == tree_to_insert.value:
#             new_children.append(tree_to_insert)
#
#         elif item == old_tree.value:
#             new_children.append(old_tree)
#
#         else:
#             new_children.append(DerivationTree(item, ()))  # TODO: fix id
#
#     if tree_to_insert.is_open is True:  # TODO: does this cover all options? does not with in regard to grammar rules
#         is_open = True
#     elif tree_to_insert.is_open is False and old_tree.is_open is False:
#         is_open = False
#     else:
#         is_open = None
#
#     return DerivationTree(old_tree.value, new_children, is_open=is_open)  # TODO: fix id
#
# def insert_into_empty_node(original_tree: DerivationTree, path, inserted_tree: DerivationTree):
#     return original_tree.replace_path(path, inserted_tree)
#
# def expand_node(old_node: DerivationTree, tree_to_insert: DerivationTree, rule: List[str], parent: str) \
#         -> DerivationTree:
#     """creates new parent for tree to insert and expands the old node"""  # TODO: this function does not work as intended
#     new_tree_to_insert = DerivationTree(parent, [tree_to_insert])  # TODO: this might cause the trouble
#
#     # TODO: extra function for rule matching
#     new_children = []
#
#     for item in rule:
#         if item == parent:
#             new_children.append(new_tree_to_insert)
#
#         elif item == old_node.value:
#             new_children.append(old_node)
#
#         else:
#             new_children.append(DerivationTree(item, ()))  # TODO: fix id
#
#     if tree_to_insert.is_open is True:  # TODO: does this cover all options? does not with in regard to grammar rules
#         is_open = True
#     elif tree_to_insert.is_open is False and old_node.is_open is False:
#         is_open = False
#     else:
#         is_open = None
#
#     return DerivationTree(parent, new_children, is_open=is_open)  # TODO: fix id
#
#
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
#
#
# def identify_insertion_points(tree: DerivationTree, parent_types: List[str], insert_type: str):
#     """Checks all nodes for possible insertion points in DFS order and return the corresponding node ids as a list."""
#     # TODO: might return path as well
#     nodes = deque()  # use deque because of O(1) runtime for pop and append.
#     nodes.append(tree)
#     parent_nodes = []
#     same_type_nodes = []
#
#     while nodes:
#         current_node = nodes.pop()
#         if current_node.children is not None:
#             new_nodes = reversed(list(current_node.children))
#             nodes.extend(new_nodes)
#         if current_node is not None:  # TODO: is this necessary
#             if current_node.value in parent_types:
#                 parent_nodes.append(current_node.id)
#             if current_node.value == insert_type:
#                 same_type_nodes.append(current_node.id)
#
#     return parent_nodes, same_type_nodes
#
#
# def identify_rule_expansions(grammar: CanonicalGrammar, insert_type: str, parent_type: str) -> List[List[str]]:
#     """
#     Return all rule expansions that fit both the type of the tree that will be inserted and the parent node into
#     which it will be inserted for direct recursive insertion. The resulting list is sorted by length of the rules, so
#     in case of multiple matching option the shortest will be considered first.
#     """
#     matching_rules = []
#     options = grammar[parent_type]
#
#     for rule in options:
#         valid_rule = True
#         if insert_type not in rule:
#             valid_rule = False
#         if parent_type not in rule:
#             valid_rule = False
#
#         if valid_rule:
#             matching_rules.append(rule)
#
#     matching_rules.sort(key=len)  # return simplest solution first, defined by length
#     return matching_rules
