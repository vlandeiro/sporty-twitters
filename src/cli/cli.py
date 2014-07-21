"""
Usage: cli -h | --help
       cli mood benchmark <labeled_tweets> [-bmptu] [-s SW] [-e E] [--min-df=M] [--n-folds=K]
                          [--n-examples=N] [--clf=C [--clf-options=O]] [--proba=P] [--roc=R]
                          [--reduce-func=R] [--features-func=F] [--liwc=L] [-k K]
       cli mood label <input_tweets> <labeled_tweets> [-l L] [--no-AH --no-DD --no-TA]
       cli tweets collect <settings_file> <output_tweets> <track_file> [<track_file>...] [-c C]
       cli tweets filter <input_tweets> <output_tweets> <track_file> [<track_file>...] [-c C]
                         [--each] [--no-rt]
       cli users collect_tweets <settings_file> <user_ids_file> <output_dir> [-c C]
       cli users list_friends <settings_file> <user_ids_file> <output_dir>
       cli users most_similar <user_ids_file> <users_dir> <friends_dir>
       cli users show <settings_file> <input_dir>

Options:
    -h, --help              Show this screen.
    --clf=C                 Classifier type to use for the task: can be 'logistic-reg', 'svm',
                            'decision-tree', 'naive-bayes', 'kneighbors'
    --clf-options=O         Options for the classifier in JSON
    --each                  Filter C tweets for each of the tracked words
    --liwc=L                Path to the LIWC dictionary
    --min-df=M              See min_df from sklearn vectorizers [default: 1]
    --n-examples=N          Number of wrong classified examples to display [default: 0]
    --n-folds=K             Number of folds [default: 3]
    --no-rt                 Remove retweets when filtering
    --proba=P               Classify a tweet as positive only if the probability to be positive
                            is greater than P
    --roc=R                 Plot the ROC curve with R the test set size given as a ratio
                            (e.g. 0.2 for 20 percent of the data) and return. Note: the benchmark
                            is not run.
    -b, --binary            No count of features, only using binary features.
    -c C, --count=C         Number of tweets to collect/filter [default: 3200]
    -e E, --emoticons=E     Path to file containing the list of emoticons to keep
    -f F, --features-func=F List of functions to execute amongst the functions of the
                            FeatureBuilder class. The functions of this list will begin
                            executed in order.
    -k K, --k-features=K    Number of features to keep during the features selection [default: 100]
    -l, --begin-line=L      Line to start labeling the tweets [default: 0]
    -m                      Keep mentions when cleaning corpus
    -p                      Keep punctuation when cleaning corpus
    -r R, --reduce-func=R   Function that will be used to reduced the labels into one general
                            label (e.g. 'lambda x, y: x or y')
    -s SW, --stopwords=SW   Path to file containing the stopwords to remove from the corpus
    -t, --top-features      Display the top features during the benchmark
    -u                      Keep URLs when cleaning corpus
"""
import sporty.sporty as sporty
from sporty.datastructures import *
from sporty.tweets import Tweets
from sporty.utils import FeaturesBuilder
from docopt import docopt
import sys
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.multiclass import OneVsRestClassifier
import os.path
from os import listdir


def main(argv=None):
    args = docopt(__doc__, argv)
    api = sporty.api()
    if args['tweets']:
        # Concatenate the words to track
        totrack = set()
        for i in args['<track_file>']:
            totrack = totrack.union(set(LSF(i).tolist()))

        if args['collect']:
            # Authenticate to the Twitter API
            api.tweets = sporty.tweets.api(settings_file=args['<settings_file>'])
            api.tweets.collect(totrack, args['<output_tweets>'], count=int(args['--count']))

        elif args['filter']:
            api.tweets.load(args['<input_tweets>'])
            api.tweets.filter(int(args['--count']), totrack, each_word=args['--each'],
                              output_file=args['<output_tweets>'], rt=not args['--no-rt'])

    elif args['users']:
        # Authenticate to the Twitter API
        api.users = sporty.users.api(args['<user_ids_file>'],
                                     args['<settings_file>'])
        if args['collect_tweets']:
            api.users.collectTweets(args['<output_dir>'], int(args['--count']))

        elif args['list_friends']:
            api.users.outputFriendsIds(args['<output_dir>'])

        elif args['show']:
            files = [os.path.join(args['<input_dir>'], f) for f in listdir(args['<input_dir>'])
                     if os.path.isfile(os.path.join(args['<input_dir>'], f))
                     and f.find('extended') == -1]
            for f in files:
                if os.path.isfile(f + '.extended'):  # friends list already exists for this user
                    continue
                with open(f + '.extended', 'w') as fout:
                    api.users.loadIds(f)
                    extended = api.users.extendFromIds()
                    for user in extended:
                        fout.write(json.dumps(user) + "\n")

        elif args['most_similar']:
            api.users.loadIds(args['<user_ids_file>'])
            sortedfriends = api.users.buildSimilarityMatrix(args['<users_dir>'], args['<friends_dir>'])
            for u in sortedfriends:
                ufriends = sortedfriends[u]
                if ufriends:
                    print str(u) + ";" + str(ufriends[0]['id'])

    elif args['mood']:
        keys = ['AH', 'DD', 'TA']
        labels = {x: [0, 1] for x in keys}
        if args['label']:
            api.tweets.load(args['<input_tweets>'])
            api.tweets.label(labels, args['<labeled_tweets>'], int(args['--begin-line']))

        elif args['benchmark']:
            # Build the right classifier given the CLI options
            classifier_choices = {'logistic-reg': LogisticRegression,
                                  'svm': SVC,
                                  'decision-tree': DecisionTreeClassifier,
                                  'naive-bayes': GaussianNB,
                                  'kneighbors': KNeighborsClassifier}

            if not args['--clf']:
                clf = SVC(kernel='linear', C=1, class_weight='auto')  # default classifier
            elif args['--clf'] in classifier_choices.keys():
                clfoptions = {}
                if args['--clf-options']:
                    clfoptions = json.loads(args['--clf-options'])
                    # avoid raising exception when setting SVM kernel using CLI
                    if 'kernel' in clfoptions:
                        clfoptions['kernel'] = str(clfoptions['kernel'])
                clf = classifier_choices[args['--clf']](**clfoptions)
            else:
                raise Exception("Wrong value for clf: must be amongst "
                                + str(classifier_choices.keys()))
            api.mood.clf = clf

            # Build the cleaner options, the TF-IDF vectorizer options,
            # and the FeaturesBuilder options.
            cleaner_options = {'stopwords': args['--stopwords'],
                               'emoticons': args['--emoticons'],
                               'rm_mentions': not args['-m'],
                               'rm_punctuation': not args['-p'],
                               'rm_unicode': not args['-u']}
            tfidf_options = {'min_df': int(args['--min-df']),
                             'binary': args['--binary'],
                             'ngram_range': (1, 1),
                             'lowercase': False}
            # get the list of functions to run from the FeaturesBuilder
            if args['--features-func']:
                func_list = eval(args['--features-func'])
                for f in func_list:
                    if f not in dir(FeaturesBuilder):
                        raise Exception(f + " is not a function of FeaturesBuilder.")
            else:
                func_list = None
            # get the reducing function
            if args['--reduce-func']:
                reduce_func = eval(args['--reduce-func'])
            else:
                reduce_func = None
            fb_options = {"labels": keys,
                          "labels_reduce_f": reduce_func,
                          "func_list": func_list,
                          "liwc_path": args['--liwc']}

            # Load the tweets
            tweets = Tweets(args['<labeled_tweets>'])

            # Build features and the vectorizer
            api.mood.buildX(tweets, int(args['--k-features']), cleaner_options, fb_options,
                            tfidf_options)

            # Plot the ROC curve if asked:
            if args['--roc']:
                api.mood.ROC_curve(float(args['--roc']))
                return

            # Run the benchmark
            argproba = False
            if args['--proba']:
                argproba = float(args['--proba'])
            return args, api.mood.benchmark(int(args['--n-folds']),
                                            int(args['--n-examples']),
                                            args['--top-features'],
                                            argproba)

if __name__ == "__main__":
    main()
