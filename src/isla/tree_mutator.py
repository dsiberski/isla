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
from typing import Optional, List, Tuple, cast, Union, Set, Dict, Any, Generator

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
        max_num_solutions: Optional[int] = None,
        replace = True  # TODO: decide if I want this as a parameter
) -> Generator[DerivationTree, Any, None]:
    insertion_info = InsertionInfo(grammar, in_tree, old_tree, graph, max_num_solutions)

    return insert_tree_full_coverage(insertion_info, old_tree)

def insert_tree_full_coverage(insertion_info, tree):
    start_nodes = deque() # enables fast FIFO
    start_nodes.append(tree)
    in_trees = deque()
    in_tree = insertion_info.in_tree

    replacement_nodes = []
    results = queue.Queue(3)  # using Queue instead of deque since it has the empty attribute

    while True:
        if insertion_info.max_num_solutions and insertion_info.solutions > insertion_info.max_num_solutions:
            break
        if results.empty():
            try:
                # step 0: get (new) start_node from list and calc new path, repeat steps 1-2 while nodes in start_nodes queue
                subtree = start_nodes.popleft() # traverse breadth first for new starting points
            except IndexError:
                # all possible direct insertions of the current in_tree have been done
                # step 3: set start_node = <start>, extend in_tree by adding parent, TODO: <new_parent> != <old_parent,
                #   repeat steps 1-2
                # TODO: look at all this code and decide if it is done in the right order/could be optimized for the program flow
                subtree = tree
                in_parents = insertion_info.sorted_parents.get(in_tree.value)
                # step 3.1: extend in_tree
                if in_parents:
                    in_trees.extend(extend_tree(insertion_info.canonical_grammar, in_tree, in_parents))

                # step 3.2: get next expanded tree
                try:
                    in_tree = in_trees.popleft() # TODO: fix that pop() also works (JSON3), low priority -> pop()
                    #                                results in nicer order for results, but too many trivial expansions
                    # step 3.2.2: avoid trivial expansion by skipping expansions with the same parent type as last in_tree
                    # new_tree = in_trees.popleft()
                    # # TODO: trying to eliminate trivial extension, but does not work properly
                    # #   the current code also breaks LANG test -> WHY????? low priority
                    # #   MIGHT BE FIXED WHEN PREDICATES WORK (ESPECIALLY NEXT)
                    # while new_tree.value == in_tree.value:
                    #     new_tree = in_trees.popleft()
                    # in_tree = new_tree
                except IndexError:
                    # step 4: terminate if in_tree.value = <start> / old_tree.value and no alternative extension for
                    #   the in_tree exists
                    break

            # step 1: follow path, add siblings to start-nodes list

            # step 1.1: calculate path
            path = get_path(subtree, in_tree, insertion_info.graph)

            if path:
                # step 1.2: follow path through subtree (subtree can be complete old_tree)
                substituted_tree, replacements = walk_path(subtree, insertion_info.in_tree, path, start_nodes)
                replacement_nodes.extend(replacements)

                if substituted_tree:
                    # step 2: found end of path -> try to insert tree
                    new_tree = insert_merged_tree(in_tree, substituted_tree, insertion_info.old_tree, path,
                                                  insertion_info.canonical_grammar)
                        # step 2.1.1: check if expansion fits in_tree + old children
                        # step 2.1.2: collect children's and insert's type and match with rules for parent type
                        # step 2.2: insert for each expansion that fits

                    # step 2.3: check if the tree is valid
                    if new_tree:
                        if valid_result(new_tree, insertion_info.old_tree, insertion_info.in_tree):
                            results.put(new_tree)
                            insertion_info.new_solution()

        else:
            # return calculated results
            yield results.get(timeout=60)  # ensure it will not block forever, deque also has no empty attribute


def match_rule(grammar, rule, in_tree, sibling=DerivationTree("", ())):
    # TODO: cannot add multiple siblings of same type, rename this function since it does not return complete tree?
    new_children = []
    new_sibling = None

    if sibling and sibling.children:
        if in_tree.value == sibling.value:
            siblings = list(sibling.children)
            new_sibling = siblings[0] # TODO: I do not remember why I implemented this, add comment for explanation!
            sibling = None

    for item in rule:
        # TODO: fix that a sibling is only inserted once, try to fix syntax stuff?
        if new_sibling is not None and item == new_sibling.value:
            new_children.append(new_sibling)
            new_sibling = None # TODO: workaround, fix that it works with multiple children instead
            # TODO: if it does not accommodate all siblings, do not return anything -> no valid result; medium priority

        elif sibling and item == sibling.value:
            new_children.append(sibling)

        elif item == in_tree.value:
            new_children.append(in_tree)

        elif not is_nonterminal(item):
            new_children.append(DerivationTree(item, ()))  # TODO: fix id? low priority
            # TODO: should this be None or () ? None might indicate open node, while () indicates closed node?
        else:
            child = grammar.get(item)[0]
            if child and '<' not in child:
                # if the item's child is a terminal node - as denoted by not having "<...>" in the grammar - create a
                # complete terminal node
                new_child = DerivationTree(child[0], ())
                new_children.append(DerivationTree(item, [new_child]))
            else:
                # if nothing fits, add item as open node without children
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

        if len(path) > 1:  # TODO: add comment, it definitely does something relevant (test LANG1)
            path.pop()

    except IndexError:
        path = []
        pass

    return path


def walk_path(substituted_tree, in_tree, path, start_nodes):
    replacement_nodes = []

    for node in path:
        parent = substituted_tree
        if substituted_tree:
            substituted_tree = get_next_subtree(substituted_tree, node)

        # step 1.3: add substituted tree's children to start nodes
        if parent:
            for child in parent.children:
                if child.value == in_tree.value:
                    replacement_nodes.append(parent)
            try:
                # remove nodes that have been traversed before on the path from the start nodes queue
                start_nodes.remove(parent)
            except ValueError:
                pass

            if parent.children:
                for child in parent.children:
                    if is_nonterminal(child.value):
                        # add children to start_nodes queue
                        start_nodes.append(child)

    return substituted_tree, replacement_nodes

def insert_via_replacement(old_tree, sub_tree, in_tree, grammar):
    new_children = []
    new_insert = None
    child_added = False

    for child in sub_tree.children:
        if not child_added and child.value == in_tree.value:
            new_children.append(in_tree)
            new_insert = child
        else:
            new_children.append(child)

    new_subtree = DerivationTree(sub_tree.value, new_children)

    new_substitute_tree = insert_tree(grammar, new_insert, new_subtree, max_num_solutions=1, replace=False)

    try:
        new_tree = old_tree.replace_path(old_tree.find_node(sub_tree), next(new_substitute_tree))
    except StopIteration:
        return None

    return new_tree

def get_next_subtree(tree, node):
    if tree.children:
        for child in tree.children:
            if child.value == node:
                return child
    return None # there is no child matching the path


def insert_merged_tree(in_tree, substituted_tree, old_tree, path, canonical_grammar):
    parent_type = path[len(path) - 1]
    # step 2.1: check if expansion fits in_tree + old children
    possible_rules = canonical_grammar.get(parent_type)
    # TODO: this is recursive insertion currently, do I have to consider parallel insertion? low priority

    new_tree = None
    for rule in possible_rules:
        if parent_type in rule and in_tree.value in rule:
            # TODO: should be fine because recursion, parent_type both on the left and right side of rule
            # step 2.1.1: collect children's and insert's type and match with rules for parent type
            new_children = match_rule(canonical_grammar, rule, in_tree, substituted_tree)
            # step 2.2: insert if True for each expansion that fits
            new_subtree = DerivationTree(parent_type, new_children)  # TODO: id, low priority
            new_tree = old_tree.replace_path(old_tree.find_node(substituted_tree), new_subtree)  # TODO: identify path more efficiently? low priority

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
    # returns list of new trees of parent value with tree as a subtree
    ext_trees = []
    try:
        parents.remove(tree.value) # TODO: can this create problems? low priority
    except ValueError:
        pass
    for parent in parents:
        possible_rules = grammar.get(parent)
        rules = []

        for item in possible_rules:
            if tree.value in item:
                rules.append(item)
        for rule in rules:
            children = match_rule(grammar, rule, tree)
            ext_trees.append(DerivationTree(parent, children))

    return ext_trees


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

class InsertionInfo:
    def __init__(self, grammar, in_tree, old_tree, graph=None, max_num_solutions=None):
        self.grammar = grammar
        self.in_tree = in_tree
        self.old_tree = old_tree
        self.canonical_grammar = canonical(grammar)
        self.sorted_parents = possible_parent_types(
            self.canonical_grammar)  # TODO: try to only initialize sorted_parents when needed later on, low priority
        if graph is None:
            self.graph = GrammarGraph.from_grammar(grammar) # create a grammar graph if it is not available

        self.max_num_solutions = max_num_solutions
        self.solutions = 0

    def new_solution(self):
        self.solutions = self.solutions + 1
