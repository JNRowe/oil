#!/usr/bin/env python2
"""
build/NINJA_subgraph.py

Directory structure:

# These are the code generators.  Could nested like asdl/asdl_main too
_bin/
  shwrap/
    asdl_main
    mycpp_main
    lexer_gen
    ...

# These
_build/
  NINJA/  # part of the Ninja graph
    asdl.asdl_main/
      all-pairs.txt
      deps.txt

  gen/
    asdl/
      hnode.asdl.{cc,h}
    bin/
      osh_eval.mycpp.cc  -- suffix is the generator
    core/
      runtime.asdl.{cc,h}
      optview.gen.h
    frontend/
      syntax.asdl.{cc,h}
      types.asdl.h  # no .cc file
    mycpp/
      examples/
        expr_asdl.{cc,h}
        containers.mycpp.cc
        containers_raw.mycpp.cc
        containers.pea.cc
        containers_raw.pea.cc

# C code shared with the Python build
# eventually this can be moved into Ninja
_devbuild/
  gen/
    osh-lex.h
    osh-types.h
    id.h
    grammar_nt.h

    runtime_asdl.py

build/
  NINJA-steps.sh  # for building stubs
"""

from __future__ import print_function

import os
import subprocess
import sys

def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def shwrap_py(n, main_py, deps_base_dir='_build/NINJA', rule='write-shwrap-py'):
  rel_path, _ = os.path.splitext(main_py)
  py_module = rel_path.replace('/', '.')  # asdl/asdl_main.py -> asdl.asdl_main

  deps_path = os.path.join(deps_base_dir, py_module, 'deps.txt')
  with open(deps_path) as f:
    deps = [line.strip() for line in f]

  deps.remove(main_py)  # raises ValueError if it's not there

  basename = os.path.basename(rel_path)
  n.build('_bin/shwrap/%s' % basename, rule, [main_py] + deps)
  n.newline()


def asdl_cpp(n, asdl_path, pretty_print_methods=True):
  # to create _gen/mycpp/examples/expr.asdl.h
  prefix = '_gen/%s' % asdl_path

  if pretty_print_methods:
    outputs = [prefix + '.cc', prefix + '.h']
    asdl_flags = '' 
  else:
    outputs = [prefix + '.h']
    asdl_flags = '--no-pretty-print-methods'

  debug_mod = '%s_debug.py' % prefix 
  outputs.append(debug_mod)

  # NOTE: Generating syntax_asdl.h does NOT depend on hnode_asdl.h, but
  # COMPILING anything that #includes it does.  That is handled elsewhere.

  n.build(outputs, 'asdl-cpp', asdl_path,
          implicit=['_bin/shwrap/asdl_main'],
          variables=[
            ('action', 'cpp'),
            ('out_prefix', prefix),
            ('asdl_flags', asdl_flags),
            ('debug_mod', debug_mod),
          ])
  n.newline()


def NinjaGraph(n):

  n.comment('Generated by %s' % __file__)
  n.newline()

  # Preprocess one translation unit
  n.rule('write-shwrap-py',
         # $in must start with main program
         command='build/NINJA-steps.sh write-shwrap py $out $in',
         description='make-pystub $out $in')
  n.newline()

  n.rule('write-shwrap-mycpp',
         # $in must start with main program
         command='build/NINJA-steps.sh write-shwrap mycpp $out $in',
         description='make-pystub $out $in')
  n.newline()

  n.rule('asdl-cpp',
         command='_bin/shwrap/asdl_main $action $asdl_flags $in $out_prefix $debug_mod',
         description='asdl_main $action $asdl_flags $in $out_prefix $debug_mod')
  n.newline()

  #
  # shwrap
  #

  # All the code generators from NINJA-config.sh
  #
  # TODO: could be moved into asdl/NINJA_subgraph.py, etc.
  shwrap_py(n, 'asdl/asdl_main.py')
  shwrap_py(n, 'core/optview_gen.py')
  shwrap_py(n, 'frontend/consts_gen.py')
  shwrap_py(n, 'frontend/flag_gen.py')
  shwrap_py(n, 'frontend/lexer_gen.py')
  shwrap_py(n, 'frontend/option_gen.py')
  shwrap_py(n, 'oil_lang/grammar_gen.py')
  shwrap_py(n, 'osh/arith_parse_gen.py')

  shwrap_py(n, 'mycpp/mycpp_main.py',
            deps_base_dir='prebuilt/ninja',
            rule='write-shwrap-mycpp')

  # This is Python 3, but the wrapper still works
  shwrap_py(n, 'pea/pea_main.py',
            deps_base_dir='prebuilt/ninja')

  #
  # ASDL
  #

  asdl_cpp(n, 'asdl/hnode.asdl', pretty_print_methods=False)
  asdl_cpp(n, 'frontend/syntax.asdl')
  asdl_cpp(n, 'frontend/types.asdl', pretty_print_methods=False)
  asdl_cpp(n, 'core/runtime.asdl')

  #
  # Other code generators
  #

  n.rule('consts-gen',
         command='_bin/shwrap/consts_gen $action $out_prefix',
         description='consts_gen $action $out_prefix')

  n.rule('flag-gen',
         command='_bin/shwrap/flag_gen $action $out_prefix',
         description='flag_gen $action $out_prefix')

  n.rule('option-gen',
         command='_bin/shwrap/option_gen $action $out_prefix',
         description='consts_gen $action $out_prefix')

  n.rule('optview-gen',
         # uses shell style
         command='_bin/shwrap/optview_gen > $out',
         description='optview_gen > $out')

  n.rule('arith-parse-gen',
         # uses shell style
         command='_bin/shwrap/arith_parse_gen > $out',
         description='arith-parse-gen > $out')

  prefix = '_gen/frontend/id_kind.asdl'
  n.build([prefix + '.h', prefix + '.cc'], 'consts-gen', [],
          implicit=['_bin/shwrap/consts_gen'],
          variables=[
            ('out_prefix', prefix),
            ('action', 'cpp'),
          ])
  n.newline()

  # Similar to above
  prefix = '_gen/frontend/consts'
  n.build([prefix + '.h', prefix + '.cc'], 'consts-gen', [],
          implicit=['_bin/shwrap/consts_gen'],
          variables=[
            ('out_prefix', prefix),
            ('action', 'cpp-consts'),
          ])
  n.newline()

  prefix = '_gen/frontend/arg_types'
  n.build([prefix + '.h', prefix + '.cc'], 'flag-gen', [],
          implicit=['_bin/shwrap/flag_gen'],
          variables=[
            ('out_prefix', prefix),
            ('action', 'cpp'),
          ])
  n.newline()

  prefix = '_gen/frontend/option.asdl'
  # no .cc file
  n.build([prefix + '.h'], 'option-gen', [],
          implicit=['_bin/shwrap/option_gen'],
          variables=[
            ('out_prefix', prefix),
            ('action', 'cpp'),
          ])
  n.newline()

  n.build(['_gen/core/optview.h'], 'optview-gen', [],
          implicit=['_bin/shwrap/optview_gen'])
  n.newline()

  n.build(['_gen/osh/arith_parse.cc'], 'arith-parse-gen', [],
          implicit=['_bin/shwrap/arith_parse_gen'])
  n.newline()
