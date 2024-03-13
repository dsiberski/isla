import unittest

from isla.derivation_tree import DerivationTree
from isla.tree_mutator import insert_tree
from grammar_graph.gg import GrammarGraph

from isla.parser import EarleyParser
from isla_formalizations import scriptsizec
from isla_formalizations.xml_lang import XML_GRAMMAR, XML_GRAMMAR_WITH_NAMESPACE_PREFIXES
from test_data import LANG_GRAMMAR, JSON_GRAMMAR
from test_helpers import parse, canonical


class TestTreeMutator(unittest.TestCase):
    def test_insert_lang(self):
        #canonical_grammar = canonical(LANG_GRAMMAR)
        result = list()
        inp = "x := 1 ; y := z"
        tree = DerivationTree.from_parse_tree(parse(inp, LANG_GRAMMAR))

        to_insert = DerivationTree.from_parse_tree(parse("y := 0", LANG_GRAMMAR, "<assgn>"))
        results = insert_tree(LANG_GRAMMAR, to_insert, tree)
        while True:
            try:
                result.append(next(results))
            except StopIteration:
                break

        str_results = [str(t) for t in result]
        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn("x := 1 ; y := 0 ; y := z", map(str, result))
        self.assertIn("y := 0 ; x := 1 ; y := z", map(str, result))
        self.assertIn("x := 1 ; y := z ; y := 0", map(str, result))

        results = insert_tree(LANG_GRAMMAR, to_insert, tree)
        self.assertIn("y := 0 ; x := 1 ; y := z", map(str, results))

        inp = "x := 1 ; y := 2 ; y := z"
        tree = DerivationTree.from_parse_tree(parse(inp, LANG_GRAMMAR))
        results = insert_tree(LANG_GRAMMAR, to_insert, tree)

        result.clear()

        while True:
            try:
                result.append(next(results))
            except StopIteration:
                break

        str_results = [str(t) for t in result]
        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn("x := 1 ; y := 2 ; y := 0 ; y := z", map(str, result))

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

        results = insert_tree(LANG_GRAMMAR, inserted_tree, into_tree)
        result = list()
        while True:
            try:
                result.append(next(results))
            except StopIteration:
                break


        # TODO: invalid result is returned
        str_results = [str(t) for t in result]
        print("\n\n")
        print("\n\n".join(str_results))

        self.assertTrue(all(t.find_node(inserted_tree) for t in result))
        self.assertTrue(all(t.find_node(into_tree.get_subtree((0, 0))) for t in result))
        self.assertTrue(all(t.find_node(into_tree.get_subtree((0, 2, 0))) for t in result))

    # def test_insert_into_empty(self):
    #     canonical_grammar = LANG_GRAMMAR
    #
    #     in_tree = DerivationTree(
    #         '<start>', (
    #             DerivationTree(
    #                 '<stmt>', (
    #                     DerivationTree(
    #                         '<assgn>', (
    #                             DerivationTree('<var>', None, id=245),
    #                             DerivationTree(' := ', (), id=244),
    #                             DerivationTree('<rhs>', None, id=240),
    #                         ), id=246),
    #                 ), id=247),
    #         ), id=237)
    #
    #     tree = DerivationTree('<rhs>', (DerivationTree('<var>', None, id=12249),), id=12250)
    #
    #     results = insert_tree(canonical_grammar, tree, in_tree)
    #     result = next(results)
    #
    #     self.assertTrue(all(t.find_node(tree) for t in result))
    #     self.assertTrue(all(t.find_node(12249) for t in result))
    #     self.assertTrue(all(t.find_node(12250) for t in result))
    #     self.assertTrue(all(t.find_node(245) for t in result))

    def test_insert_lang_3(self):
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

        result = insert_tree(LANG_GRAMMAR, tree, in_tree)

        # TODO: invalid result is returned!
        str_results = [str(t) for t in result]
        print("\n\n")
        print("\n\n".join(str_results))

        self.assertTrue(all(t.find_node(tree) for t in result))
        self.assertTrue(all(t.find_node(12249) for t in result))
        self.assertTrue(all(t.find_node(12250) for t in result))
        self.assertTrue(all(t.find_node(240) for t in result))
        self.assertTrue(all(t.find_node(245) for t in result))

    def test_insert_json_1(self):
        inp = ' { "T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } } '
        tree = DerivationTree.from_parse_tree(parse(inp, JSON_GRAMMAR))
        to_insert = DerivationTree.from_parse_tree(parse(' "key" : { "key" : null } ', JSON_GRAMMAR, "<member>"))

        results = insert_tree(JSON_GRAMMAR, to_insert, tree, max_num_solutions=20)
        str_results = [result.to_string().strip() for result in results]

        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn(
            '{ "key" : { "key" : null } , '
            '"T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } }',
            str_results)

    def test_insert_json_2(self):
        inp = ' { "T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } } '
        tree = DerivationTree.from_parse_tree(parse(inp, JSON_GRAMMAR))
        to_insert = DerivationTree.from_parse_tree(parse(' "cheese" ', JSON_GRAMMAR, "<element>"))

        results = insert_tree(JSON_GRAMMAR, to_insert, tree, max_num_solutions=10)
        str_results = [result.to_string().strip() for result in results]

        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn(
            '['
            ' { "T" : { "I" : true , "" : [ false , "salami" ] , "" : true , "" : null , "" : false } } , '
            '"cheese" ]',
            str_results)

    def test_insert_json_1_subset_1(self):
        inp = ' { "T" : false } '
        tree = DerivationTree.from_parse_tree(parse(inp, JSON_GRAMMAR))
        to_insert = DerivationTree.from_parse_tree(parse(' "key" : { "key" : null } ', JSON_GRAMMAR, "<member>"))

        results = insert_tree(JSON_GRAMMAR, to_insert, tree, max_num_solutions=10)
        str_results = [result.to_string().strip() for result in results]

        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn(
            '{ "key" : { "key" : null } , '
            '"T" : false } }',
            str_results)

    def test_insert_json_1_subset_2(self):
        inp = ' { "T" : { "" : [ false , "salami" ] } } '
        tree = DerivationTree.from_parse_tree(parse(inp, JSON_GRAMMAR))
        to_insert = DerivationTree.from_parse_tree(parse(' "key" : { "key" : null } ', JSON_GRAMMAR, "<member>"))

        results = insert_tree(JSON_GRAMMAR, to_insert, tree, max_num_solutions=10)
        str_results = [result.to_string().strip() for result in results]

        print("\n\n")
        print("\n\n".join(str_results))

        self.assertIn(
            '{ "key" : { "key" : null } , '
            '"T" : { "" : [ false , "salami" ]  } }',
            str_results)


    def test_insert_assignment(self):
        assgn = DerivationTree.from_parse_tree(("<assgn>", None))
        tree = (
        '<start>', [('<stmt>', [('<assgn>', [('<var>', None), (' := ', []), ('<rhs>', [('<var>', None)])])])])
        results = insert_tree(
            LANG_GRAMMAR,
            assgn,
            DerivationTree.from_parse_tree(tree),
            max_num_solutions=None
        )


        # TODO: this test is sensitive to the order of results, fix this!
        self.assertEqual(
            [  # '<var> := <var> ; <assgn> ; <stmt>',
                '<assgn> ; <var> := <var>',
                '<var> := <var> ; <assgn>'],
            list(map(str, results))
        )

    def test_insert_assignment_2(self):
        tree = DerivationTree('<assgn>', id=1)
        in_tree = DerivationTree(
            "<start>", (
                DerivationTree(
                    "<stmt>", (
                        DerivationTree("<assgn>", id=4),
                        DerivationTree(" ; ", (), id=5),
                        DerivationTree("<stmt>", (DerivationTree("<assgn>", id=7),), id=6)),
                    id=3),),
            id=2)
        DerivationTree.next_id = 8

        # TODO: tests for IDs!


        results = insert_tree(
            LANG_GRAMMAR,
            tree,
            in_tree)

        for idx, result in enumerate(results):
            for node_id in range(2, 7):
                self.assertTrue(
                    result.find_node(node_id) is not None,
                    f'Could not find node {node_id} in result no. {idx + 1}: {result}')

    def test_tree_insert_direct_embedding(self):
        # TODO: prob unnecessary, is this insertion into empty node?
        in_tree = DerivationTree("<start>", (DerivationTree("<stmt>", None, id=0),), id=1)
        tree = DerivationTree('<assgn>', id=2)
        results = insert_tree(
            LANG_GRAMMAR,
            tree,
            in_tree)
        self.assertTrue(
            all(result.find_node(node.id) is not None for result in results for _, node in result.paths()))


    def test_insert_xml_1(self):
        # TODO: fix infinite loop

        tree = DerivationTree.from_parse_tree(next(EarleyParser(XML_GRAMMAR).parse("<b>asdf</b>")))
        to_insert = DerivationTree("<xml-open-tag>", [
            DerivationTree("<", []),
            DerivationTree("<id>", [
                DerivationTree("<id-start-char>", [
                    DerivationTree("a", [])])]),
            DerivationTree(">", [])
        ])

        result = insert_tree(XML_GRAMMAR, to_insert, tree)
        str_results = [str(t) for t in result]
        # print("\n\n".join(str_results))
        self.assertIn("<a><b>asdf</b><xml-close-tag>", str_results)
        self.assertIn("<b><a>asdf<xml-close-tag></b>", str_results)
        self.assertIn(
            "<xml-open-tag><b>asdf</b><a><inner-xml-tree><xml-close-tag><inner-xml-tree><xml-close-tag>",
            str_results)

    def test_insert_xml_2(self):
        tree = DerivationTree('<start>', (
            DerivationTree('<xml-tree>', (
                DerivationTree('<xml-openclose-tag>', (
                    DerivationTree('<', ()),
                    DerivationTree('<id>', (
                        DerivationTree('<id-with-prefix>', (
                            DerivationTree('<id-no-prefix>', None),
                            DerivationTree(':', ()),
                            DerivationTree('<id-no-prefix>', None))),)),
                    DerivationTree('/>', ()))),)),))

        to_insert = DerivationTree('<xml-tree>', (
            DerivationTree('<xml-open-tag>', (
                DerivationTree('<', ()),
                DerivationTree('<id>', None),
                DerivationTree(' ', ()),
                DerivationTree('<xml-attribute>', None),
                DerivationTree('>', ()))),
            DerivationTree('<inner-xml-tree>', None),
            DerivationTree('<xml-close-tag>', (
                DerivationTree('</', ()),
                DerivationTree('<id>', None),
                DerivationTree('>', ())))))

        result = insert_tree(XML_GRAMMAR_WITH_NAMESPACE_PREFIXES, to_insert, tree)
        self.assertTrue(result)

        str_results = [str(t) for t in result]
        self.assertIn("<<id> <xml-attribute>><<id-no-prefix>:<id-no-prefix>/></<id>>", str_results)

    def test_insert_xml_4(self):
        to_insert = DerivationTree('<xml-attribute>', (
            DerivationTree('<id>', (
                DerivationTree('<id-with-prefix>', (
                    DerivationTree('<id-no-prefix>', (
                        DerivationTree('<id-start-char>', (
                            DerivationTree('x', (), id=139898),), id=139895),
                        DerivationTree('<id-chars>', (
                            DerivationTree('<id-char>', (
                                DerivationTree('<id-start-char>', (
                                    DerivationTree('m', (), id=139905),), id=139902),), id=139899),
                            DerivationTree('<id-chars>', (
                                DerivationTree('<id-char>', (
                                    DerivationTree('<id-start-char>', (
                                        DerivationTree('l', (), id=139909),), id=139906),), id=139903),
                                DerivationTree('<id-chars>', (
                                    DerivationTree('<id-char>', (
                                        DerivationTree('<id-start-char>', (
                                            DerivationTree('n', (), id=139912),), id=139910),), id=139907),
                                    DerivationTree('<id-chars>', (
                                        DerivationTree('<id-char>', (
                                            DerivationTree('<id-start-char>', (
                                                DerivationTree('s', (), id=139914),), id=139913),), id=139911),),
                                                   id=139908)), id=139904)), id=139900)), id=139896)), id=139891),
                    DerivationTree(':', (), id=139892),
                    DerivationTree('<id-no-prefix>', None, id=139915)), id=139889),), id=139885),
            DerivationTree('="', (), id=139916),
            DerivationTree('<text>', None, id=139917),
            DerivationTree('"', (), id=139918)), id=139884)

        into_tree = DerivationTree('<xml-attribute>', (
            DerivationTree('<id>', (
                DerivationTree('<id-no-prefix>', None, id=138999),), id=137339),
            DerivationTree('="', (), id=137340),
            DerivationTree('<text>', None, id=137341),
            DerivationTree('"', (), id=137342)), id=21903)

        results = insert_tree(
            XML_GRAMMAR_WITH_NAMESPACE_PREFIXES,
            to_insert,
            into_tree,
            GrammarGraph.from_grammar(XML_GRAMMAR_WITH_NAMESPACE_PREFIXES),
            max_num_solutions=30)

        self.assertTrue(
            all(result.find_node(node) is not None for result in results for _, node in to_insert.paths()))
        self.assertTrue(
            all(result.find_node(node) is not None for result in results for _, node in into_tree.paths()))

    def test_insert_scriptsizec(self):
        inserted_tree = DerivationTree(
            '<declaration>', (
                DerivationTree('int ', ()),
                DerivationTree('<id>', None),
                DerivationTree(';', ())))

        into_tree = DerivationTree(
            '<start>', (
                DerivationTree('<statement>', (
                    DerivationTree('<expr>', (
                        DerivationTree('<test>', (
                            DerivationTree('<sum>', (
                                DerivationTree('<term>', (
                                    DerivationTree('<id>', None),)),)),)),)),
                    DerivationTree(';', ()))),))

        result_trees = insert_tree(
            scriptsizec.SCRIPTSIZE_C_GRAMMAR,
            inserted_tree,
            into_tree,
            max_num_solutions=20
        )

        result_trees_str = [str(t) for t in result_trees]
        self.assertIn("{<id>;int <id>;<statements>}", result_trees_str)
        self.assertIn("{int <id>;<id>;<statements>}", result_trees_str)



    # Test deactivated: Should assert that no prefix trees are generated. The implemented
    # check in insert_tree, however, was too expensive for the JSON examples. Stalling for now.
    def test_insert_var(self):
        # TODO: this does not return anything currently
        tree = ('<start>', [('<stmt>', [('<assgn>', None), ('<stmt>', None)])])

        results = insert_tree(LANG_GRAMMAR,
                             DerivationTree("<var>", None),
                             DerivationTree.from_parse_tree(tree))
        str_results = [result.to_string().strip() for result in results]

        print("\n\n")
        print("\n\n".join(str_results))

        #print(list(map(str, results)))
        self.assertEqual(
           ['<var> := <rhs><stmt>',
            '<assgn><var> := <rhs>',
            '<var> := <rhs> ; <assgn><stmt>',
            '<assgn> ; <var> := <rhs> ; <assgn><stmt>',
            '<assgn><var> := <rhs> ; <stmt>',
            '<assgn><assgn> ; <var> := <rhs> ; <stmt>'],
           str_results)
        #     list(map(str, results))
        # )

if __name__ == '__main__':
    unittest.main()