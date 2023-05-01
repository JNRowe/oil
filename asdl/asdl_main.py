#!/usr/bin/env python2
"""
asdl_main.py - Generate Python and C from ASDL schemas.
"""
from __future__ import print_function

import optparse
import os
import sys

from asdl import ast
from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python
#from asdl.util import log

ARG_0 = os.path.basename(sys.argv[0])


def Options():
  """Returns an option parser instance."""

  p = optparse.OptionParser()
  p.add_option('--no-pretty-print-methods',
               dest='pretty_print_methods',
               action='store_false',
               default=True,
               help='Whether to generate pretty printing methods')

  # Control Python constructors

  # for hnode.asdl
  p.add_option('--py-init-N',
               dest='py_init_n',
               action='store_true',
               default=False,
               help='Generate Python __init__ that requires every field')

  # The default, which matches C++
  p.add_option('--init-zero-N',
               dest='init_zero_n',
               action='store_true',
               default=True,
               help='Generate 0 arg and N arg constructors, in Python and C++')

  return p


class UserType(object):
  """
  TODO: Delete this class after we have modules with 'use'?
  """

  def __init__(self, mod_name, type_name):
    self.mod_name = mod_name
    self.type_name = type_name

  def __repr__(self):
    return '<UserType %s %s>' % (self.mod_name, self.type_name)


def main(argv):
  o = Options()
  opts, argv = o.parse_args(argv)

  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  try:
    schema_path = argv[2]
  except IndexError:
    raise RuntimeError('Schema path required')

  schema_filename = os.path.basename(schema_path)
  if schema_filename in ('syntax.asdl', 'runtime.asdl'):
    app_types = {'id': UserType('id_kind_asdl', 'Id_t')}
  else:
    app_types = {}

  if action == 'c':  # Generate C code for the lexer
    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    v = gen_cpp.CEnumVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'cpp':  # Generate C++ code for ASDL schemas
    out_prefix = argv[3]

    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    # asdl/typed_arith.asdl -> typed_arith_asdl
    ns = os.path.basename(schema_path).replace('.', '_')

    with open(out_prefix + '.h', 'w') as f:
      guard = ns.upper()
      f.write("""\
// %s.h is generated by %s

#ifndef %s
#define %s

""" % (out_prefix, ARG_0, guard, guard))

      f.write("""\
#include <cstdint>
""")
      f.write("""
#include "mycpp/runtime.h"
""")
      if opts.pretty_print_methods:
        f.write("""\
#include "_gen/asdl/hnode.asdl.h"
using hnode_asdl::hnode_t;

""")

      if app_types:
        f.write("""\
#include "_gen/frontend/id_kind.asdl.h"
using id_kind_asdl::Id_t;

""")

      for use in schema_ast.uses:
        # Forward declarations in the header, like
        # namespace syntax_asdl { class command_t; }
        # must come BEFORE namespace, so it can't be in the visitor.

        # assume sum type for now!
        cpp_names = [
            'class %s;' % ast.TypeNameHeuristic(n) for n in use.type_names
        ]
        f.write('namespace %s_asdl { %s }\n' %
                (use.module_parts[-1], ' '.join(cpp_names)))
        f.write('\n')

      f.write("""\
namespace %s {

// use struct instead of namespace so 'using' works consistently
#define ASDL_NAMES struct

""" % ns)

      v = gen_cpp.ForwardDeclareVisitor(f)
      v.VisitModule(schema_ast)

      debug_info = {}
      v2 = gen_cpp.ClassDefVisitor(
          f,
          pretty_print_methods=opts.pretty_print_methods,
          debug_info=debug_info)
      v2.VisitModule(schema_ast)

      f.write("""
}  // namespace %s

#endif  // %s
""" % (ns, guard))

      try:
        debug_info_path = argv[4]
      except IndexError:
        pass
      else:
        with open(debug_info_path, 'w') as f:
          from pprint import pformat
          f.write('''\
cpp_namespace = %r
tags_to_types = \\
%s
''' % (ns, pformat(debug_info)))

      if not opts.pretty_print_methods:
        return

      with open(out_prefix + '.cc', 'w') as f:
        f.write("""\
// %s.cc is generated by %s

#include "%s.h"
#include <assert.h>
""" % (out_prefix, ARG_0, out_prefix))

        f.write("""\
#include "prebuilt/asdl/runtime.mycpp.h"  // generated code uses wrappers here
""")

        # To call pretty-printing methods
        for use in schema_ast.uses:
          f.write('#include "_gen/%s.asdl.h"  // "use" in ASDL \n' %
                  '/'.join(use.module_parts))

        f.write("""\

// Generated code uses these types
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__External;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::Field;
using hnode_asdl::color_e;

""")

        if app_types:
          f.write('using id_kind_asdl::Id_str;\n')

        f.write("""
namespace %s {

""" % ns)

        v3 = gen_cpp.MethodDefVisitor(f)
        v3.VisitModule(schema_ast)

        f.write("""
}  // namespace %s
""" % ns)

  elif action == 'mypy':  # Generated typed MyPy code
    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    try:
      abbrev_module_name = argv[3]
    except IndexError:
      abbrev_mod = None
    else:
      # Weird Python rule for importing: fromlist needs to be non-empty.
      abbrev_mod = __import__(abbrev_module_name, fromlist=['.'])

    f = sys.stdout

    # TODO: Remove Any once we stop using it
    f.write("""\
from asdl import pybase
from pylib.collections_ import OrderedDict
from typing import Optional, List, Tuple, Dict, Any, cast, TYPE_CHECKING
""")

    if schema_ast.uses:
      f.write('\n')
      f.write('if TYPE_CHECKING:\n')
    for use in schema_ast.uses:
      py_names = [ast.TypeNameHeuristic(n) for n in use.type_names]
      # indented
      f.write('  from _devbuild.gen.%s_asdl import %s\n' %
              (use.module_parts[-1], ', '.join(py_names)))
    f.write('\n')

    for typ in app_types.itervalues():
      if isinstance(typ, UserType):
        f.write('from _devbuild.gen.%s import %s\n' %
                (typ.mod_name, typ.type_name))
        # HACK
        f.write('from _devbuild.gen.%s import Id_str\n' % typ.mod_name)
        f.write('\n')

    if opts.pretty_print_methods:
      f.write("""
from asdl import runtime  # For runtime.NO_SPID
from asdl.runtime import NewRecord, NewLeaf
from _devbuild.gen.hnode_asdl import color_e, hnode, hnode_e, hnode_t, Field

""")

    abbrev_mod_entries = dir(abbrev_mod) if abbrev_mod else []
    v = gen_python.GenMyPyVisitor(
        f,
        abbrev_mod_entries,
        pretty_print_methods=opts.pretty_print_methods,
        py_init_n=opts.py_init_n)
    v.VisitModule(schema_ast)

    if abbrev_mod:
      f.write("""\
#
# CONCATENATED FILE
#

""")
      first, module = abbrev_module_name.rsplit('.', 1)
      dir_name = first.replace('.', '/')
      path = os.path.join(dir_name, module + '.py')
      with open(path) as in_f:
        f.write(in_f.read())

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('%s: FATAL: %s' % (ARG_0, e), file=sys.stderr)
    sys.exit(1)
