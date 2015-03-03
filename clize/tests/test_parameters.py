# clize -- A command-line argument parser for Python
# Copyright (C) 2011-2015 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

from sigtools import support, modifiers

from clize import parser, errors, Parameter, runner, parameters
from clize.tests import util


@util.testfunc
def check_repr(self, sig_str, annotation, str_rep):
    sig = support.s(sig_str, locals={'a': annotation})
    csig = parser.CliSignature.from_signature(sig)
    self.assertEqual(str_rep, str(csig))


@util.testfunc
def test_bad_param(self, sig_str, annotation, error=ValueError):
    sig = support.s(sig_str, locals={'a': annotation})
    self.assertRaises(error, parser.CliSignature.from_signature, sig)


@util.testfunc
def test_help(self, sig_info, doc, expected):
    sig_str, annotation, _ = sig_info
    f = support.f(sig_str, locals={'a': annotation})
    f.__doc__ = doc
    cli = runner.Clize.get_cli(f)
    self.assertEqual(expected.split(), cli('func', '--help').split())


@util.testfunc
def annotated_sigtests(self, sig_info, in_args, args, kwargs):
    sig_str, annotation, str_rep = sig_info
    sig = support.s(sig_str, locals={'a': annotation})
    csig = parser.CliSignature.from_signature(sig)
    ba = util.read_arguments(csig, in_args)
    self.assertEqual(ba.args, args)
    self.assertEqual(ba.kwargs, kwargs)


@util.testfunc
def annotated_sigerror_tests(self, sig_info, in_args,
                             exc=errors.BadArgumentFormat):
    sig_str, annotation, str_rep = sig_info
    sig = support.s(sig_str, locals={'a': annotation})
    csig = parser.CliSignature.from_signature(sig)
    self.assertRaises(exc, util.read_arguments, csig, in_args)


@check_repr
class RepTests(object):
    mapped_basic = ('par:a', parameters.mapped([
        ('greeting', ['hello'], 'h1'),
        ('parting', ['goodbye'], 'h2'),
        ]), 'par')
    mapped_default = ('par:a="greeting"', parameters.mapped([
        ('greeting', ['hello'], 'h1'),
        ('parting', ['goodbye'], 'h2'),
        ]), '[par]')
    mapped_alternate_list = ('par:a', parameters.mapped([
        ('greeting', ['hello'], 'h1'),
        ('parting', ['goodbye'], 'h2'),
        ], list_name="options"), 'par')
    mapped_no_list = ('par:a', parameters.mapped([
        ('greeting', ['hello'], 'h1'),
        ('parting', ['goodbye'], 'h2'),
        ], list_name=None), 'par')
    mapped_kw = ('*, par:a', parameters.mapped([
        ('greeting', ['hello'], 'h1'),
        ('parting', ['goodbye'], 'h2'),
        ], list_name=None), '--par=STR')
    mapped_force_icase = ('par:a', parameters.mapped([
        (1, ['thing'], 'h')
        ], case_sensitive=False), 'par')
    mapped_force_scase = ('par:a', parameters.mapped([
        (1, ['Thing'], 'h'),
        ], case_sensitive=True), 'par')
    mapped_imply_scase = ('par:a', parameters.mapped([
        (1, ['thing'], 'h'),
        (2, ['Thing'], 'h'),
        ]), 'par')
    mapped_bad_icase = ('par:a', parameters.mapped([
        (1, ['thing'], 'h'),
        (2, ['Thing'], 'h'),
        ], case_sensitive=False), 'par')

    oneof_basic = 'par:a', parameters.one_of('hello', 'goodbye', 'bye'), 'par'
    oneof_help = (
        'par:a', parameters.one_of(('hello', 'h1'), ('bye', 'h2')), 'par')

    multi_basic = '*, par:a', parameters.multi(), '[--par=STR...]'
    multi_req = '*, par:a', parameters.multi(1), '--par=STR...'
    multi_min = '*, par:a', parameters.multi(2), '--par=STR...'
    multi_max = '*, par:a', parameters.multi(max=2), '[--par=STR...]'
    multi_bound = '*, par:a', parameters.multi(min=2, max=3), '--par=STR...'
    multi_conv = '*, par:a', (parameters.multi(), int), '[--par=INT...]'
    multi_last_opt = (
        '*args, par:a', (parameters.multi(), Parameter.L),
        '[--par=STR...] [args...]')

    margs_basic = '*args:a', parameters.multi(), '[args...]'
    margs_req = '*args:a', parameters.multi(1), 'args...'
    margs_min = '*args:a', parameters.multi(2), 'args...'
    margs_max = '*args:a', parameters.multi(max=2), '[args...]'
    margs_bound = '*args:a', parameters.multi(min=2, max=3), 'args...'
    margs_conv = '*args:a', (parameters.multi(), int), '[args...]'
    margs_last_opt = (
        '*args:a, par=""', (parameters.multi(), Parameter.L),
        '[--par=STR] [args...]')

    @parameters.argument_decorator
    def _blank(arg):
        return arg + 'x'
    deco_blank_pos = 'par:a', _blank, 'par'
    deco_blank_posd = 'par:a="d"', _blank, '[par]'
    deco_blank_kw = '*, par:a', _blank, '--par=STR'
    deco_blank_kwd = '*, par:a="d"', _blank, '[--par=STR]'
    deco_blank_args = '*par:a', _blank, '[par...]'
    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _kw(arg, kw):
        return arg + kw
    deco_kw_pos = 'par:a', _kw, '--kw=STR par'
    deco_kw_posd = 'par:a="d"', _kw, '[--kw=STR par]'
    deco_kw_kw = '*, par:a', _kw, '--kw=STR --par=STR'
    deco_kw_kwd = '*, par:a="d"', _kw, '[--kw=STR --par=STR]'
    deco_kw_args = '*par:a', _kw, '[--kw=STR par...]'
    @parameters.argument_decorator
    @modifiers.autokwoargs
    def _kwdef(arg, kw='D'):
        return arg + kw
    deco_def_pos = 'par:a', _kwdef, '[--kw=STR] par'
    deco_def_posd = 'par:a="d"', _kwdef, '[[--kw=STR] par]'
    deco_def_kw = '*, par:a', _kwdef, '[--kw=STR] --par=STR'
    deco_def_kwd = '*, par:a="d"', _kwdef, '[[--kw=STR] --par=STR]'
    deco_def_args = '*par:a', _kwdef, '[[--kw=STR] par...]'
    @parameters.argument_decorator
    @modifiers.autokwoargs
    def _flag(arg, f=False):
        return arg + ('y' if f else 'n')
    deco_flag_pos = 'par:a', _flag, '[-f] par'
    deco_flag_posd = 'par:a="d"', _flag, '[[-f] par]'
    deco_flag_kw = '*, par:a', _flag, '[-f] --par=STR'
    deco_flag_kwd = '*, par:a="d"', _flag, '[[-f] --par=STR]'
    deco_flag_args = '*par:a', _flag, '[[-f] par...]'
    deco_flag_other = 'par:a, *, x=False', _flag, '[-x] [-f] par'
    @parameters.argument_decorator
    @modifiers.autokwoargs
    def _int(arg, i=0):
        return arg + str(i)
    deco_int_pos = 'par:a', _int, '[-i INT] par'
    deco_int_posd = 'par:a="d"', _int, '[[-i INT] par]'
    deco_int_kw = '*, par:a', _int, '[-i INT] --par=STR'
    deco_int_kwd = '*, par:a="d"', _int, '[[-i INT] --par=STR]'
    deco_int_args = '*par:a', _int, '[[-i INT] par...]'
    deco_int_other = 'par:a, *, x=False', _int, '[-x] [-i INT] par'
    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _all(arg, kw, flag=False, kwd='D', i=0):
        return arg, kw, flag, kwd, i
    _all_rep = '--kw=STR [--flag] [--kwd=STR] [-i INT] '
    deco_all_pos = 'par:a', _all, _all_rep + 'par'
    deco_all_posd = 'par:a="d"', _all, '[' + _all_rep + 'par]'
    deco_all_kw = '*, par:a', _all, _all_rep + '--par=STR'
    deco_all_kwd = '*, par:a="d"', _all, '[' + _all_rep + '--par=STR]'
    deco_all_args = '*par:a', _all, '[' + _all_rep + 'par...]'
    @parameters.argument_decorator
    @modifiers.kwoargs(start='why')
    def _inner(arg, why, zed='zed'):
        return '(' + arg + why + zed + ')'
    @parameters.argument_decorator
    @modifiers.kwoargs(start='ab')
    @modifiers.annotate(cd=_inner)
    def _nest(arg, ab, cd='cd'):
        return '(' + arg + ab + cd + ')'
    _nest_rep = '--ab=STR [--why=STR [--zed=STR] --cd=STR] '
    deco_nest_pos = 'par:a', _nest, _nest_rep + 'par'
    deco_nest_posd = 'par:a="d"', _nest, '[' + _nest_rep + 'par]'
    deco_nest_kw = '*, par:a', _nest, _nest_rep + '--par=STR'
    deco_nest_kwd = '*, par:a="d"', _nest, '[' + _nest_rep + '--par=STR]'
    deco_nest_args = '*par:a', _nest, '[' + _nest_rep + 'par...]'

    pn_pos = 'par:a', parameters.pass_name, ''
    pn_pos_first = 'par:a, other', parameters.pass_name, 'other'
    pn_pos_nextpicky = 'par:a, other:int', parameters.pass_name, 'other'
    pn_kw = '*, par:a', parameters.pass_name, ''


@test_bad_param
class BadParamTests(object):
    @parameters.argument_decorator
    def _with_pokarg(arg, invalid):
        raise NotImplementedError
    deco_with_pokarg = 'par: a', _with_pokarg

    pn_varargs = '*par: a', parameters.pass_name
    pn_varkwargs = '**par: a', parameters.pass_name


@annotated_sigtests
class MappedTests(object):
    exact_1 = RepTests.mapped_basic, ['hello'], ['greeting'], {}
    exact_2 = RepTests.mapped_basic, ['goodbye'], ['parting'], {}
    isec_1 = RepTests.mapped_basic, ['HElLo'], ['greeting'], {}
    isec_2 = RepTests.mapped_basic, ['GoODByE'], ['parting'], {}

    use_default = RepTests.mapped_default, [], [], {}

    exact_alternate = (
        RepTests.mapped_alternate_list, ['hello'], ['greeting'], {})
    exact_no_lisy = RepTests.mapped_no_list, ['hello'], ['greeting'], {}

    forced_icase_1 = RepTests.mapped_force_icase, ['thing'], [1], {}
    forced_icase_2 = RepTests.mapped_force_icase, ['ThiNG'], [1], {}

    implied_scase_1 = RepTests.mapped_imply_scase, ['thing'], [1], {}
    implied_scase_2 = RepTests.mapped_imply_scase, ['Thing'], [2], {}

    forced_scase_1 = RepTests.mapped_force_scase, ['Thing'], [1], {}

    def test_show_list(self):
        sig = support.s('par:a', locals={'a': RepTests.mapped_basic[1]})
        csig = parser.CliSignature.from_signature(sig)
        ba = util.read_arguments(csig, ['list'])
        par = csig.positional[0]
        self.assertEqual(par.show_list, ba.func)
        self.assertEqual(
            """name: Possible values for par:
            hello h1
            goodbye h2""".split(),
            ba.func('name', *ba.args, **ba.kwargs).split())

    def test_show_list_alt(self):
        sig = support.s('par:a',
                        locals={'a': RepTests.mapped_alternate_list[1]})
        csig = parser.CliSignature.from_signature(sig)
        ba = util.read_arguments(csig, ['options'])
        par = csig.positional[0]
        self.assertEqual(par.show_list, ba.func)
        self.assertEqual(
            """name: Possible values for par:
            hello h1
            goodbye h2""".split(),
            ba.func('name', *ba.args, **ba.kwargs).split())


@annotated_sigerror_tests
class MappedErrorTests(object):
    not_found = RepTests.mapped_basic, ['dog']
    forced_scase = RepTests.mapped_force_scase, ['thing']
    bas_icase = RepTests.mapped_bad_icase, ['anything'], ValueError
    alternate = RepTests.mapped_alternate_list, ['list']
    none = RepTests.mapped_no_list, ['list']


@test_help
class MappedHelpTests(object):
    basic = RepTests.mapped_basic, "par: type of greeting", """
        Usage: func par
        Arguments:
          par          type of greeting (use "list" for options)
        Other actions:
          -h, --help   Show the help
    """
    default = RepTests.mapped_default, "par: type of greeting", """
        Usage: func [par]
        Arguments:
          par          type of greeting (default: hello,
                       use "list" for options)
        Other actions:
          -h, --help   Show the help
    """
    alternate = RepTests.mapped_alternate_list, "par: type of greeting", """
        Usage: func par
        Arguments:
          par          type of greeting (use "options" for options)
        Other actions:
          -h, --help   Show the help
    """
    none = RepTests.mapped_no_list, "par: type of greeting", """
        Usage: func par
        Arguments:
          par          type of greeting
        Other actions:
          -h, --help   Show the help
    """
    kw = RepTests.mapped_kw, "par: type of greeting", """
        Usage: func [OPTIONS]
        Options:
          --par=STR   type of greeting
        Other actions:
          -h, --help  Show the help
    """


@annotated_sigtests
class OneOfTests(object):
    exact = RepTests.oneof_basic, ('hello',), ['hello'], {}
    icase = RepTests.oneof_basic, ('Hello',), ['hello'], {}

    def test_show_list(self):
        sig = support.s('par:a', locals={'a': RepTests.oneof_help[1]})
        csig = parser.CliSignature.from_signature(sig)
        ba = util.read_arguments(csig, ['list'])
        par = csig.positional[0]
        self.assertEqual(par.show_list, ba.func)
        self.assertEqual(
            """name: Possible values for par:
            hello h1
            bye h2""".split(),
            ba.func('name', *ba.args, **ba.kwargs).split())


@annotated_sigtests
class MultiTests(object):
    basic_none = RepTests.multi_basic, (), [], {'par': []}
    basic_one = RepTests.multi_basic, ('--par=one',), [], {'par': ['one']}
    basic_two = (
        RepTests.multi_basic, ('--par=one', '--par', 'two'),
        [], {'par': ['one', 'two']})

    conv = RepTests.multi_conv, ('--par=1', '--par', '2'), [], {'par': [1, 2]}

    req_met = (RepTests.multi_req, ('--par=1',), [], {'par': ['1']})

    min_met = (
        RepTests.multi_min, ('--par=1', '--par=2'), [], {'par': ['1', '2']})

    max_met_1 = RepTests.multi_max, (), [], {'par': []}
    max_met_2 = RepTests.multi_max, ('--par=1',), [], {'par': ['1']}
    max_met_3 = (
        RepTests.multi_max, ('--par=1', '--par=2'), [], {'par': ['1', '2']})

    last_opt = (
        RepTests.multi_last_opt, ('--par=1', '--par=2'),
        ['--par=2'], {'par': ['1']})

    a_basic_none = RepTests.margs_basic, (), [], {}
    a_basic_one = RepTests.margs_basic, ('one',), ['one'], {}
    a_basic_two = RepTests.margs_basic, ('one', 'two'), ['one', 'two'], {}

    a_conv = RepTests.margs_conv, ('1', '2'), [1, 2], {}

    a_req_met = RepTests.margs_req, ('1',), ['1'], {}

    a_min_met = RepTests.margs_min, ('1', '2'), ['1', '2'], {}

    a_max_met_1 = RepTests.margs_max, (), [], {}
    a_max_met_2 = RepTests.margs_max, ('1',), ['1'], {}
    a_max_met_3 = RepTests.margs_max, ('1', '2'), ['1', '2'], {}

    a_last_opt = (
        RepTests.margs_last_opt, ('1', '--par=2'), ['1', '--par=2'], {})


@annotated_sigerror_tests
class MultiErrorTests(object):
    req_not_met = RepTests.multi_req, (), errors.MissingRequiredArguments
    min_not_met_1 = (
        RepTests.multi_min, ('--par=one',), errors.NotEnoughValues)
    min_not_met_2 = (
        RepTests.multi_min, ('--par', 'one'), errors.NotEnoughValues)

    max_passed_1 = (
        RepTests.multi_max, ('--par=1', '--par=2', '--par=3'),
        errors.TooManyValues)
    max_passed_2 = (
        RepTests.multi_max, ('--par=1', '--par=2', '--par=3', '--par=4'),
        errors.TooManyValues)

    def test_message(self):
        sig_str, annotation, str_rep = RepTests.multi_bound
        sig = support.s(sig_str, locals={'a': annotation})
        csig = parser.CliSignature.from_signature(sig)

        try:
            util.read_arguments(csig, ('--par=1',))
        except errors.NotEnoughValues as e:
            self.assertEqual(e.message, "Received too few values for --par")

        try:
            util.read_arguments(csig,
                                ('--par=1', '--par=2', '--par=3', '--par=4'))
        except errors.TooManyValues as e:
            self.assertEqual(e.message, "Received too many values for --par")

    a_req_not_met = RepTests.margs_req, (), errors.MissingRequiredArguments
    a_min_not_met_1 = (
        RepTests.margs_min, ('one',), errors.NotEnoughValues)
    a_min_not_met_2 = (
        RepTests.margs_min, ('one',), errors.NotEnoughValues)

    a_max_passed_1 = RepTests.margs_max, ('1', '2', '3'), errors.TooManyValues
    a_max_passed_2 = (
        RepTests.margs_max, ('1', '2', '3', '4'), errors.TooManyValues)


@test_help
class MultiHelpTests(object):
    basic = RepTests.multi_basic, "par: addresses", """
        Usage: func [OPTIONS]
        Options:
          --par=STR   addresses
        Other actions:
          -h, --help  Show the help
    """


@annotated_sigtests
class DecoTests(object):
    blank_pos = RepTests.deco_blank_pos, ['1'], ['1x'], {}
    blank_posd = RepTests.deco_blank_posd, ['1'], ['1x'], {}
    blank_posd_d = RepTests.deco_blank_posd, [], [], {}
    blank_kw = RepTests.deco_blank_kw, ['--par=1'], [], {'par': '1x'}
    blank_kwd = RepTests.deco_blank_kwd, ['--par=1'], [], {'par': '1x'}
    blank_kwd_d = RepTests.deco_blank_kwd, [], [], {}
    blank_args = RepTests.deco_blank_args, ['1', '2'], ['1x', '2x'], {}
    blank_args_none = RepTests.deco_blank_args, [], [], {}

    kw_pos = RepTests.deco_kw_pos, ['--kw=y', '1'], ['1y'], {}
    kw_posd = RepTests.deco_kw_posd, ['--kw=y', '1'], ['1y'], {}
    kw_posd_d = RepTests.deco_kw_posd, [], [], {}
    kw_kw = RepTests.deco_kw_kw, ['--kw=y', '--par=1'], [], {'par': '1y'}
    kw_kwd = RepTests.deco_kw_kwd, ['--kw=y', '--par=1'], [], {'par': '1y'}
    kw_kwd_d = RepTests.deco_kw_kwd, [], [], {}
    kw_args = (
        RepTests.deco_kw_args, ['--kw=a', '1', '--kw=b', '2'],
        ['1a', '2b'], {})
    kw_args_none = RepTests.deco_kw_args, [], [], {}

    def_pos = RepTests.deco_def_pos, ['--kw=z', '1'], ['1z'], {}
    def_pos_D = RepTests.deco_def_pos, ['1'], ['1D'], {}
    def_posd = RepTests.deco_def_posd, ['--kw=z', '1'], ['1z'], {}
    def_posd_D = RepTests.deco_def_posd, ['1'], ['1D'], {}
    def_posd_d = RepTests.deco_def_posd, [], [], {}
    def_kw = RepTests.deco_def_kw, ['--kw=z', '--par=1'], [], {'par': '1z'}
    def_kwd = RepTests.deco_def_kwd, ['--kw=z', '--par=1'], [], {'par': '1z'}
    def_kwd_D = RepTests.deco_def_kwd, ['--par=1'], [], {'par': '1D'}
    def_kwd_d = RepTests.deco_def_kwd, [], [], {}
    def_args = (
        RepTests.deco_def_args, ['--kw=a', '1', '--kw=b', '2', '3'],
        ['1a', '2b', '3D'], {}
        )
    def_args_none = RepTests.deco_def_args, [], [], {}

    flag_pos = RepTests.deco_flag_pos, ['-f', '1'], ['1y'], {}
    flag_pos_n = RepTests.deco_flag_pos, ['1'], ['1n'], {}
    flag_posd = RepTests.deco_flag_posd, ['-f', '1'], ['1y'], {}
    flag_posd_n = RepTests.deco_flag_posd, ['1'], ['1n'], {}
    flag_posd_d = RepTests.deco_flag_posd, [], [], {}
    flag_kw = RepTests.deco_flag_kw, ['-f', '--par=2'], [], {'par': '2y'}
    flag_kw_n = RepTests.deco_flag_kw, ['--par=2'], [], {'par': '2n'}
    flag_kwd = RepTests.deco_flag_kwd, ['-f', '--par=2'], [], {'par': '2y'}
    flag_kwd_n = RepTests.deco_flag_kwd, ['--par=2'], [], {'par': '2n'}
    flag_kwd_d = RepTests.deco_flag_kwd, [], [], {}
    flag_args = RepTests.deco_flag_args, ['-f', '6', '5'], ['6y', '5n'], {}
    flag_args_none = RepTests.deco_flag_args, [], [], {}

    flag_redisp_a = RepTests.deco_flag_other, ['-fx', '2'], ['2y'], {'x': True}
    flag_redisp_b = RepTests.deco_flag_other, ['-xf', '2'], ['2y'], {'x': True}

    flag_pos = RepTests.deco_flag_pos, ['-f', '1'], ['1y'], {}
    flag_pos_abs = RepTests.deco_flag_pos, ['1'], ['1n'], {}

    int_redisp_a = RepTests.deco_int_other, ['-i5x', 'a'], ['a5'], {'x': True}
    int_redisp_b = RepTests.deco_int_other, ['-xi5', 'a'], ['a5'], {'x': True}

    all_pos = (
        RepTests.deco_all_pos, ['--kw=kw', 'par'],
        [('par', 'kw', False, 'D', 0)], {})

    nest = (
        RepTests.deco_nest_pos,
        ['--ab=1', '--why=2', '--zed=3', '--cd=4', 'a'],
        ['(a1(423))'], {}
        )
    nest_defaults = (
        RepTests.deco_nest_pos,
        ['--ab=1', 'a'],
        ['(a1cd)'], {}
        )

    def test_copy_required(self):
        obj = object()
        def deco(arg):
            raise NotImplementedError
        class BaseParamCls(parser.ParameterWithValue):
            required = obj
        class ParamCls(BaseParamCls, parameters.DecoratedArgumentParameter):
            pass
        p = ParamCls(decorator=deco, argument_name='test', display_name='test')
        self.assertTrue(obj is p.sub_required)

    def test_composed_property(self):
        class Shell(object):
            def __init__(self, real):
                self.real = real
            attr = parameters._ComposedProperty('attr')
        class Target(object):
            pass
        t = Target()
        s = Shell(t)
        self.assertRaises(AttributeError, lambda: s.attr)
        obj = object()
        s.attr = obj
        self.assertTrue(t.attr is obj)
        obj = object()
        t.attr = obj
        self.assertTrue(s.attr is obj)
        del s.attr
        self.assertRaises(AttributeError, lambda: s.attr)


MissingReq = errors.MissingRequiredArguments


@annotated_sigerror_tests
class DecoErrorTests(object):
    blank_missing = RepTests.deco_blank_pos, [], MissingReq
    pos_kw_missing = RepTests.deco_kw_pos, ['1'], MissingReq
    pos_kw_missing_after = RepTests.deco_kw_pos, ['1', '--kw=y'], MissingReq

    args_kwdef_noarg_1 = RepTests.deco_def_pos, ['1', '--kw=x'], MissingReq
    args_kwdef_noarg_2 = (
        RepTests.deco_def_pos, ['--kw=x', '1', '--kw=y'], MissingReq)
    args_flag_noarg_1 = (
        RepTests.deco_flag_args, ['1', '-f', '1', '-f'], MissingReq)
    args_flag_noarg_2 = (
        RepTests.deco_flag_pos, ['-f'], MissingReq)


@util.repeated_test
class DecoHelpTests(object):
    def _test_func(self, sig_str, annotation, doc, expected):
        f = support.f(sig_str, locals={'a': annotation})
        f.__doc__ = doc
        cli = runner.Clize.get_cli(f)
        self.assertEqual(expected.split(), cli('func', '--help').split())

    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _undoc(arg, kw, flag=False, kwd='D', i=0):
        raise NotImplementedError
    undoc = 'par: a', _undoc, "par: things", """
        Usage: func [OPTIONS] --kw=STR [--flag] [--kwd=STR] [-i INT] par
        Arguments:
            par     things
        Options:
            --kw=STR
            --flag
            --kwd=STR   (default: D)
            -i INT      (default: 0)
        Other actions:
            -h, --help  Show the help
    """


    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _doc(arg, kw, flag=False, kwd='D', i=0):
        """
        kw: KW

        flag: FLAG

        kwd: KWD

        i: I
        """
        raise NotImplementedError
    doc = 'par: a', _doc, "par: things", """
        Usage: func [OPTIONS] --kw=STR [--flag] [--kwd=STR] [-i INT] par
        Arguments:
            par     things
        Options:
            --kw=STR    KW
            --flag      FLAG
            --kwd=STR   KWD (default: D)
            -i INT      I (default: 0)
        Other actions:
            -h, --help  Show the help
    """


    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _label(arg, kw, flag=False, kwd='D', i=0):
        """

        Qualifies parameters of kind "_label":

        kw: KW

        flag: FLAG

        kwd: KWD

        i: I
        """
        raise NotImplementedError
    label = 'par: a', _label, "par: things", """
        Usage: func [OPTIONS] --kw=STR [--flag] [--kwd=STR] [-i INT] par
        Arguments:
            par     things
        Qualifies parameters of kind "_label":
            --kw=STR    KW
            --flag      FLAG
            --kwd=STR   KWD (default: D)
            -i INT      I (default: 0)
        Other actions:
            -h, --help  Show the help
    """

    @parameters.argument_decorator
    @modifiers.kwoargs(start='kw')
    def _subst(arg, kw, flag=False, kwd='D', i=0):
        """

        Qualifies parameters of kind "_label":

        kw: KW

        flag: FLAG

        kwd: KWD

        i: I
        """
        raise NotImplementedError
    subst = 'par: a', _subst, "par: things", """
        Usage: func [OPTIONS] --kw=STR [--flag] [--kwd=STR] [-i INT] par
        Arguments:
            par     things
        Qualifies parameters of kind "_label":
            --kw=STR    KW
            --flag      FLAG
            --kwd=STR   KWD (default: D)
            -i INT      I (default: 0)
        Other actions:
            -h, --help  Show the help
    """

    nest_doc = 'par: a', RepTests._nest, "par: things", """
        Usage: func [OPTIONS] --ab=STR [--why=STR [--zed=STR] --cd=STR] par
        Arguments:
            par     things
        Options:
            --ab=STR
            --cd=STR    (default: cd)
            --why=STR
            --zed=STR   (default: zed)
        Other actions:
            -h, --help  Show the help
    """

@annotated_sigtests
class PnTests(object):
    pn_pos_solo = RepTests.pn_pos, (), ['test'], {}
    pn_pos_first = RepTests.pn_pos_first, ('arg',), ['test', 'arg'], {}
    pn_kw_solo = RepTests.pn_kw, (), [], {'par': 'test'}

@annotated_sigerror_tests
class PnErrorTests(object):
    pn_pos_toomany = RepTests.pn_pos, ('arg',), errors.TooManyArguments
    pn_pos_errinnext = (
        RepTests.pn_pos_nextpicky, ('bad',), errors.BadArgumentFormat
        )

    def test_pn_pos_errinnext_context(self):
        sig_str, annotation, str_rep = RepTests.pn_pos_nextpicky
        sig = support.s(sig_str, locals={'a': annotation})
        csig = parser.CliSignature.from_signature(sig)
        try:
            util.read_arguments(csig, ('bad',))
        except errors.BadArgumentFormat as exc:
            self.assertEqual(exc.param.display_name, 'other')
