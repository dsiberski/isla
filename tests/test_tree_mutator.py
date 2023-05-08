import unittest

from isla.derivation_tree import DerivationTree
from isla.tree_mutator import insert_tree

from test_data import LANG_GRAMMAR, JSON_GRAMMAR
from test_helpers import parse, canonical


class TestTreeMutator(unittest.TestCase):
    def test_insert_lang(self):
        canonical_grammar = canonical(LANG_GRAMMAR)

        inp = "x := 1 ; y := z"
        tree = DerivationTree.from_parse_tree(parse(inp, LANG_GRAMMAR))

        to_insert = DerivationTree.from_parse_tree(parse("y := 0", LANG_GRAMMAR, "<assgn>"))
        results = insert_tree(canonical_grammar, to_insert, tree)
        self.assertIn("x := 1 ; y := 0 ; y := z", map(str, results))

        results = insert_tree(canonical_grammar, to_insert, tree)
        self.assertIn("y := 0 ; x := 1 ; y := z", map(str, results))

        inp = "x := 1 ; y := 2 ; y := z"
        tree = DerivationTree.from_parse_tree(parse(inp, LANG_GRAMMAR))
        results = insert_tree(canonical_grammar, to_insert, tree)
        self.assertIn("x := 1 ; y := 2 ; y := 0 ; y := z", map(str, results))

    def test_insert_lang_2(self):
        inserted_tree = DerivationTree('<assgn>', (
            DerivationTree('<var>', None),
            DerivationTree(' := ', ()),
            DerivationTree('<rhs>', None)))

        into_tree = DerivationTree('<start>', (
            DerivationTree('<stmt>', (
                DerivationTree('<assgn>', (
                    DerivationTree('<var>', None),
                    DerivationTree(' := ', ()),
                    DerivationTree('<rhs>', (
                        DerivationTree('<digit>', None),)))),
                DerivationTree(' ; ', ()),
                DerivationTree('<stmt>', (
                    DerivationTree('<assgn>', (
                        DerivationTree('<var>', None),
                        DerivationTree(' := ', ()),
                        DerivationTree('<rhs>', (
                            DerivationTree('<var>', None),)))),)))),))

        result = insert_tree(canonical(LANG_GRAMMAR), inserted_tree, into_tree)

        # str_results = [str(t) for t in result]
        # print("\n\n".join(str_results))

        self.assertTrue(all(t.find_node(inserted_tree) for t in result))
        self.assertTrue(all(t.find_node(into_tree.get_subtree((0, 0))) for t in result))
        self.assertTrue(all(t.find_node(into_tree.get_subtree((0, 2, 0))) for t in result))

    def test_insert_lang_3(self):
        canonical_grammar = canonical(LANG_GRAMMAR)

        in_tree = DerivationTree(
            '<start>', (
                DerivationTree(
                    '<stmt>', (
                        DerivationTree(
                            '<assgn>', (
                                DerivationTree('<var>', None, id=245),
                                DerivationTree(' := ', (), id=244),
                                DerivationTree('<rhs>', (
                                    DerivationTree(
                                        '<var>', (DerivationTree('x', (), id=12249),),
                                        id=12250),
                                ), id=240)
                            ), id=246),
                    ), id=247),
            ), id=237)

        tree = DerivationTree('<rhs>', (DerivationTree('<var>', None, id=12251),), id=12252)

        result = insert_tree(canonical_grammar, tree, in_tree)

        self.assertTrue(all(t.find_node(tree) for t in result))
        self.assertTrue(all(t.find_node(12249) for t in result))
        self.assertTrue(all(t.find_node(12250) for t in result))
        self.assertTrue(all(t.find_node(240) for t in result))
        self.assertTrue(all(t.find_node(245) for t in result))

    def test_insert_json_1(self):
        inp = ' { "T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } } '
        tree = DerivationTree.from_parse_tree(parse(inp, JSON_GRAMMAR))
        to_insert = DerivationTree.from_parse_tree(parse(' "key" : { "key" : null } ', JSON_GRAMMAR, "<member>"))

        results = insert_tree(canonical(JSON_GRAMMAR), to_insert, tree)
        str_results = [result.to_string().strip() for result in results]

        self.assertIn(
            '{ "key" : { "key" : null } , '
            '"T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } }',
            str_results)