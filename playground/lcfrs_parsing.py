from __future__ import print_function
from playground.experiment_helpers import TRAINING, VALIDATION, TESTING, CorpusFile, RESULT, SplitMergeExperiment
from constituent.induction import direct_extract_lcfrs, BasicNonterminalLabeling, NonterminalsWithFunctions, binarize, \
    LCFRS_rule
from parser.gf_parser.gf_interface import GFParser, GFParser_k_best
from grammar.induction.terminal_labeling import PosTerminals, FeatureTerminals, FrequencyBiasedTerminalLabeling, FormTerminals, StanfordUNKing, CompositionalTerminalLabeling
from playground.constituent_split_merge import ConstituentExperiment, ScoringExperiment, token_to_features, my_feature_filter, ScorerAndWriter
from parser.sDCP_parser.sdcp_trace_manager import compute_reducts, PySDCPTraceManager
from parser.discodop_parser.parser import DiscodopKbestParser
from parser.sDCP_parser.sdcp_parser_wrapper import print_grammar
from constituent.filter import check_single_child_label
import sys
import os
import plac
if sys.version_info < (3,):
    reload(sys)
    sys.setdefaultencoding('utf8')

# select one of the splits from {"SPMRL", "HN08", "WSJ"}
# SPLIT = "SPMRL"
SPLIT = "HN08"
# SPLIT = "WSJ"

DEV_MODE = True  # enable to parse the DEV set instead of the TEST set
QUICK = True  # enable for quick testing during debugging (small train/dev/test sets)

MULTI_OBJECTIVES = True  # runs evaluations with multiple parsing objectives but reuses the charts

if SPLIT == "SPMRL":
    # all files are from SPMRL shared task

    corpus_type = "TIGERXML"
    train_path = '../res/SPMRL_SHARED_2014_NO_ARABIC/GERMAN_SPMRL/gold/xml/train/train.German.gold.xml'
    train_start = 1
    train_filter = None
    train_limit = 40474
    train_exclude = [7561, 17632, 46234, 50224]
    train_corpus = None

    validation_path = '../res/SPMRL_SHARED_2014_NO_ARABIC/GERMAN_SPMRL/gold/xml/dev/dev.German.gold.xml'
    validation_start = 40475
    validation_size = validation_start + 4999
    validation_filter = None

    if DEV_MODE:
        test_start = validation_start
        test_limit = validation_size
        test_exclude = train_exclude
        test_path = '../res/SPMRL_SHARED_2014_NO_ARABIC/GERMAN_SPMRL/gold/xml/dev/dev.German.gold.xml'
    else:
        test_start = 45475
        test_limit = test_start + 4999
        test_exclude = train_exclude
        test_path = '../res/SPMRL_SHARED_2014_NO_ARABIC/GERMAN_SPMRL/gold/xml/test/test.German.gold.xml'
    test_filter = None

    if QUICK:
        train_path = '../res/SPMRL_SHARED_2014_NO_ARABIC/GERMAN_SPMRL/gold/xml/train5k/train5k.German.gold.xml'
        train_limit = train_start + 2000
        validation_size = validation_start + 200
        test_limit = test_start + 200
#
elif SPLIT == "HN08":
    # files are based on the scripts in Coavoux's mind the gap 1.0
    # where we commented out `rm -r tiger21 tiger22 marmot_tags` in generate_tiger_data.sh

    corpus_type = "EXPORT"
    base_path = "../res/TIGER/tiger21"
    train_start = 1
    train_limit = 50474

    train_path = os.path.join(base_path, "tigertraindev_root_attach.export")

    def train_filter(x):
        return x % 10 >= 2

    train_exclude = [7561, 17632, 46234, 50224]
    train_corpus = None

    validation_start = 1
    validation_size = 50471
    validation_path = os.path.join(base_path, "tigerdev_root_attach.export")

    def validation_filter(x):
        return x % 10 == 1

    if not DEV_MODE:
        test_start = 1  # validation_size  # 40475
        test_limit = 50474
        # test_limit = 200 * 5 // 4
        test_exclude = train_exclude
        test_path = os.path.join(base_path, "tigertest_root_attach.export")

        def test_filter(x):
            return x % 10 == 0
    else:
        test_start = 1
        test_limit = 50474
        test_exclude = train_exclude
        test_path = validation_path
        test_filter = validation_filter

    if QUICK:
        train_limit = 5000 * 5 // 4
        validation_size = 200 * 5 // 4
        test_limit = 200 * 5 // 4
#
elif SPLIT == "WSJ":
    # file is from Kilian Evang's dptb.tar.bz2

    corpus_type = "EXPORT"
    corpus_path = "../res/WSJ/ptb-discontinuous/dptb7.export"
    train_path = validation_path = test_path = corpus_path
    train_exclude = validation_exclude = test_exclude = []
    train_filter = validation_filter = test_filter = None

    # sections 2-21
    train_start = 3915
    train_limit = 43746

    # section 24
    validation_start = 47863
    validation_size = 49208

    if not DEV_MODE:
        # section 23
        test_start = 45447
        test_limit = 47862
    else:
        test_start = validation_start
        test_limit = validation_size

    if QUICK:
        train_limit = train_start + 2000
        validation_size = validation_start + 200
        test_limit = test_start + 200


# fine_terminal_labeling = FeatureTerminals(token_to_features, feature_filter=my_feature_filter)
# fine_terminal_labeling = FormTerminals()
fine_terminal_labeling = CompositionalTerminalLabeling(FormTerminals(), PosTerminals())
fallback_terminal_labeling = PosTerminals()

terminal_threshold = 10


def terminal_labeling(corpus, threshold=terminal_threshold):
    return FrequencyBiasedTerminalLabeling(fine_terminal_labeling, fallback_terminal_labeling, corpus, threshold)


class InductionSettings:
    def __init__(self):
        self.normalize = False
        self.disconnect_punctuation = True
        self.terminal_labeling = PosTerminals()
        # self.nont_labeling = NonterminalsWithFunctions()
        self.nont_labeling = BasicNonterminalLabeling()
        self.binarize = True
        self.isolate_pos = True
        self.hmarkov = 0

    def __str__(self):
        s = "Induction Settings {\n"
        for key in self.__dict__:
            if not key.startswith("__") and key not in []:
                s += "\t" + key + ": " + str(self.__dict__[key]) + "\n"
        return s + "}"


class LCFRSExperiment(ConstituentExperiment, SplitMergeExperiment):
    def __init__(self, induction_settings, directory=None, filters=None):
        ConstituentExperiment.__init__(self, induction_settings, directory=directory, filters=filters)
        SplitMergeExperiment.__init__(self)

        self.strip_vroot = False
        self.k_best = 500

    def __valid_tree(self, obj):
        return obj.complete() and not obj.empty_fringe()

    def induce_from(self, obj):
        if not self.__valid_tree(obj):
            print(obj, list(map(str, obj.token_yield())), obj.full_yield())
            return None, None
        grammar = direct_extract_lcfrs(obj, term_labeling=self.terminal_labeling,
                                       nont_labeling=self.induction_settings.nont_labeling,
                                       binarize=self.induction_settings.binarize,
                                       isolate_pos=self.induction_settings.isolate_pos,
                                       hmarkov=self.induction_settings.hmarkov)
        if self.backoff:
            self.terminal_labeling.backoff_mode = True
            grammar2 = direct_extract_lcfrs(obj, term_labeling=self.terminal_labeling,
                                            nont_labeling=self.induction_settings.nont_labeling,
                                            binarize=self.induction_settings.binarize,
                                            isolate_pos=self.induction_settings.isolate_pos,
                                            hmarkov=self.induction_settings.hmarkov)
            self.terminal_labeling.backoff_mode = False
            grammar.add_gram(grammar2)
        # print(grammar)
        # for rule in grammar.rules():
        #     print(rule)
        #     for lhs, rhs, dcp in binarize(rule.lhs(), rule.rhs(), rule.dcp()):
        #         bin_rule = LCFRS_rule(lhs=lhs, dcp=dcp)
        #         for rhs_nont in rhs:
        #             bin_rule.add_rhs_nont(rhs_nont)
        #         print("\t", bin_rule)
        # print()
        return grammar, None

    def initialize_parser(self):
        save_preprocess=(self.directory, "mygrammar")
        k = 1 if not self.organizer.disable_split_merge or self.oracle_parsing else self.k_best
        if "disco-dop" in self.parsing_mode:
            self.parser = DiscodopKbestParser(grammar=self.base_grammar, k=self.k_best,
                                              cfg_ctf=self.disco_dop_params["cfg_ctf"],
                                              pruning_k=self.disco_dop_params["pruning_k"],
                                              beam_beta=self.disco_dop_params["beam_beta"],
                                              beam_delta=self.disco_dop_params["beam_delta"]
                                              )
        else:
            self.parser = GFParser_k_best(self.base_grammar, save_preprocessing=save_preprocess, k=k)

    def compute_reducts(self, resource):

        # print_grammar(self.base_grammar)
        # for rule in self.base_grammar.rules():
        #     print(rule.get_idx(), rule)
        # sys.stdout.flush()

        training_corpus = list(filter(self.__valid_tree, self.read_corpus(resource)))
        parser = self.organizer.training_reducts.get_parser() if self.organizer.training_reducts is not None else None
        nonterminal_map = self.organizer.nonterminal_map
        frequency = self.backoff_factor if self.backoff else 1.0
        trace = compute_reducts(self.base_grammar, training_corpus, self.induction_settings.terminal_labeling,
                                parser=parser, nont_map=nonterminal_map, debug=False, frequency=frequency)
        if self.backoff:
            self.terminal_labeling.backoff_mode = True
            trace.compute_reducts(training_corpus, frequency=1.0)
            self.terminal_labeling.backoff_mode = False
        print("computed trace")
        return trace

    def print_config(self, file=None):
        if file is None:
            file = self.logger
        ConstituentExperiment.print_config(self, file=file)
        SplitMergeExperiment.print_config(self, file=file)

    def read_stage_file(self):
        ScoringExperiment.read_stage_file(self)

        if "training_reducts" in self.stage_dict:
            self.organizer.training_reducts = PySDCPTraceManager(self.base_grammar, self.terminal_labeling)
            self.organizer.training_reducts.load_traces_from_file(
                bytes(self.stage_dict["training_reducts"], encoding="utf-8"))

        if "validation_reducts" in self.stage_dict:
            self.organizer.validation_reducts = PySDCPTraceManager(self.base_grammar, self.terminal_labeling)
            self.organizer.validation_reducts.load_traces_from_file(
                bytes(self.stage_dict["validation_reducts"], encoding="utf-8"))

        SplitMergeExperiment.read_stage_file(self)


@plac.annotations(
    directory=('directory in which experiment is run', 'option', None, str)
    )
def main(directory=None):
    induction_settings = InductionSettings()
    induction_settings.hmarkov = 1
    induction_settings.disconnect_punctuation = False
    induction_settings.normalize = True

    filters = []
    # filters += [check_single_child_label, lambda x: check_single_child_label(x, label="SB")]
    experiment = LCFRSExperiment(induction_settings, directory=directory, filters=filters)
    experiment.resources[TRAINING] = CorpusFile(path=train_path, start=train_start, end=train_limit, exclude=train_exclude,
                                                filter=train_filter, type=corpus_type)
    experiment.resources[VALIDATION] = CorpusFile(path=validation_path, start=validation_start, end=validation_size
                                                  , exclude=train_exclude, filter=validation_filter, type=corpus_type)
    experiment.resources[TESTING] = CorpusFile(path=test_path, start=test_start,
                                               end=test_limit, exclude=train_exclude, filter=test_filter, type=corpus_type)

    backoff_threshold = 8
    induction_settings.terminal_labeling = terminal_labeling(experiment.read_corpus(experiment.resources[TRAINING]),
                                                             backoff_threshold)
    experiment.backoff = True


    experiment.terminal_labeling = induction_settings.terminal_labeling
    experiment.organizer.validator_type = "SIMPLE"
    experiment.organizer.project_weights_before_parsing = True
    experiment.organizer.disable_em = False
    experiment.organizer.disable_split_merge = False
    experiment.organizer.max_sm_cycles = 5
    experiment.organizer.threads = 8
    experiment.oracle_parsing = False
    experiment.k_best = 500
    experiment.disco_dop_params["pruning_k"] = 50000
    experiment.read_stage_file()

    if MULTI_OBJECTIVES:
        experiment.parsing_mode = "discodop-multi-method"
        experiment.resources[RESULT] = ScorerAndWriter(experiment,
                                                       directory=experiment.directory,
                                                       logger=experiment.logger,
                                                       secondary_scores=3)
        experiment.run_experiment()
    else:
        experiment.parsing_mode = "latent-viterbi-disco-dop"
        experiment.run_experiment()

        experiment.parsing_mode = "k-best-rerank-disco-dop"
        experiment.resources[RESULT] = ScorerAndWriter(experiment, directory=experiment.directory, logger=experiment.logger)
        experiment.run_experiment()

        experiment.resources[RESULT] = ScorerAndWriter(experiment, directory=experiment.directory, logger=experiment.logger)
        experiment.parsing_mode = "variational-disco-dop"
        experiment.run_experiment()

        experiment.resources[RESULT] = ScorerAndWriter(experiment, directory=experiment.directory, logger=experiment.logger)
        experiment.parsing_mode = "max-rule-prod-disco-dop"
        experiment.run_experiment()


if __name__ == '__main__':
    plac.call(main)
