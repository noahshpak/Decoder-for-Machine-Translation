#!/usr/bin/env python
import optparse
import sys
import models
import math

optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="input", default="data/input", help="File containing sentences to translate (default=data/input)")
optparser.add_option("-t", "--translation-model", dest="tm", default="data/tm", help="File containing translation model (default=data/tm)")
optparser.add_option("-l", "--language-model", dest="lm", default="data/lm", help="File containing ARPA-format language model (default=data/lm)")
optparser.add_option("-v", "--verbosity", dest="verbosity", default=1, type="int", help="Verbosity level, 0-3 (default=1)")
opts = optparser.parse_args()[0]

#tm = models.TM(opts.tm,sys.maxint)
#lm = models.LM(opts.lm)
#french = [tuple(line.strip().split()) for line in open(opts.input).readlines()]
#english = [tuple(line.strip().split()) for line in sys.stdin]

def maybe_write(s, verbosity):
   if (opts.verbosity > verbosity):
      sys.stdout.write(s)
      sys.stdout.flush()


class Scorer:

   def __init__(self, opts):
      self.opts = opts
      self.tm = models.TM(opts.tm, sys.maxint)
      self.lm = models.LM(opts.lm)
      self.french = [tuple(line.strip().split()) for line in open(opts.input).readlines()]
   # tm should translate unknown words as-is with probability 1
      for word in set(sum(self.french,())):
         if (word,) not in self.tm:
            self.tm[(word,)] = [models.phrase(word, 0.0)]
   
   def grade_score(self, f, e):
      alignments = self.get_alignments(f, e)
      score = self.grade_with_alignments(f, e, alignments)
      return score

   def bitmap(self, sequence):
      """ Generate a coverage bitmap for a sequence of indexes """
      return reduce(lambda x,y: x|y, map(lambda i: long('1'+'0'*i,2), sequence), 0)
   
   def bitmap2str(self, b, n, on='o', off='.'):
      """ Generate a length-n string representation of bitmap b """
      return '' if n==0 else (on if b&1==1 else off) + self.bitmap2str(b>>1, n-1, on, off)
   
   def logadd10(self, x,y):
      """ Addition in logspace (base 10): if x=log(a) and y=log(b), returns log(a+b) """
      return x + math.log10(1 + pow(10,y-x))

  
   def grade_with_alignments(self, f, e, alignments):
     # maybe_write("Aligning...\n",0)
      #maybe_write("NOTE: TM logprobs may be positive since they do not include segmentation\n",0)
      total_logprob = 0.0
      unaligned_sentences = 0
      #maybe_write("===========================================================\n",1)
      #maybe_write("SENTENCE PAIR:\n%s\n%s\n" % (" ".join(f), " ".join(e)),0)    
      #maybe_write("\nLANGUAGE MODEL SCORES:\n",1)
      lm_state = self.lm.begin()
      lm_logprob = 0.0
      for word in e + ("</s>",):
       #  maybe_write("%s: " % " ".join(lm_state + (word,)),1)
         (lm_state, word_logprob) = self.lm.score(lm_state, word)
         lm_logprob += word_logprob
        # maybe_write("%f\n" % (word_logprob,),1)
        # maybe_write("TOTAL LM LOGPROB: %f\n" % lm_logprob,0)
      total_logprob += lm_logprob
        # maybe_write("\nALL POSSIBLE PHRASE-TO-PHRASE ALIGNMENTS:\n",1)
         # Compute sum of probability of all possible alignments by dynamic programming.
         # To do this, recursively compute the sum over all possible alignments for each
         # each pair of English prefix (indexed by ei) and French coverage (indexed by 
         # bitmap v), working upwards from the base case (ei=0, v=0) [i.e. forward chaining]. 
         # The final sum is the one obtained for the pair (ei=len(e), v=range(len(f))
        # maybe_write("\nDYNAMIC PROGRAMMING SUM OVER ALIGNMENTS\n",2)
      chart = [{} for _ in e] + [{}]
      chart[0][0] = 0.0
      for ei, sums in enumerate(chart[:-1]):
         for v in sums:
            for ej, logprob, fi, fj in alignments[ei]:
               if self.bitmap(range(fi,fj)) & v == 0:
                  new_v = self.bitmap(range(fi,fj)) | v
                  #            maybe_write("(%d, %s): %f + (%d, %d, %s): %f -> (%d, %s): %f\n" % 
                  #                     (ei, self.bitmap2str(v,len(f)), sums[v], 
                  #                     ei, ej, self.bitmap2str(self.bitmap(range(fi,fj)),len(f)), logprob, 
                  #                    ej, self.bitmap2str(new_v,len(f)), sums[v]+logprob), 2)
                  if new_v in chart[ej]:
                     chart[ej][new_v] = self.logadd10(chart[ej][new_v], sums[v]+logprob)
                  else:
                     chart[ej][new_v] = sums[v]+logprob
      goal = self.bitmap(range(len(f)))
      if goal in chart[len(e)]:
         #     maybe_write("\nTOTAL TM LOGPROB: %f\n" % chart[len(e)][goal],0)
         total_logprob += chart[len(e)][goal]
      else:
         total_logprob = -10000

         #         maybe_write("\n\n",2)
      return total_logprob
 
   def get_alignments(self, f, e):
      alignments = [[] for _ in e]
      for fi in xrange(len(f)):
         for fj in xrange(fi+1,len(f)+1):
            if f[fi:fj] in self.tm:
               for phrase in self.tm[f[fi:fj]]:
                  ephrase = tuple(phrase.english.split())
                  for ei in xrange(len(e)+1-len(ephrase)):
                     ej = ei+len(ephrase)
                     if ephrase == e[ei:ej]:
             #           maybe_write("%s ||| %d, %d : %d, %d ||| %s ||| %f\n" % 
 #                                   (" ".join(f[fi:fj]), fi, fj, ei, ej, " ".join(ephrase), phrase.logprob),1)
                        alignments[ei].append((ej, phrase.logprob, fi, fj))
      return alignments






