"""
core/NINJA_subgraph.py
"""

from __future__ import print_function

from build.ninja_lib import log

_ = log


def NinjaGraph(ru):
  n = ru.n

  ru.comment('Generated by %s' % __name__)

  n.build(['_gen/core/optview.h'], 'optview-gen', [],
          implicit=['_bin/shwrap/optview_gen'])
  n.newline()

  ru.asdl_library(
      'core/runtime.asdl',
      deps = ['//frontend/syntax.asdl'])