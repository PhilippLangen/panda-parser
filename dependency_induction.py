__author__ = 'kilian'

from general_hybrid_tree import GeneralHybridTree
from dcp import DCP_rule, DCP_term, DCP_var, DCP_index, DCP_string
from lcfrs import LCFRS, LCFRS_lhs, LCFRS_var
from decomposition import join_spans, fanout_limited_partitioning, left_branching_partitioning, right_branching_partitioning
from parsing import LCFRS_parser


###################   Top level methods for grammar induction.   ###################


def induce_grammar(trees, nont_labelling, term_labelling, recursive_partitioning, start_nont = 'START'):
    """
    Top level method to induce an LCFRS/DCP-hybrid grammar for dependency parsing.
    :rtype: LCFRS
    :param trees: Iterator over GeneralHybridTree (i.e. list (or Generator for lazy IO))
    :param nont_labelling: GeneralHybridTree, NodeIds, Top_max, Bottom_max, Fanout -> str
    :param term_labelling: GeneralHybridTree, NodeId -> str
    :param recursive_partitioning: GeneralHybridTree -> RecursivePartitioning
    :param start_nont: str
    :return: LCFRS
    """
    grammar = LCFRS(start_nont)
    n_trees = 0
    for tree in trees:
        n_trees += 1

        rec_par_int = recursive_partitioning(tree)

        rec_par_nodes = tree.node_id_rec_par(rec_par_int)

        (_, _, nont_name) = add_rules_to_grammar_rec(tree, rec_par_nodes, grammar, nont_labelling, term_labelling)

        # Add rule from top start symbol to top most nonterminal for the hybrid tree
        lhs = LCFRS_lhs(start_nont)
        lhs.add_arg([LCFRS_var(0, 0)])
        rhs = [nont_name]
        dcp_rule = DCP_rule(DCP_var(-1, 0), [DCP_var(0, 0)])

        grammar.add_rule(lhs, rhs, 1.0, [dcp_rule])

    grammar.make_proper()
    return (n_trees, grammar)

# Nonterminal labelling strategies
def strict_pos( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'strict', lambda tree, id, dep: tree.node_pos(id))
def strict_pos_dep( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'strict'
                           , lambda tree, id, dep:
        tree.node_pos(id) + ':' + tree.node_dep_label(id) if dep
        else tree.node_pos(id))
def strict_word( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'strict', lambda tree, id, dep: tree.node_label(id))
def child_pos ( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'child', lambda tree, id, dep: tree.node_pos(id))
def child_pos_dep( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'child'
                           , lambda tree, id, dep:
        tree.node_pos(id) + ':' + tree.node_dep_label(id) if dep
        else tree.node_pos(id))
def child_word( a, b, c, d, e):
    return nonterminal_str(a, b, c, d, e, 'child', lambda tree, id, dep: tree.node_label(id))


# Terminal labelling strategies
def term_word( tree, id):
    return tree.node_label(id)
def term_pos(tree, id):
    return tree.node_pos(id)

# and corresponding tree-yield strategies for parsing
def word_yield(tree):
    return tree.labelled_yield()
def pos_yield(tree):
    return tree.pos_yield()

# Recursive partitioning strategies
def left_branching(tree):
    return left_branching_partitioning(len(tree.id_yield()))
def right_branching(tree):
    return right_branching_partitioning(len(tree.id_yield()))
def direct_extraction(tree):
    return tree.recursive_partitioning()
fanout_k = lambda tree, k: fanout_limited_partitioning(tree.recursive_partitioning(), k)
def fanout_1(tree):
    return fanout_k(tree, 1)
def fanout_2(tree):
    return fanout_k(tree, 2)
def fanout_3(tree):
    return fanout_k(tree, 3)
def fanout_4(tree):
    return fanout_k(tree, 4)
def fanout_5(tree):
    return fanout_k(tree, 5)
def fanout_6(tree):
    return fanout_k(tree, 6)
def fanout_7(tree):
    return fanout_k(tree, 7)
def fanout_8(tree):
    return fanout_k(tree, 8)



###################################### Recursive Rule extraction method ###################################


def add_rules_to_grammar_rec(tree, rec_par, grammar, nont_labelling, term_labelling):
    """
    Extract LCFRS/DCP-hybrid-rules from some hybrid tree, according to some recursive partitioning
    and add them to some grammar.
    :rtype: ([[str]],[[str]],str)
    :param tree: GeneralHybridTree
    :param rec_par: pair of (list of string) and (list of rec_par))
    :param grammar: LCFRS
    :param nont_labelling: GeneralHybridTree, Top_max, Bottom_max, Fanout -> string
    :param term_labelling: GeneralHybridTree, node_id -> string
    :return: (top_max, bottom_max, nont_name) of root in rec_par :raise Exception:
    """
    (node_ids, children) = rec_par

    # Sanity check
    if children and len(node_ids) == 1:
        raise Exception('A singleton in a recursive partitioning should not have children.')

    if len(node_ids) == 1:
        t_max = top_max(tree, node_ids)
        b_max = bottom_max(tree, node_ids)

        dependency_label = tree.node_dep_label(node_ids[0])
        dcp = [create_leaf_DCP_rule(b_max, dependency_label)]
        lhs = create_leaf_lcfrs_lhs(tree, node_ids, t_max, b_max, nont_labelling, term_labelling)

        grammar.add_rule(lhs, [], 1.0, dcp)

        return (t_max, b_max, lhs.nont())

    else:
        # Create rules for children and obtain top_max and bottom_max of child nodes
        child_t_b_max = []
        for child in children:
            child_t_b_max.append(add_rules_to_grammar_rec(tree, child, grammar, nont_labelling, term_labelling))

        # construct DCP equations
        dcp = []
        t_max = top_max(tree, node_ids)
        b_max = bottom_max(tree, node_ids)

        # create equations for synthesized attributes on LHS
        for arg in range(len(t_max)):
            dcp.append(create_dcp_rule(-1, len(b_max) + arg, t_max, b_max, child_t_b_max))

        # create equations for inherited attributes on RHS
        for cI in range(len(child_t_b_max)):
            child = child_t_b_max[cI]
            for arg in range(len(child[1])):
                dcp.append(create_dcp_rule(cI, arg, t_max, b_max, child_t_b_max))

         # create LCFRS-rule, attach dcp and add to grammar
        lhs = create_lcfrs_lhs(tree, node_ids, t_max, b_max, children, nont_labelling)
        rhs = [nont_name for (_, _, nont_name) in child_t_b_max]
        grammar.add_rule(lhs, rhs, 1.0, dcp)

        return t_max, b_max, lhs.nont()



def create_dcp_rule(mem, arg, top_max, bottom_max, children):
    """
    Create DCP equation for some synthesized attributes of LHS nont
    or inherited attributes of RHS nont of an LCFRS-sDCP-hybrid rule.
    :rtype: DCP_rule
    :param mem: int                            (member part of attribute: -1 for LHS, >=0 for RHS)
    :param arg: int                            (argument part of attribute: >= 0)
    :param top_max:    list of list of string  (top_max of nont on LHS)
    :param bottom_max: list of list of string  (bottom_max of nont on LHS)
    :param children: list of pairs of list of list of string
                                       (pair of (top_max, bottom_max) for every nont on RHS)
    :return: DCP_rule :raise Exception:
    """
    lhs = DCP_var(mem, arg)
    rhs = []
    if mem < 0:
        conseq_ids = top_max[arg-len(bottom_max)][:]
    else:
        conseq_ids = children[mem][1][arg][:]
    while conseq_ids:
        id = conseq_ids[0]
        if mem >= 0:
            c_index = -1
        else:
            c_index = 0
        match = False
        while c_index < len(children) and not match:
            if c_index >= 0:
                child = children[c_index]
            else:
                # If equation for inherited arguments of some nont on RHS is computed,
                # the inherited arguments of the LHS are used in addition.
                # The second component is empty, which allows for some magic below!
                child = (bottom_max, [])
            t_seq_index = 0
            while t_seq_index < len(child[0]) and not match:
                t_seq = child[0][t_seq_index]
                # check if correct child synthesized attribute was found
                if id == t_seq[0]:
                    # sanity check, is t_seq a prefix of conseq_ids
                    if conseq_ids[:len(t_seq)] != t_seq:
                        raise Exception
                    # Append variable corresponding to synthesized attribute of nont on RHS.
                    # Or, append variable corresponding to inherited attribute of nont on LHS,
                    # where len(child[1]) evaluates to 0 as intended.
                    rhs.append(DCP_var(c_index, len(child[1]) + t_seq_index))
                    # remove matched prefix from conseq_ids
                    conseq_ids = conseq_ids[len(t_seq):]
                    # exit two inner while loops
                    match = True
                t_seq_index += 1
            c_index += 1
        # Sanity check, that attribute was matched:
        if not match:
            raise Exception('Expected ingredient for synthesised or inherited argument was not found.')
    return DCP_rule(lhs, rhs)


def create_lcfrs_lhs(tree, node_ids, t_max, b_max, children, nont_labelling):
    """
    Create the LCFFRS_lhs of some LCFRS-DCP hybrid rule.
    :rtype: LCFRS_lhs
    :param tree:     GeneralHybridTree
    :param node_ids: list of string (node in an recursive partitioning)
    :param t_max:    top_max of node_ids
    :param b_max:    bottom_max of node ids
    :param children: list of pairs of list of list of string
#                    (pairs of top_max / bottom_max of child nodes in recurisve partitioning)
    :param nont_labelling: GeneralHybridTree, Top_max, Bottom_max, Fanout -> String
    :return: LCFRS_lhs :raise Exception:
    """
    positions = map(tree.node_index, node_ids)
    spans = join_spans(positions)

    children_spans = map(join_spans, [map(tree.node_index, ids) for (ids,_) in children])

    lhs = LCFRS_lhs(nont_labelling(tree, node_ids, t_max, b_max, len(spans)))
    for (low, high) in spans:
        arg = []
        i = low
        while (i <= high):
            mem = 0
            match = False
            while mem < len(children_spans) and not match:
                child_spans = children_spans[mem]
                mem_arg = 0
                while mem_arg < len(child_spans) and not match:
                    child_span = child_spans[mem_arg]
                    if child_span[0] == i:
                        arg.append(LCFRS_var(mem, mem_arg))
                        i = child_span[1] + 1
                        match = True
                    mem_arg += 1
                mem += 1
            # Sanity check
            if not match:
                raise Exception('Expected ingredient for LCFRS argument was not found.')
        lhs.add_arg(arg)

    return lhs


def create_leaf_DCP_rule(bottom_max, dependency_label):
    """
    Creates a DCP rule for a leaf of the recursive partitioning.
    Note that the linked LCFRS-rule has an empty RHS.
    If the corresponding node in the hybrid tree is not a leaf, i.e. bottom_max != [],
    there is exactly one inherited argument <0,0>. The only synthesized argument
    generates a DCP_term of the form "[0:{dependency_label}]( <0,0> ).
    Otherwise, there is no inherited argument, and the only synthesized argument
    generates a DCP_term of the form "[0:{dependency_label}]( )".
    :rtype: DCP_rule
    :param bottom_max: list of list of string
    :param dependency_label: dependency label linked to the corresponding terminal
    :return: DCP_rule
    """
    if bottom_max:
        arg = 1
    else:
        arg = 0
    lhs = DCP_var(-1, arg)
    term_head = DCP_index(0, dependency_label)
    if bottom_max:
        term_arg = [DCP_var(-1, 0)]
    else:
        term_arg = []
    rhs = [DCP_term(term_head, term_arg)]
    return DCP_rule(lhs, rhs)


def create_leaf_lcfrs_lhs(tree, node_ids, t_max, b_max, nont_labelling, term_labelling):
    """
    Create LCFRS_lhs for a leaf of the recursive partitioning,
    i.e. this LCFRS creates (consumes) exactly one terminal symbol.
    :param tree: GeneralizedHybridTree
    :param node_ids: list of string
    :param t_max: top_max of node_ids
    :param b_max: bottom_max of node_ids
    :param nont_labelling: GeneralHybridTree, Top_max, Bottom_max, Fanout -> string
    :param term_labelling: GeneralHybridTree, node_id -> string
    :return: LCFRS_lhs
    """

    # Build LHS
    lhs = LCFRS_lhs(nont_labelling(tree, node_ids, t_max, b_max, 1))
    id = node_ids[0]
    arg = [term_labelling(tree, id)]
    lhs.add_arg(arg)
    return lhs



######################   Auxiliary: top_max and bottom_max    #################################################


def top_max(tree, id_set):
    """
    Compute list of node ids that delimit id_set from the top
    and group maximal subsets of neighbouring nodes together.
    :rtype: [[str]]
    :param tree: GeneralHybridTree
    :param id_set: list of string
    :return: list of list of string
    """
    return maximize(tree, top(tree, id_set))


def bottom_max(tree, id_set):
    """
    Compute list of node ids that delimit id_set from the bottom.
    and group maximal subsets of neighbouring nodes together.
    :rtype: [[str]]
    :param tree: GeneralHybridTree
    :param id_set: list of string
    :return: list of list of string
    """
    return maximize(tree, bottom(tree, id_set))


def top(tree, id_set):
    """
    Compute list of node ids that delimit id_set from the top.
    :rtype: [[str]]
    :param tree: GeneralHybridTree
    :param id_set: list of string  (node ids)
    :return: list of string  (node ids)
    """
    top_nodes = [id for id in id_set if tree.parent(id) not in id_set]
    return top_nodes


def bottom(tree, id_set):
    """
    Compute list of node ids that delimit id_set from the bottom.
    :rtype: [[str]]
    :param tree: list of node ids that delimit id_set from the bottom.
    :param id_set: list of string  (node ids)
    :return: list of string  (node ids)
    """
    bottom_nodes = [id for id in tree.id_yield()
                    if tree.parent(id) in id_set and id not in id_set]
    return bottom_nodes


def maximize(tree, id_set):
    """
    Group maximal subsets of neighbouring nodes together.
    :param tree: GeneralHybridTree
    :param id_set: list of string
    :return: list of list of string
    """
    nodes = id_set[:]
    max_list = []
    while len(nodes) > 0:
        id = nodes[0]

        # Assume that the following two lists contain tree nodes, that are
        # siblings, ordered from left to right.
        all_siblings = tree.siblings(id)
        present_siblings = [id for id in all_siblings if id in nodes]

        nodes = [id for id in nodes if id not in present_siblings]

        while len(present_siblings) > 0:
            i = all_siblings.index(present_siblings[0])
            j = 1
            while j < len(present_siblings) and all_siblings[i + j] == present_siblings[j]:
                j += 1
            max_list += [present_siblings[:j]]
            present_siblings = present_siblings[j:]

    return max_list



######################  Implementation of nonterminal naming strategies     ####################################

lcfrs_fanout_in_nonterminal_name = True


def nonterminal_str(tree, node_ids, t_max, b_max, fanout, labelling_strategy, node_name):
    """
    Auxiliary function to implement nonterminal labelling strategies.
    :rtype: str
    :param tree:    GeneralHybridTree
    :param node_ids: NodeIds
    :param t_max:   top_max
    :param b_max:   bottom_max
    :param fanout:  int
    :param labelling_strategy: string (strict or child)
    :param node_name: GeneralHybridTree, NodeId -> String
    :return: :raise Exception:
    """
    tree_node_name = lambda id, dep: node_name(tree, id, dep)
    if not lcfrs_fanout_in_nonterminal_name:
        fanout = ''
    else:
        fanout = str(fanout) + ':'
    if labelling_strategy == 'strict':
        return strict_labeling(tree, node_ids, t_max, b_max, fanout, tree_node_name).replace(' ', '').replace('*', '')
    elif labelling_strategy == 'child':
        return child_labeling(tree, node_ids, t_max, b_max, fanout, tree_node_name).replace(' ', '').replace('*', '')
    else:
        raise Exception('Unknown labelling scheme \'' + labelling_strategy +'\'')


def strict_labeling(tree, node_ids, t_max, b_max, fanout, tree_node_name):
    """
    Create nonterminal label, according to strict labeling strategy.
    :rtype: str
    :param tree:   GeneralHybridTree
    :param node_ids: Node Ids
    :param t_max:  top_max
    :param b_max:  bottom_max
    :param fanout: int
    :param tree_node_name: NodeId -> string
    :return: string
    """
    with_dep_label = []
    if len(node_ids) == 1:
        id_seqs = b_max
        with_dep_label = t_max
    else:
        id_seqs = b_max + t_max

    arg_dep = argument_dependencies(tree, id_seqs + with_dep_label)
    strict_label = ','.join(
        ['#'.join(map(lambda id: tree_node_name(id, False), id_seq)) for id_seq in id_seqs]
        +
        ['#'.join(map(lambda id: tree_node_name(id, True), id_seq)) for id_seq in with_dep_label]
    )

    return '{' + fanout + strict_label + ',' + arg_dep + '}'


def child_labeling(tree, node_ids, t_max, b_max, fanout, tree_node_name):
    """
    Create nonterminal label, according to child labeling strategy.
    :rtype: str
    :param tree:  GeneralHybridTree
    :param node_ids: NodeIds
    :param t_max: top_max
    :param b_max: top_max
    :param fanout: int
    :param tree_node_name: NodeId -> string
    :return: string
    """
    with_dep_label = []
    if len(node_ids) == 1:
        id_seqs = b_max
        with_dep_label = t_max
    else:
        id_seqs = b_max + t_max
    arg_dep = argument_dependencies(tree, id_seqs + with_dep_label)

    child_label = ','.join([child_of(tree, node_ids, id_seq, tree_node_name) for id_seq in id_seqs]
        +
        ['#'.join(map(lambda id: tree_node_name(id, True), id_seq)) for id_seq in with_dep_label]
    )

    return '{' + fanout + child_label + ',' + arg_dep + '}'


def child_of(tree, node_ids, id_seq, tree_node_name):
    """
    Auxiliary function, that replaces consecutive tree ids by the appropriate
    string in child labeling.
    :param tree: GeneralHybridTree
    :param id_seq: list of NodeIds
    :param tree_node_name: NodeId -> string
    :return: string :raise Exception:
    """
    if len(id_seq) == 1:
        return tree_node_name(id_seq[0], False)
    elif len(id_seq) > 1:
        # assuming that id_seq are siblings in tree, and thus also not at root level
        return 'children-of(' + tree_node_name(tree.parent(id_seq[0]), False) + ')'
    else:
        raise Exception('Empty components in top_max!')


def argument_dependencies(tree, id_seqs):
    """
    Compute a string that represents, how the arguments of some dcp-nonterminal
    depend on one another.
    :rtype: str
    :param tree: GeneralHybridTree
    :param id_seqs: list of list of string (Concatenation of top_max and bottom_max)
    :return: string
        (of the form "1.4(0).2(3(5))": 1, 4 and 2 are independent, 4 depends on 0, etc.)
    """
    ancestor = {}
    descendants = {}

    # Build a table with the dependency relation of arguments.
    # The table holds the indices of a node in name_seqs.
    for i in range(len(id_seqs)):
        name_seq = id_seqs[i]
        for j in range(len(id_seqs)):
            name_seq2 = id_seqs[j]
            if name_seq[0] in [descendant for id in name_seq2 for descendant in tree.descendants(id)]:
                ancestor[i] = j
                if not j in descendants.keys():
                    descendants[j] = [i]
                else:
                    descendants[j].append(i)

    # compute the set of nodes that have no ancestors
    topmost = [i for i in range(len(id_seqs)) if i not in ancestor.keys()]

    # recursively compute the dependency string
    return argument_dependencies_rec(tree, id_seqs, descendants, topmost)


def argument_dependencies_rec(tree, id_seqs, descendants, arg_indices):
    """
    Recursively compute the string for the argument dependencies.
    :rtype str
    :param tree: GeneralHybridTree
    :param id_seqs: list of list of string (concatenation of top_max and bottom_max)
    :param descendants: map from (indices of id_seqs) to (list of (indices of id_seqs))
    :param arg_indices: list of (indices of id_seqs)
    :return: string
    """

    # skip nodes that are descendants of some other node in arg_indices
    skip = [i for j in arg_indices for i in arg_indices if j in descendants.keys() and i in descendants[j] ]
    arg_indices = [i for i in arg_indices if i not in skip]

    # sort indices according to position in yield
    arg_indices = sorted(arg_indices,
           cmp= lambda i, j: cmp(tree.node_index(id_seqs[i][0]),
                                 tree.node_index(id_seqs[j][0])))
    term = []
    for i in arg_indices:
        t = str(i)
        if i in descendants.keys():
            t += '(' + argument_dependencies_rec(tree, id_seqs, descendants, descendants[i]) + ')'
        term.append(t)

    return '.'.join(term)



##########################    Tests     #######################################################


def test_dependency_induction():
    tree = GeneralHybridTree()
    tree.add_node("v1",'Piet',"NP",True)
    tree.add_node("v21",'Marie',"N",True)
    tree.add_node("v",'helpen',"V",True)
    tree.add_node("v2",'lezen', "V", True)
    tree.add_child("v","v2")
    tree.add_child("v","v1")
    tree.add_child("v2","v21")
    tree.set_root("v")
    tree.set_dep_label('v','ROOT')
    tree.set_dep_label('v1','SBJ')
    tree.set_dep_label('v2','VBI')
    tree.set_dep_label('v21','OBJ')
    tree.reorder()
    # print tree.children("v")
    # print tree
    #
    # for id_set in ['v v1 v2 v21'.split(' '), 'v1 v2'.split(' '),
    #                'v v21'.split(' '), ['v'], ['v1'], ['v2'], ['v21']]:
    #     print id_set, 'top:', top(tree, id_set), 'bottom:', bottom(tree, id_set)
    #     print id_set, 'top_max:', max(tree, top(tree, id_set)), 'bottom_max:', max(tree, bottom(tree, id_set))
    #
    # print "some rule"
    # for mem, arg in [(-1, 0), (0,0), (1,0)]:
    #     print create_DCP_rule(mem, arg, top_max(tree, ['v','v1','v2','v21']), bottom_max(tree, ['v','v1','v2','v21']),
    #                           [(top_max(tree, l), bottom_max(tree, l)) for l in [['v1', 'v2'], ['v', 'v21']]])
    #
    #
    # print "some other rule"
    # for mem, arg in [(-1,1),(1,0)]:
    #     print create_DCP_rule(mem, arg, top_max(tree, ['v1','v2']), bottom_max(tree, ['v1','v2']),
    #                           [(top_max(tree, l), bottom_max(tree, l)) for l in [['v1'], ['v2']]])
    #
    # print 'strict:' , strict_labeling(tree, top_max(tree, ['v','v21']), bottom_max(tree, ['v','v21']))
    # print 'child:' , child_labeling(tree, top_max(tree, ['v','v21']), bottom_max(tree, ['v','v21']))
    # print '---'
    # print 'strict: ', strict_labeling(tree, top_max(tree, ['v1','v21']), bottom_max(tree, ['v1','v21']))
    # print 'child: ', child_labeling(tree, top_max(tree, ['v1','v21']), bottom_max(tree, ['v1','v21']))
    # print '---'
    # print 'strict:' , strict_labeling(tree, top_max(tree, ['v','v1', 'v21']), bottom_max(tree, ['v','v1', 'v21']))
    # print 'child:' , child_labeling(tree, top_max(tree, ['v','v1', 'v21']), bottom_max(tree, ['v','v1', 'v21']))


    tree2 = GeneralHybridTree()
    tree2.add_node("v1",'Piet',"NP",True)
    tree2.add_node("v211", 'Marie', 'N', True)
    tree2.add_node("v",'helpen',"V",True)
    tree2.add_node("v2",'leren', "V", True)
    tree2.add_node("v21",'lezen',"V",True)
    tree2.add_child("v","v2")
    tree2.add_child("v","v1")
    tree2.add_child("v2","v21")
    tree2.add_child("v21","v211")
    tree2.set_root("v")
    tree2.set_dep_label('v','ROOT')
    tree2.set_dep_label('v1','SBJ')
    tree2.set_dep_label('v2','VBI')
    tree2.set_dep_label('v21','VFIN')
    tree2.set_dep_label('v211', 'OBJ')
    tree2.reorder()

    # print tree2.children("v")
    # print tree2
    #
    # print 'siblings v211', tree2.siblings('v211')
    # print top(tree2, ['v','v1', 'v211'])
    # print top_max(tree2, ['v','v1', 'v211'])
    #
    # print '---'
    # print 'strict:' , strict_labeling(tree2, top_max(tree2, ['v','v1', 'v211']), bottom_max(tree2, ['v','v11', 'v211']))
    # print 'child:' , child_labeling(tree2, top_max(tree2, ['v','v1', 'v211']), bottom_max(tree2, ['v','v11', 'v211']))

    # rec_par = ('v v1 v2 v21'.split(' '),
    #            [('v1 v2'.split(' '), [(['v1'],[]), (['v2'],[])])
    #                ,('v v21'.split(' '), [(['v'],[]), (['v21'],[])])
    #            ])
    #
    # grammar = LCFRS(nonterminal_str(tree, top_max(tree, rec_par[0]), bottom_max(tree, rec_par[0]), 'strict'))
    #
    # add_rules_to_grammar_rec(tree, rec_par, grammar, 'child')
    #
    # grammar.make_proper()
    # print grammar

    print tree.recursive_partitioning()

    (_, grammar) = induce_grammar([tree, tree2], strict_pos_dep, term_pos, direct_extraction, 'START')
    print max([grammar.fanout(nont) for nont in grammar.nonts()])
    print grammar

    parser = LCFRS_parser(grammar, 'NP N V V'.split(' '))
    parser.print_parse()


    hybrid_tree = GeneralHybridTree()
    hybrid_tree = parser.new_DCP_Hybrid_Tree(hybrid_tree, 'P M h l'.split(' '), 'Piet Marie helpen lezen'.split(' '), True)
    print hybrid_tree.full_labelled_yield()
    print hybrid_tree

    string = "hallo"
    dcp_string = DCP_string(string)
    dcp_string.set_dep_label("dep")
    print dcp_string, dcp_string.dep_label()

# test_dependency_induction()