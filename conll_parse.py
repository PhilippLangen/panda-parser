#!/usr/bin/python2.7
#  -*- coding: iso-8859-15 -*-
__author__ = 'kilian'

from general_hybrid_tree import GeneralHybridTree
import re


test_file = 'examples/Dependency_Corpus.conll'
test_file_modified = 'examples/Dependency_Corpus_modified.conll'

global_s = """1       Viele   _       PIAT    PIAT    _       4       NK      4       NK
2       G�ttinger       _       ADJA    ADJA    _       4       NK      4       NK
3       ``      _       $(      $(      _       4       PUNC    4       PUNC
4       Autonome        _       NN      NN      _       6       SB      6       SB
5       ''      _       $(      $(      _       6       PUNC    6       PUNC
6       laufen  _       VVFIN   VVFIN   _       0       ROOT    0       ROOT
7       zur     _       APPRART APPRART _       6       MO      6       MO
8       Zeit    _       NN      NN      _       7       NK      7       NK
9       mit     _       APPR    APPR    _       6       MO      6       MO
10      einem   _       ART     ART     _       9       NK      9       NK
11      unguten _       ADJA    ADJA    _       9       NK      9       NK
12      Gef�hl  _       NN      NN      _       9       NK      9       NK
13      durch   _       APPR    APPR    _       6       MO      6       MO
14      die     _       ART     ART     _       13      NK      13      NK
15      Stadt   _       NN      NN      _       13      NK      13      NK
16      .       _       $.      $.      _       6       PUNC    6       PUNC"""


def match_line(line):
    match = re.search(r'^([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)$', line)
    return match

# parses a conll file
# file: path to file
# return: list of GeneralHbyridTree
def parse_conll_corpus(file):
    file_content = open(file).readlines()

    trees = []

    i = 0;
    tree_count = 0

    while i < len(file_content):
        tree = None
        line = file_content[i]
        match = match_line(line)
        while match:
            if match.group(1) == '1':
                tree_count += 1
                tree = GeneralHybridTree('tree' + str(tree_count))

            id = match.group(1)
            label = match.group(2)
            pos = match.group(4)
            parent = match.group(7)
            deprel = match.group(8)

            tree.add_node(id, label, pos, True, True)
            tree.add_child(parent, id)
            tree.set_dep_label(id, deprel)

            if parent == '0':
                tree.set_root(id)

            if i < len(file_content):
                line = file_content[i]
                match = match_line(line)
                i += 1
            else:
                match = None

        # Assume empty line, otherwise raise exception
        match = re.search(r'^[^\s]*$', line)
        if not match:
            raise Exception

        if tree:
            # basic sanity checks
            if not tree.rooted():
                raise Exception
            elif tree.n_nodes() != len(tree.full_yield()):
                raise Exception

            trees.append(tree)
            # print tree
    return trees


# Output a hybrid tree, that models the dependency structure of some sentence, in conll format.
# tree: GeneralHybridTree
# return: string (multiple lines!)
def tree_to_conll_str(tree):
    s = '\n'.join([node_to_conll_str(tree, id) for id in tree.full_yield()])
    return s

def node_to_conll_str(tree, id):
    delimiter = '\t'
    s = ''
    s += str(tree.node_index(id) + 1) + delimiter
    s += tree.node_label(id) + delimiter
    s += '_' + delimiter
    s += tree.node_pos(id) + delimiter
    s += tree.node_pos(id) + delimiter
    s += '_' + delimiter
    dependency_info = ''
    if (tree.root() == id):
        dependency_info += '0' + delimiter
    else:
        dependency_info += str(tree.node_index(tree.parent(id)) + 1) + delimiter
    dependency_info += tree.node_dep_label(id)
    s += dependency_info + delimiter + dependency_info
    return s

# Compute UAS, LAS, UEM, LEM, length (of front) for the parsed dependency tree,
# given some reference tree.
# reference: GeneralHybridTree
# test: GeneralHybridTree
# return : 5-tuple of int
def compare_dependency_trees(reference, test):
    UAS = 0
    LAS = 0
    UEM = 0
    LEM = 0

    # sanity check
    if reference.full_yield() != test.full_yield():
        raise Exception

    for i in range(1, len(reference.full_yield()) + 1):
        ref_id = reference.index_node(i)
        test_id = test.index_node(i)
        if reference.root() == ref_id:
            if test.root() == test_id:
                UAS += 1
                if reference.node_dep_label(ref_id) == test.node_dep_label(test_id):
                    LAS += 1
        elif test.root() != test_id:
            ref_parent_i = reference.node_index(reference.parent(ref_id))
            test_parent_i = test.node_index(test.parent(test_id))
            if ref_parent_i == test_parent_i:
                UAS += 1
                if reference.node_dep_label(ref_id) == test.node_dep_label(test_id):
                    LAS += 1

    if reference.n_nodes() == UAS:
        UEM = 1
        if reference.n_nodes() == LAS:
            LEM = 1

    return (UAS, LAS, UEM, LEM, reference.n_nodes())

def score_cmp_dep_trees(reference, test):
    (UAS, LAS, UEM, LEM, length) = compare_dependency_trees(reference, test)
    return (UAS * 1.0 / length, LAS * 1.0 / length, UEM, LEM)


def test_conll_parse():
    trees = parse_conll_corpus(test_file)
    test_trees = parse_conll_corpus(test_file_modified)
    for i in range (len(trees)):
        if i < len(test_trees):
            print compare_dependency_trees(trees[i], test_trees[i])
            print score_cmp_dep_trees(trees[i], test_trees[i])

    print compare_dependency_trees(trees[i], trees[i])
    # print score_cmp_dep_trees(trees[i], test_trees[i])
        # print tree
        # print tree_to_conll_str(tree), '\n '
    # print node_to_conll_str(trees[0], trees[0].root())

    # print tree_to_conll_str(trees[0])


test_conll_parse()
