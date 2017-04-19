from corpora.conll_parse import parse_conll_corpus, tree_to_conll_str
from hybridtree.dependency_tree import disconnect_punctuation
from hybridtree.general_hybrid_tree import HybridTree
from hybridtree.monadic_tokens import construct_conll_token
import dependency.induction as d_i
import dependency.labeling as d_l
import time
import parser.parser_factory
import copy
from parser.sDCP_parser.sdcp_parser_wrapper import print_grammar, PysDCPParser, LCFRS_sDCP_Parser, SDCPDerivation
from playground_rparse.process_rparse_grammar import fall_back_left_branching_token
import subprocess
import grammar.linearization as g_l
import decomposition as dec
import re
import argparse


result = 'recursive-partitoning-results.conll'
start = 'START'
term_labelling = d_i.the_terminal_labeling_factory().get_strategy('pos')

tree_parser = LCFRS_sDCP_Parser  # tree parser to count derivations per hybrid tree


tree_yield = term_labelling.prepare_parser_input

train_limit = 2000
test_limit = 5100


#add command line arguments
argParser = argparse.ArgumentParser(description='Train a hybrid grammar using different strategies for recursive partitioning transformation.')
argParser.add_argument('-s', nargs='*', choices=['rtl', 'ltr', 'nnont', 'random', 'argmax']) #choose strategies
argParser.add_argument('-l', nargs='*', choices=['strict', 'child']) #choose strict and/or child labelling
argParser.add_argument('-t', nargs='*', choices=['pos', 'deprel', 'pos+deprel']) #choose pos, deprel, pos+deprel labelling
argParser.add_argument('-f', nargs='*') #choose maximal fanout(s)
argParser.add_argument('-n', nargs='*', choices=['rtl', 'ltr', 'random', 'argmax']) #choose fallback strategy if no-new-nont is used
argParser.add_argument('-r', nargs='*') #set random seed(s) for random strategy
argParser.add_argument('-c', choices=['hungarian','polish']) #choose corpus



def main(ignore_punctuation=False):

    file = open('results.txt', 'w')
    file.close()
    

    parser1 = parser.parser_factory.CFGParser
    parser23 = parser.parser_factory.GFParser


    args = vars(argParser.parse_args())

    #parse command line arguments for transformation strategies,
    #random seed, fallback strategy for no-new-nont and corpora
    if args['c'] is None or args['c'] == 'hungarian':
        test = '../res/SPMRL_SHARED_2014_NO_ARABIC/HUNGARIAN_SPMRL/pred/conll/test/test.Hungarian.pred.conll'
        train ='../res/SPMRL_SHARED_2014_NO_ARABIC/HUNGARIAN_SPMRL/pred/conll/train/train.Hungarian.pred.conll'
    else:
        test = '../res/SPMRL_SHARED_2014_NO_ARABIC/POLISH_SPMRL/pred/conll/test/test.Polish.pred.conll'
        train ='../res/SPMRL_SHARED_2014_NO_ARABIC/POLISH_SPMRL/pred/conll/train/train.Polish.pred.conll'


    strategies = []
    if args['s'] is None:
        strategies = ['']
    else:
        for strategy in args['s']:
            if strategy == 'rtl':
                strategies += ['']
            elif strategy == 'ltr':
                strategies += ['-left-to-right']
            elif strategy == 'nnont':
                if args['n'] is None:
                    strategies += ['-no-new-nont-rtl']
                else:
                    for fallback in args['n']:
                        if fallback == 'random':
                            if args['r'] is None:
                                strategies += ['-no-new-nont-random-1']
                            else:
                                for seed in args['r']:
                                    strategies += ['-no-new-nont-random-' + seed]
                        else:
                            strategies += ['-no-new-nont-' + fallback]
            elif strategy == 'random':
                if args['r'] is None:
                    strategies += ['-random-1']
                else:
                    for seed in args['r']:
                        strategies += ['-random-' + seed]
            else: #argmax strategy
                strategies += ['-' + strategy]
    
    #parse command line argument for child vs. strict labelling
    labellings1 = []
    if args['l'] is None:
        labellings1 = ['strict']
    else:
        labellings1 = args['l']

    #for pos vs. deprel
    labellings2 = []
    if args['t'] is None:
        labellings2 = ['pos']
    else:
        labellings2 = args['t']

    
    #parse command line argument for fanout
    fanouts = []
    if args['f'] is None:
        fanouts = ['1']
    else:
        fanouts = args['f']


    for strategy in  strategies:
        for labelling1 in labellings1:
            for labelling2 in labellings2:
                for fanout in fanouts:
                    if fanout == '1':
                        trainAndEval(strategy, labelling1, labelling2, fanout, parser1, train, test, ignore_punctuation)
                    else:
                        trainAndEval(strategy, labelling1, labelling2, fanout, parser23, train, test, ignore_punctuation)




def trainAndEval(strategy, labelling1, labelling2, fanout, parser_type, train, test, ignore_punctuation=False):
    file = open('results.txt', 'a')
    term_labelling = d_i.the_terminal_labeling_factory().get_strategy('pos')
    recursive_partitioning = d_i.the_recursive_partitioning_factory().getPartitioning('fanout-' + str(fanout) + strategy)
    primary_labelling = d_l.the_labeling_factory().create_simple_labeling_strategy(labelling1, labelling2)
    

    trees = parse_conll_corpus(train, False, train_limit)
    if ignore_punctuation:
        trees = disconnect_punctuation(trees)
    (n_trees, grammar) = d_i.induce_grammar(trees, primary_labelling, term_labelling.token_label, recursive_partitioning, start)
    
    
    file.write('\n\n\n')
    if strategy == '':
        file.write('-right-to-left' + ' ' + labelling1 + ' ' + labelling2 + ' ' + fanout)
    else:
        file.write(strategy + ' ' + labelling1 + ' ' + labelling2 + ' ' + fanout)
    file.write('\n')
    
    
    res = ''

    res += '#nonts:' + str(len(grammar.nonts()))
    res += ' #rules:' + str(len(grammar.rules()))
    
    # The following code is to count the number of derivations for a hypergraph (tree parser required)
    tree_parser.preprocess_grammar(grammar)

    trees = parse_conll_corpus(train , False, train_limit)
    if ignore_punctuation:
        trees = disconnect_punctuation(trees)
    

    derCount = 0
    derMax = 0
    i = 0
    for tree in trees:
        parser = tree_parser(grammar, tree)  # if tree parser is used
        der = parser.count_derivation_trees()
        if der > derMax:
            derMax = der
        derCount += der
        i += 1
        print i

    res += "  average: " + str(1.0*derCount/train_limit)
    res += " maximal: " + str(derMax)
    
    
    total_time = 0.0

    # The following code works for string parsers for evaluating
    
    parser_type.preprocess_grammar(grammar)
    
    trees = parse_conll_corpus(test, False, test_limit)
    if ignore_punctuation:
        trees = disconnect_punctuation(trees)
    
    with open(result, 'w') as result_file:
        failures = 0
        for tree in trees:
            time_stamp = time.clock()
    
            parser = parser_type(grammar, tree_yield(tree.token_yield()))
    
            time_stamp = time.clock() - time_stamp
            total_time += time_stamp
    
    
            cleaned_tokens = copy.deepcopy(tree.full_token_yield())
            for token in cleaned_tokens:
                token.set_deprel('_')
            h_tree = HybridTree(tree.sent_label())
            h_tree = parser.dcp_hybrid_tree_best_derivation(h_tree, cleaned_tokens, ignore_punctuation,
                                                            construct_conll_token)
   
            if h_tree:
                result_file.write(tree_to_conll_str(h_tree))
                result_file.write('\n\n')
            else:
                failures += 1
                forms = [token.form() for token in tree.full_token_yield()]
                poss = [token.pos() for token in tree.full_token_yield()]
                result_file.write(tree_to_conll_str(fall_back_left_branching_token(cleaned_tokens)))
                result_file.write('\n\n')

    
    
    res += "  no punctuation: "
    out = subprocess.check_output(["perl", "../util/eval.pl", "-g", test, "-s", result, "-q"])
    match = re.search(r'[^=]*= (\d+\.\d+)[^=]*= (\d+.\d+).*', out)
    res += ' l:' + match.group(1) #labeled attachment score
    res += ' u:' + match.group(2) #unlabeled attachment score
    res += "  punctation: "
    out = subprocess.check_output(["perl", "../util/eval.pl", "-g", test, "-s", result, "-q", "-p"])
    match = re.search(r'[^=]*= (\d+\.\d+)[^=]*= (\d+.\d+).*', out)
    res += ' l:' + match.group(1)
    res += ' u:' + match.group(2)
    

    
    res += " time: " + str(total_time)
    


    file.write(res)
    file.close()





if __name__ == '__main__':
    main()



