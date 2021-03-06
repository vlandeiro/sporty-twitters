import json
import sys
import re
from math import sqrt
from collections import defaultdict
from collections import OrderedDict
from collections import Counter


class ContextSimilar(object):
    """
    Class that allows the user to expand a vocabulary by looking for the words
    in a corpus that have the most similar contexts to the words in the
    vocabulary.
    """

    def __init__(self, vocabulary, corpus, n=100):
        """
        Initializes the ContextSimilar instance by setting the vocabulary and
        the corpus.
        """
        super(ContextSimilar, self).__init__()
        self.vocabulary = vocabulary
        self.corpus = corpus
        self.n = n
        self.contexts = defaultdict(lambda: defaultdict(int))
        self.similarityMatrix = defaultdict(lambda: defaultdict(float))
        self.sortedSimilarWords = OrderedDict()

    def buildContexts(self):
        """
        Builds the similarity contexts by looking at the 3-word neighbourhood
        of every word for every tweet in the corpus.
        """
        for tw in self.corpus:
            # split the tweet in a list of words
            words = re.split("\s+", tw.strip())
            words = [x for x in words if x]  # remove empty words

            # build the context for each word by considering the 3 left
            # neighbours and the 3 right neighbours of the each word.
            target = 0
            for w in words:
                w_dic = self.contexts[w]
                i = 0
                for i in range(max(0, target-3), target):
                    entry = words[i] + "@" + str(i-target)
                    w_dic[entry] += 1
                for i in range(target+1, min(target+3, len(words))):
                    entry = words[i] + "@" + str(i-target)
                    w_dic[entry] += 1
                target += 1
        return self.contexts

    def cosineSimilarity(self, k1, k2):
        """
        Compute the cosine similarity between two words considering their
        neighbourhood.
        """
        A = defaultdict(int, self.contexts[k1])
        B = defaultdict(int, self.contexts[k2])
        if len(A) == 0 or len(B) == 0:
            return 0
        if len(A) < len(B):
            M = A
            N = B
        else:
            M = B
            N = A

        normA = sqrt(sum([x**2 for x in A.values()]))
        normB = sqrt(sum([x**2 for x in B.values()]))

        score = 0.
        score = sum([float(M[k]*N[k]) for k in M.keys()])/float(normA*normB)
        return score

    def buildMostSimilar(self):
        """
        Returns the words that are most similar to all the words in the
        vocabulary.
        """
        total_scores = defaultdict(float)

        # cumulate the similarity scores
        for w in self.vocabulary:
            dict4word = self.similarityMatrix[w]
            for context_w in dict4word:
                total_scores[context_w] += dict4word[context_w]

        # sort the words ordered by cumulated similarity
        sortedSim = sorted(total_scores, key=total_scores.get, reverse=True)
        for w in sortedSim:
            self.sortedSimilarWords[w] = total_scores[w]
            self.sortedSimilarWords[w] /= float(len(self.vocabulary))

        return self.sortedSimilarWords

    def buildSimilarityMatrix(self):
        """
        Builds a similiraty matrix based on the cosine similarity for a given
        list of words. For each of the word U in the list, it computes the
        similarity with every word V in the contexts previously built.
        """
        w = len(self.contexts)
        h = len(self.vocabulary)
        # number of elements in the similarity matrix
        total = h*w

        for k1 in self.vocabulary:
            for k2 in self.contexts.keys():
                self.similarityMatrix[k1][k2] = self.cosineSimilarity(k1, k2)
        return self.similarityMatrix

    def expandVocabulary(self):
        """
        Combines methods of this class to expand the given vocabulary.
        """
        self.buildContexts()
        self.buildSimilarityMatrix()
        self.buildMostSimilar()
        return self.sortedSimilarWords[:self.n]


class Cooccurrences(object):
    """
    Class that allows the user to expand a vocabulary by finding the words
    that are most frequently cooccurrences of the vocabulary words in a given
    corpus.
    """

    def __init__(self, vocabulary, corpus, n=5):
        """
        Initializes the Cooccurrences instance by setting the vocabulary and
        the corpus.
        """
        super(Cooccurrences, self).__init__()
        self.vocabulary = vocabulary
        self.corpus = corpus
        self.n = 5
        self.cooccurrences = {w: Counter() for w in vocabulary}
        self.docFrequency = Counter()
        self.tfidf = {w: defaultdict(float) for w in vocabulary}
        self.sortedTfidf = {}

    def buildCooccurrences(self):
        """
        For each word in the corpus, counts how much time each of the other
        words appear. Returns the dictionary that contains the results of the
        cooccurrences counting.
        """
        for entry in self.corpus:
            # keep only the words that are in the corpus and in the vocabulary
            corpus_w = set(re.split("\s+", entry.strip()))
            common = [w for w in corpus_w if w in self.vocabulary]

            for w in common:
                # copy of the corpus words without the word to analyze
                list_words = filter(lambda x: x != w, corpus_w)
                # update the document frequency count
                self.docFrequency.update(list_words)
                # update the cooccurrences count
                self.cooccurrences[w].update(list_words)

        return self.cooccurrences

    def buildTfidf(self):
        """
        Sort the cooccurrences of each word in the cooccurrences dictionary
        using TF-IDF.
        """
        for v in self.vocabulary:
            for c in self.cooccurrences[v]:
                self.tfidf[v][c] = float(self.cooccurrences[v][c])
                self.tfidf[v][c] /= float(self.docFrequency[c])
            self.sortedTfidf[v] = sorted(self.tfidf[v].keys(),
                                         key=self.tfidf[v].get,
                                         reverse=True)

    def expandVocabulary(self):
        self.buildCooccurrences()
        self.buildTfidf()
        results = []
        for v in self.sortedTfidf.keys():
            results += self.sortedTfidf[v][:self.n]
        return results
