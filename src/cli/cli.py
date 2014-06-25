"""
Usage: cli -h | --help
       cli mood benchmark <labeled_tweets> [-umpt] [-s SW] [-e E] [-b] [--no-AH --no-DD --no-TA]
                          [--min-df=M] [--n-folds=K] [--n-examples=N] [--clf=C [--clf-options=O]]
       cli mood label <input_tweets> <labeled_tweets> [-l L] [--no-AH --no-DD --no-TA]
       cli tweets collect <settings_file> <output_tweets> <track_file> [<track_file>...] [-c C]
       cli tweets filter <input_tweets> <output_tweets> <track_file> [<track_file>...] [-c C]
                         [--each] [--no-rt]
       cli users collect_tweets <settings_file> <user_ids_file> <output_dir> [-c C]
       cli users list_friends <settings_file> <user_ids_file> <output_dir>

Options:
    -h, --help              Show this screen.
    --clf=C                 Classifier type to use for the task: can be 'logistic-reg', 'svm',
                            'decision-tree', 'naive-bayes', 'kneighbors'
    --clf-options=O         Options for the classifier in JSON
    --each                  Filter C tweets for each of the tracked words
    --min-df=M              See min_df from sklearn vectorizers [default: 1]
    --n-examples=N          Number of wrong classified examples to display [default: 0]
    --n-folds=K             Number of folds [default: 3]
    --no-AH                 Do not label tweets on Anger/Hostility dimension
    --no-DD                 Do not label tweets on Depression/Dejection dimension
    --no-TA                 Do not label tweets on Tension/Anxiety dimension
    --no-rt                 Remove retweets when filtering
    -b, --binary            No count of features, only using binary features.
    -c C, --count=C         Number of tweets to collect/filter [default: 3200]
    -e E, --emoticons=E     Path to file containing the list of emoticons to keep
    -l, --begin-line=L      Line to start labeling the tweets [default: 0]
    -m                      Keep mentions when cleaning corpus
    -p                      Keep punctuation when cleaning corpus
    -s SW, --stopwords=SW   Path to file containing the stopwords to remove from the corpus
    -t, --top-features      Display the top features during the benchmark
    -u                      Keep URLs when cleaning corpus
"""
import sporty.sporty as sporty
from sporty.datastructures import *
from sporty.tweets import Tweets
from docopt import docopt
import sys
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.multiclass import OneVsRestClassifier
import os.path


def main():
    args = docopt(__doc__)
    api = sporty.api()
    if args['tweets']:
        # Concatenate the words to track
        totrack = set()
        for i in args['<track_file>']:
            totrack = totrack.union(set(LSF(i).tolist()))

        if args['collect']:
            # Authenticate to the Twitter API
            api.tweets = sporty.tweets.api(settings_file=args['<settings_file>'])
            api.collect(totrack, args['<output_tweets>'], count=int(args['--count']))

        if args['filter']:
            api.load(args['<input_tweets>'])
            api.filter(int(args['--count']), totrack, each_word=args['--each'],
                       output_file=args['<output_tweets>'], rt=not args['--no-rt'])

    elif args['users']:
        # Authenticate to the Twitter API
        api.users = sporty.users.api(args['<user_ids_file>'],
                                     args['<settings_file>'])
        if args['collect_tweets']:
            api.collectTweets(args['<output_dir>'], int(args['--count']))

        if args['list_friends']:
            api.getFriends(args['<output_dir>'])

    elif args['mood']:
        keys = ['AH', 'DD', 'TA']
        if args['--no-AH']:
            keys.remove('AH')
        if args['--no-DD']:
            keys.remove('DD')
        if args['--no-TA']:
            keys.remove('TA')

        labels = {x: [0, 1] for x in keys}

        if args['label']:
            api.load(args['<input_tweets>'])
            api.label(labels, args['<labeled_tweets>'], int(args['--begin-line']))

        elif args['benchmark']:
            # Build the right classifier given the CLI options
            classifier_choices = {'logistic-reg': LogisticRegression,
                                  'svm': SVC,
                                  'decision-tree': DecisionTreeClassifier,
                                  'naive-bayes': GaussianNB,
                                  'kneighbors': KNeighborsClassifier}

            clf = SVC(kernel='linear', C=1, class_weight='auto')  # default classifier
            if args['--clf'] in classifier_choices.keys():
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

            # Build the cleaner options and the TF-IDF vectorizer options
            cleaner_options = {'stopwords': args['--stopwords'],
                               'emoticons': args['--emoticons'],
                               'rm_mentions': not args['-m'],
                               'rm_punctuation': not args['-p'],
                               'rm_unicode': not args['-u']}
            tfidf_options = {'min_df': int(args['--min-df']),
                             'binary': args['--binary'],
                             'ngram_range': (1, 1)}

            # Load the tweets
            tweets = Tweets(args['<labeled_tweets>'])

            # Build features and the vectorizer
            api.buildFeatures(tweets, cleaner_options=cleaner_options, labels=keys)
            api.buildVectorizer(options=tfidf_options)

            # Run the benchmark
            api.benchmark(int(args['--n-folds']),
                          int(args['--n-examples']),
                          args['--top-features'])

if __name__ == "__main__":
    main()
