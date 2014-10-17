# Hybrid Tree
# A directed acyclic graph, where a (not necessarily strict) subset of the nodes is linearly ordered.

from collections import defaultdict
from decomposition import *


class GeneralHybridTree:
    def __init__(self, sent_label=None):
        """
        :param sent_label: name of the sentence
        :type: str
        """
        # label of sentence (identifier in corpus)
        self.__sent_label = sent_label
        # id of root node
        self.__root = None
        # list of node ids
        self.__nodes = []
        # maps node id to list of ids of children
        self.__id_to_child_ids = {}
        # maps node id to node label
        self.__id_to_label = {}
        # maps node id to part-of-speech tag
        self.__id_to_pos = {}
        # list of node ids in ascending order
        self.__ordered_ids = []
        # list of node ids in ascending order, including disconnected nodes
        self.__full_yield = []
        # maps node id to position in the ordering
        self.__id_to_node_index = {}
        # maps node_index (position in ordering) to node id
        self.__node_index_to_id = {}
        # number of nodes in ordering
        self.__n_ordered_nodes = 0
        # store dependency labels (DEPREL in ConLL)
        self.__id_to_dep_label = {}

        # Get label of sentence.

    def sent_label(self):
        """
        :rtype: str
        :return: name of the sentence
        """
        return self.__sent_label

    def set_root(self, id):
        """
        Set root to node given by id.
        :param id: node id
        :type id: str
        """
        self.__root = id

    # @property
    def rooted(self):
        """
        :rtype: bool
        :return: Has root been determined?
        """
        return self.__root is not None

    # @property
    def root(self):
        """
        :rtype: str
        :return: Id of root.
        """
        return self.__root

    def add_node(self, id, label, pos=None, order=False, connected=True):
        """
        Add next node. Order of adding nodes is significant for ordering.
        Set order = True and connected = False to include some token (e.g. punctuation)
        that appears in the yield but shall be ignored during tree operations.
        :param id: node id
        :type id: str
        :param label: word, syntactic category
        :type label: str
        :param pos: part of speech
        :type pos: str
        :param order: include node in linear ordering
        :type order: bool
        :param connected: should the node be connected to other nodes
        :type connected: bool
        """
        self.__nodes += [id]
        self.__id_to_label[id] = label
        if (pos is not None):
            self.__id_to_pos[id] = pos
        if (order is True):
            if (connected is True):
                self.__ordered_ids += [id]
                self.__id_to_node_index[id] = self.__n_ordered_nodes
                self.__n_ordered_nodes += 1
                self.__node_index_to_id[self.__n_ordered_nodes] = id
            self.__full_yield += [id]

    def add_child(self, parent, child):
        """
        Add a pair of node ids in the tree's parent-child relation.
        :param parent: id of parent node
        :type parent: str
        :param child: id of child node
        :type child: str
        """
        if not parent in self.__id_to_child_ids:
            self.__id_to_child_ids[parent] = []
        self.__id_to_child_ids[parent] += [child]

    def parent(self, id):
        """
        :rtype: str
        :param id: node id
        :type id: str
        :return: id of parent node, or None.
        """
        return self.__parent_recur(id, self.root())

    def __parent_recur(self, child, id):
        """
        :rtype: str
        :param child: str (the node, whose parent is searched)
        :param id: (potential parent)
        :return:  id of parent node, or None.
        """
        if child in self.children(id):
            return id
        else:
            for next_id in self.children(id):
                parent = self.__parent_recur(child, next_id)
                if parent is not None:
                    return parent
        return None

    # @property
    def reentrant(self):
        """
        :rtype: bool
        :return: Is there node that is child of two nodes?
        """
        parent = defaultdict(list)
        for id in self.__id_to_child_ids:
            for child in self.children(id):
                parent[child] += [id]
        for id in parent:
            if len(parent[id]) > 1:
                return True
        return False

    def children(self, id):
        """
        :rtype: list[str]
        :param id: str
        :return: Get the list of node ids of child nodes, or the empty list.
        """
        if id in self.__id_to_child_ids:
            return self.__id_to_child_ids[id]
        else:
            return []

    def descendants(self, id):
        """
        :param id: node id
        :type id: str
        :return: the list of node ids of all "transitive" children
        :rtype: list[str]
        """
        des = []
        if id in self.__id_to_child_ids:
            for id2 in self.__id_to_child_ids[id]:
                des.append(id2)
                des += self.descendants(id2)
        return des

    def in_ordering(self, id):
        """
        :param id: node id
        :type id: str
        :return: Is the node in the ordering?
        :rtype: bool
        """
        return id in self.__ordered_ids

    def index_node(self, index):
        """
        :param index: index in ordering
        :type index: int
        :return: node id at index in ordering
        :rtype: str
        """
        return self.__node_index_to_id[index]

    def node_index(self, id):
        """
        :param id: node id
        :type id: str
        :return: index of node in ordering
        :rtype: int
        """
        return self.__id_to_node_index[id]

    def reorder(self):
        """
        Reorder children according to smallest node (w.r.t. ordering) in subtree.
        """
        self.__reorder(self.root())

    def __reorder(self, id):
        """
        :param id: node id
        :type id: str
        :return: index of smallest node in sub tree (or -1 if none exists)
        :rtype: int
        """
        min_indices = {}
        if self.children(id).__len__() > 0:
            for child in self.children(id):
                min_indices[child] = self.__reorder(child)
            self.__id_to_child_ids[id] = sorted(self.children(id), key=lambda i: min_indices[i])
        if self.in_ordering(id):
            min_indices[id] = self.__id_to_node_index[id]
        min_index = -1
        for index in min_indices.values():
            if min_index < 0 or index < min_index:
                min_index = index
        return min_index

    def fringe(self, id):
        """
        :param id: node id
        :type id: str
        :return: indices (w.r.t. ordering) of all nodes under some node, cf. \Pi^{-1} in paper
        :rtype: list[int]
        """
        y = []
        if self.in_ordering(id):
            y = [self.__id_to_node_index[id]]
        for child in self.children(id):
            y += self.fringe(child)
        return y

    # Number of contiguous spans of node.
    # id: string
    # return: int
    def n_spans(self, id):
        return len(join_spans(self.fringe(id)))

    # Maximum number of spans of any node.
    # return: int
    def max_n_spans(self):
        nums = [self.n_spans(id) for id in self.nodes()]
        if len(nums) > 0:
            return max(nums)
        else:
            return 1

    # Total number of gaps in any node.
    # return: int
    def n_gaps(self):
        return self.__n_gaps_below(self.root())

    # id: string
    # return: int
    def __n_gaps_below(self, id):
        n_gaps = self.n_spans(id) - 1
        for child in self.children(id):
            n_gaps += self.__n_gaps_below(child)
        return n_gaps

    # Create unlabelled structure, only in terms of breakup of yield
    # return: pair consisting of (root and list of child nodes)
    def unlabelled_structure(self):
        return self.unlabelled_structure_recur(self.root())

    def unlabelled_structure_recur(self, id):
        head = set(self.fringe(id))
        tail = [self.unlabelled_structure_recur(child) for \
                child in self.children(id)]
        # remove useless step
        if len(tail) == 1 and head == tail[0][0]:
            return tail[0]
        else:
            return (head, tail)

    def recursive_partitioning(self):
        return self.recursive_partitioning_rec(self.root())

    def recursive_partitioning_rec(self, id):
        head = set(self.fringe(id))
        tail = [(set([self.node_index(id)]), [])]
        # descendants = self.descendants(id)
        # descendants.append(id)
        # head = filter(self.in_ordering, descendants)
        # tail = [([id], [])]
        tail += map(self.recursive_partitioning_rec, self.children(id))
        if len(tail) == 1 and head == tail[0][0]:
            return tail[0]
        else:
            return (head, tail)

    def node_id_rec_par(self, rec_par):
        (head, tail) = rec_par
        head = map(lambda x: self.index_node(x + 1), head)
        tail = map(self.node_id_rec_par, tail)
        return (head, tail)

    # Labelled spans.
    # return: list of spans (each of which is string plus an even
    # number of (integer) positions)
    def labelled_spans(self):
        spans = []
        for id in [n for n in self.nodes() if not n in self.full_yield()]:
            span = [self.node_label(id)]
            for (low, high) in join_spans(self.fringe(id)):
                span += [low, high]
            # TODO: this if-clause allows to handle trees, that have nodes with empty fringe
            if len(span) >= 3:
                spans += [span]
        return sorted(spans, \
                      cmp=lambda x, y: cmp([x[1]] + [-x[2]] + x[3:] + [x[0]], \
                                           [y[1]] + [-y[2]] + y[3:] + [y[0]]))

    #
    def id_yield(self):
        return self.__ordered_ids

    # Get yield as list of all labels of nodes, that are in the ordering
    # return: list of string
    def labelled_yield(self):
        return [self.node_label(id) for id in self.__ordered_ids]

    # Get full yield (including disconnected nodes) as list of labels
    def full_labelled_yield(self):
        return [self.node_label(id) for id in self.__full_yield]

    # Get full yield (including disconnected nodes) as list of ids
    def full_yield(self):
        return self.__full_yield

    # Get ids of all nodes.
    # return: list of string
    def nodes(self):
        return self.__nodes

    # Get the label of some node.
    # id: string
    # return: string
    def node_label(self, id):
        return self.__id_to_label[id]

    # Does yield cover whole string?
    # return: bool
    def complete(self):
        return self.rooted() and \
               len(self.fringe(self.root())) == self.__n_ordered_nodes

    # Get POS of node
    # id: string
    def node_pos(self, id):
        return self.__id_to_pos[id]

    # Get dependency label (DEPREL) of node
    # id: string
    def node_dep_label(self, id):
        if id in self.__id_to_dep_label.keys():
            return self.__id_to_dep_label[id]
        else:
            return None

    # Set dependency label (DEPREL) of node
    # id: string
    # dep_label: string
    def set_dep_label(self, id, dep_label):
        self.__id_to_dep_label[id] = dep_label

    # Get POS-yield (omitting disconnected nodes)
    def pos_yield(self):
        return [self.node_pos(id) for id in self.__ordered_ids]

    # Number of nodes in total tree (omitting disconnected nodes)
    def n_nodes(self):
        return self.__n_nodes_below(self.root()) + 1

    # Number of nodes below node
    # id: string
    # return: int
    def __n_nodes_below(self, id):
        n = len(self.children(id))
        for child in self.children(id):
            n += self.__n_nodes_below(child)
        return n

    # Is there any non-ordered node without children?
    # Includes the case the root has no children.
    # return: bool
    def empty_fringe(self):
        for id in self.nodes():
            if len(self.children(id)) == 0 and not id in self.full_yield():
                return True
        return self.rooted() and len(self.fringe(self.root())) == 0

    # The siblings of id, i.e. the children of id's parent (including id),
    # ordered from left to right.
    # If id is the root, [root] is returned
    # id: string
    # return: list of string (node ids)
    def siblings(self, id):
        if self.root() == id:
            return [id]
        else:
            parent = self.parent(id)
            if not parent:
                raise Exception('non-root node has no parent!')
            return self.children(parent)

    def __hybrid_tree_str(self, root, level):
        dep = self.node_dep_label(root)
        if dep:
            dep = '\t(' + dep + ')\t'
        else:
            dep = ''
        s = level * ' ' + self.node_label(root) + dep + '\n'
        for child in self.children(root):
            s += self.__hybrid_tree_str(child, level + 1)
        return s

    def __str__(self):
        return self.__hybrid_tree_str(self.root(), 0)


def test():
    print "Start"
    tree = GeneralHybridTree()
    tree.add_node("v1", "Piet", "NP", True)
    tree.add_node("v21", "Marie", "N", True)
    tree.add_node("v", "helpen", "V", True)
    tree.add_node("v2", "lezen", "V", True)
    tree.add_child("v", "v2")
    tree.add_child("v", "v1")
    tree.add_child("v2", "v21")
    tree.add_node("v3", ".", "Punc", True, False)
    tree.set_root("v")
    print tree.children("v")
    tree.reorder()
    print tree.children("v")

    print "fringe v", tree.fringe("v")
    print "fringe v2", tree.fringe("v2")

    print "n spans v", tree.n_spans("v")
    print "n spans v2", tree.n_spans("v2")

    print "n_gaps", tree.n_gaps()
    print "ids:", tree.nodes()
    print "complete", tree.complete()
    print "unlabeled structure", tree.unlabelled_structure()

    print "max n spans", tree.max_n_spans()

    print "labelled yield", tree.labelled_yield()
    print "full labelled yield", tree.full_labelled_yield()

    print "full yield", tree.full_yield()

    print "labelled spans", tree.labelled_spans()
    print "POS yield", tree.pos_yield()
    # test()