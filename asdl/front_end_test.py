#!/usr/bin/env python2
"""
front_end_test.py: Tests for front_end.py
"""
from __future__ import print_function

import cStringIO
import unittest

from asdl import front_end  # module under test
from asdl import ast


class FrontEndTest(unittest.TestCase):

  def testLoadSchema(self):
    with open('asdl/examples/typed_demo.asdl') as f:
      schema_ast = front_end.LoadSchema(f, {}, verbose=True)
    print(schema_ast)

  def testSharedVariant(self):
    with open('asdl/examples/shared_variant.asdl') as f:
      schema_ast = front_end.LoadSchema(f, {}, verbose=False)
    print(schema_ast)

  def testSharedVariantCode(self):
    # generated by build/dev.sh minimal
    from _devbuild.gen.shared_variant_asdl import (double_quoted, expr, expr_e,
                                                   word_part, word_part_e)
    print(double_quoted)

    print(expr)
    print(expr_e)

    print(word_part)
    print(word_part_e)

    # These have the same value!
    self.assertEqual(65, expr_e.DoubleQuoted)
    self.assertEqual(expr_e.DoubleQuoted, word_part_e.DoubleQuoted)

    d = double_quoted(5, ['foo', 'bar'])
    d.PrettyPrint()
    print()

    b = expr.Binary(d, d, [42, 43])
    b.PrettyPrint()

  def _assertParse(self, code_str):
    f = cStringIO.StringIO(code_str)
    p = front_end.ASDLParser()
    schema_ast = p.parse(f)
    print(schema_ast)
    # For now just test its type
    self.assert_(isinstance(schema_ast, ast.Module))

  def testParse(self):
    self._assertParse("""
module foo {
  -- these are invalid, but checked in name resolution stage
  point = (int? x, int* y)

  action = Foo | Bar(point z)

  foo = (List[int] span_ids)
  bar = (Dict[string, int] options)

  -- this check happens later
  does_not_resolve = (typo zz)

  color = Red | Green

  color2 = Red | Green generate []

  color3 = Red | Green
           generate [integers]

  -- New optional lists
  spam = (Optional[List[int]] pipe_status)
  -- Nicer way of writing it
  -- spam2 = (array[int]? pipe_status)
}
""")

  def _assertParseError(self, code_str):
    f = cStringIO.StringIO(code_str)
    p = front_end.ASDLParser()
    try:
      schema_ast = p.parse(f)
    except front_end.ASDLSyntaxError as e:
      print(e)
    else:
      self.fail("Expected parse failure: %r" % code_str)

  def testParseErrors(self):
    # Need field name
    self._assertParseError('module foo { t = (int) }')

    # Need []
    self._assertParseError('module foo { t = (List foo) }')

    # Shouldn't have []
    self._assertParseError('module foo { t = (string[string] a) }')

    # Not enough params
    self._assertParseError('module foo { t = (Dict[] a) }')
    self._assertParseError('module foo { t = (Dict[string] a) }')
    self._assertParseError('module foo { t = (Dict[string, ] a) }')

    self._assertParseError('module foo { ( }')

    # Abandoned syntax
    self._assertParseError('module foo { simple: integers = A | B }')

    self._assertParseError('module foo { integers = A | B generate }')

    self._assertParseError(
        'module foo { integers = A | B generate [integers, ,] }')

    self._assertParseError('module foo { integers = A | B generate [invalid] }')

  def _assertResolve(self, code_str):
    f = cStringIO.StringIO(code_str)
    schema_ast = front_end.LoadSchema(f, {})

    print(type(schema_ast))
    print(schema_ast)

  def testResolve(self):
    self._assertResolve("""
module foo {
  point = (int x, int y)
  place = None | Two(point a, point b)
  options = (Dict[string, int] names)
}
""")

  def _assertResolveError(self, code_str):
    f = cStringIO.StringIO(code_str)
    try:
      schema_ast = front_end.LoadSchema(f, {})
    except front_end.ASDLSyntaxError as e:
      print(e)
    else:
      self.fail("Expected name resolution error: %r" % code_str)

  def testResolveErrors(self):
    self._assertResolveError("""
module foo {
  place = None | Two(typo b)
}
""")

    # Optional integer isn't allowed, because C++ can't express it
    # Integers are initialized to -1
    self._assertResolveError('module foo { t = (int? status) }')

    # Optional simple sum isn't allowed
    self._assertResolveError('''
        module foo { 
          color = Red | Green
          t = (color? status)
        }
        ''')

  def testAstNodes(self):
    # maybe[string]
    n1 = ast.NamedType('string')
    print(n1)

    n2 = ast.ParameterizedType('Optional', [n1])
    print(n2)

    n3 = ast.ParameterizedType('Dict', [n1, ast.NamedType('int')])
    print(n3)


if __name__ == '__main__':
  unittest.main()
