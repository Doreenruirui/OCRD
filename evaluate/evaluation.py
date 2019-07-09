from __future__ import print_function

import warnings
import argparse
import sys
import os.path
from collections import Counter
import numpy as np

BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

from evaluate import edist
from evaluate.prcoess_text import *
import multiprocessing

# disable rank warnings from polyfit
warnings.simplefilter('ignore', np.RankWarning)

class Args:
    def __init__(self):
        self.kind = 'exact'
        self.extension = '.txt'
        self.files = []
        self.confusion = 10
        self.allconf = None
        self.perfile = None
        self.context = 0
        self.parallel = multiprocessing.cpu_count()


def initializer(args):
    global kind, extension, context, confusion, allconf
    kind = args.kind
    extension = args.extension
    context = args.context
    confusion = args.confusion
    allconf = args.allconf


def process1(fname):
    global kind, extension, context, confusion, allconf
    counts = Counter()
    gt = project_text(read_text(fname), kind=kind)
    ftxt = allsplitext(fname)[0] + extension
    missing = 0
    if os.path.exists(ftxt):
        txt = project_text(read_text(ftxt), kind=kind)
    else:
        missing = len(gt)
        txt = ""
    # Also the ground truth cannot be empty, it is possible that
    # after filtering (args.kind) the gt string is empty.
    if len(gt) == 0:
        err = len(txt)
        if len(txt) > 0:
            cs = [(txt, '_' * len(txt))]
        else:
            cs = []
    else:
        err, cs = edist.xlevenshtein(txt, gt, context=context)
    if confusion > 0 or allconf is not None:
        for u, v in cs:
            counts[(u, v)] += 1
    return fname, err, len(gt), missing, counts


def evaluate(files):
    args = Args()
    args.files = files
    outputs = []
    if args.parallel < 2:
        for e in args.files:
            result = process1(e)
            outputs.append(result)
    else:
        try:
            pool = multiprocessing.Pool(args.parallel, initializer=initializer(args))
            for e in pool.imap_unordered(process1, args.files, 10):
                outputs.append(e)
        finally:
            pool.close()
            pool.join()
            del pool
    outputs = sorted(list(outputs))
    perfile = None
    if args.perfile is not None:
        perfile = codecs.open(args.perfile, "w", "utf-8")
    allconf = None
    if args.allconf is not None:
        allconf = codecs.open(args.allconf, "w", "utf-8")
    errs = 0
    total = 0
    missing = 0
    counts = Counter()
    for fname, e, t, m, c in outputs:
        errs += e
        total += t
        missing += m
        counts += c
        if perfile is not None:
            perfile.write("%6d\t%6d\t%s\n" % (e, t, fname))
        if allconf is not None:
            for (a, b), v in c.most_common(1000):
                allconf.write("%s\t%s\t%s\n" % (a, b, fname))

    if perfile is not None:
        perfile.close()
    if allconf is not None:
        allconf.close()

    res = {}
    res['errors'] = errs
    res['missing'] = missing
    res['total'] = total
    # print("errors    %8d" % errs)
    # print("missing   %8d" % missing)
    # print("total     %8d" % total)

    if total > 0:
        res['char_error_rate'] = "%.6f %%" % (errs * 1.0 / total)
        res['errnomiss'] = "%8.3f %%" % ((errs-missing) * 100.0 / total)
        # print("err       %8.3f %%" % (errs * 100.0 / total))
        # print("errnomiss %8.3f %%" % ((errs-missing) * 100.0 / total))

    if args.confusion > 0:
        res['confusion'] = []
        for (a, b), v in counts.most_common(args.confusion):
            print("%d\t%s\t%s" % (v, a, b))
            res['confusion'].append((v, a, b))
    print(res)
    return res
    # if total > 0:
    #     print(errs * 1.0 / total)
    # else:
    #     print("Nothing to compare")


# evaluate()