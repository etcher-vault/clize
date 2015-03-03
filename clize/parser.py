# clize -- A command-line argument parser for Python
# Copyright (C) 2011-2015 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

"""
interpret function signatures and read commandline arguments
"""

import itertools
from functools import partial, wraps

import six
from sigtools import modifiers

from clize import errors, util


class ParameterFlag(object):
    def __init__(self, name, prefix='clize.Parameter'):
        self.name = name
        self.prefix = prefix

    def __repr__(self):
        return '{0.prefix}.{0.name}'.format(self)


class Parameter(object):
    """Represents a CLI parameter.

    :param str display_name: The 'default' representation of the parameter.
    :param bool undocumented:
        If true, hides the parameter from the command help.
    :param last_option: If `True`, the parameter will set the `.posarg_only`
        flag on the bound arguments.

    Also available as `clize.Parameter`.
    """

    L = LAST_OPTION = ParameterFlag('LAST_OPTION')
    """Annotate a parameter with this and all following arguments will be
    processed as positional."""

    I = IGNORE = ParameterFlag('IGNORE')
    """Annotate a parameter with this and it will be dropped from the
    resulting CLI signature."""

    U = UNDOCUMENTED = ParameterFlag('UNDOCUMENTED')
    """Parameters annotated with this will be omitted from the
    documentation (``--help``)."""

    R = REQUIRED = ParameterFlag('REQUIRED')
    """Annotate a parameter with this to force it to be required.

    Mostly only useful for ``*args`` parameters. In other cases, simply don't
    provide a default value."""


    required = False
    """Is this parameter required?"""

    extras = ()
    """Iterable of extra parameters this parameter incurs"""

    def __init__(self, display_name, undocumented=False, last_option=None):
        self.display_name = display_name
        """The name used in printing this parameter."""
        self.undocumented = undocumented
        """If true, this parameter is hidden from the documentation."""
        self.last_option = last_option
        """If true, arguments after this parameter is triggered will all be
        processed as positional."""

    def read_argument(self, ba, i):
        """Reads one or more arguments from ``ba.in_args`` from position ``i``.

        :param clize.parser.CliBoundArguments ba:
            The bound arguments object this call is expected to mutate.
        :param int i:
            The current position in ``ba.args``.
        """
        raise NotImplementedError

    def apply_generic_flags(self, ba):
        """Called after `read_argument` in order to set attributes on ``ba``
        independently of the arguments.

        :param clize.parser.CliBoundArguments ba:
            The bound arguments object this call is expected to mutate.

        The base implementation of this method applies the `last_option`
        setting if applicable and discards itself from
        `CliBoundArguments.unsatisfied`
        """
        if self.last_option:
            ba.posarg_only = True
        ba.unsatisfied.discard(self)

    def unsatisfied(self, ba):
        """Called after processing arguments if this parameter required
        and not discarded from `.CliBoundArguments.unsatisfied`."""
        return True

    def post_parse(self, ba):
        """Called after all arguments are processed successfully."""

    def get_all_names(self):
        """Return a string with all of this parameter's names."""
        return self.get_full_name()

    def get_full_name(self):
        """Return a string that designates this parameter."""
        return self.display_name

    def __str__(self):
        """Return a string to represent this parameter in cli usage."""
        if self.required:
            return self.get_full_name()
        else:
            return '[{0}]'.format(self.get_full_name())

    def show_help(self, desc, after, f, cols):
        """Called by `~clize.help.ClizeHelp` to produce the parameter's
        description in the help output."""
        return (
            self.get_all_names(), (
                getattr(self, 'description', None) or desc
                ) + self.show_help_parens()
            )

    def show_help_parens(self):
        """Return a string to complement a parameter's description in the
        ``--help`` output."""
        s = ', '.join(self.help_parens())
        if s:
            return ' ({0})'.format(s)
        return ''

    def help_parens(self):
        """Return an iterable of strings to complement a parameter's
        description in the ``--help`` output. Used by `.show_help_parens`"""
        return ()

    def prepare_help(self, helper):
        """Called by `~clize.help.ClizeHelp` to allow parameters to
        complement the help.

        :param: clize.help.ClizeHelp helper: The object charged with
            displaying the help.
        """


class ParameterWithSourceEquivalent(Parameter):
    """Parameter that relates to a function parameter in the source.

    :param str argument_name: The name of the parameter.
    """
    def __init__(self, argument_name, **kwargs):
        super(ParameterWithSourceEquivalent, self).__init__(**kwargs)
        self.argument_name = argument_name


class HelperParameter(Parameter):
    """Parameter that doesn't appear in CLI signatures but is used for
    instance as the ``.sticky`` attribute of the bound arguments."""

    def __init__(self, **kwargs):
        super(HelperParameter, self).__init__(
            display_name='<internal>', **kwargs)


@modifiers.kwoargs(start='name')
def value_converter(func=None, name=None):
    def decorate(func):
        info = {
            'name': util.name_type2cli(func) if name is None else name,
        }
        try:
            func._clize__value_converter = info
            return func
        except (TypeError, AttributeError):
            @wraps(func)
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            _wrapper._clize__value_converter = info
            return _wrapper
    if func is not None:
        return decorate(func)
    return decorate


@value_converter(name='STR')
def identity(x=None):
    return x


_implicit_converters = {
    int: int,
    float: float,
    bool: bool,
    six.text_type: identity,
    six.binary_type: identity,
}


def get_value_converter(annotation):
    try:
        return _implicit_converters[annotation]
    except KeyError:
        pass
    if not getattr(annotation, '_clize__value_converter', False):
        raise ValueError('{0!r} is not a value converter'.format(annotation))
    return annotation


class ParameterWithValue(Parameter):
    """A parameter that takes a value from the arguments, with possible
    default and/or conversion.

    :param callable conv: A callable to convert the value or raise `ValueError`.
        Defaults to `.identity`.
    :param default: A default value for the parameter or `.util.UNSET`.
    """

    def __init__(self, conv=identity, default=util.UNSET,
                       **kwargs):
        super(ParameterWithValue, self).__init__(**kwargs)
        self.conv = conv
        """The function used for coercing the value into the desired format or
        type."""
        self.default = default
        """The default value used for the parameter, or `.util.UNSET` if there
        is no default value. Usually only used for displaying the help."""

    @property
    def required(self):
        """Tells if the parameter has no default value."""
        return self.default is util.UNSET

    def coerce_value(self, arg, ba):
        """Coerces ``arg`` using the `.conv` function. Raises
        `.errors.BadArgumentFormat` if the coercion function raises
        `ValueError`.
        """
        try:
            ret = self.conv(arg)
        except errors.CliValueError as e:
            exc = errors.BadArgumentFormat(self, e)
            exc.__cause__ = e
            raise exc
        except ValueError as e:
            exc = errors.BadArgumentFormat(self, repr(arg))
            exc.__cause__ = e
            raise exc
        else:
            return ret

    def get_value(self, ba, i):
        """Retrieves the "value" part of the argument in ``ba`` at
        position ``i``."""
        return ba.in_args[i]

    def help_parens(self):
        """Shows the default value in the parameter description."""
        if self.default != util.UNSET:
            yield 'default: ' + str(self.default)


class NamedParameter(Parameter):
    """Equivalent of a keyword-only parameter in python.

    :param aliases: The arguments that trigger this parameter. The first alias
        is used to refer to the parameter. The first one is picked as
        `.display_name` if unspecified.
    :type aliases: sequence of strings
    """
    def __init__(self, aliases, **kwargs):
        kwargs.setdefault('display_name', aliases[0])
        super(NamedParameter, self).__init__(**kwargs)
        self.aliases = aliases
        """The parameter's aliases, eg. "--option" and "-o"."""

    __key_count = itertools.count()
    @classmethod
    def alias_key(cls, name):
        """Sort key function to order aliases in source order, but with short
        forms(one dash) first."""
        return len(name) - len(name.lstrip('-')), next(cls.__key_count)

    def get_all_names(self):
        """Retrieves all aliases."""
        return ', '.join(sorted(self.aliases, key=self.alias_key)
            )

    @property
    def short_name(self):
        """Retrieves the shortest alias for displaying the parameter
        signature."""
        return min(self.aliases, key=len)

    def get_full_name(self):
        """Uses the shortest name instead of the display name."""
        return self.short_name

    def redispatch_short_arg(self, rest, ba, i):
        """Processes the rest of an argument as if it was a new one prefixed
        with one dash.

        For instance when ``-a`` is a flag in ``-abcd``, the object implementing
        it will call this to proceed as if ``-a -bcd`` was passed."""
        if not rest:
            return
        try:
            nparam = ba.sig.aliases['-' + rest[0]]
        except KeyError as e:
            raise errors.UnknownOption(e.args[0])
        orig_args = ba.in_args
        ba.in_args = ba.in_args[:i] + ('-' + rest,) + ba.in_args[i + 1:]
        try:
            nparam.read_argument(ba, i)
        finally:
            ba.in_args = orig_args
        ba.unsatisfied.discard(nparam)

    def get_value(self, ba, i):
        """Fetches the value after the ``=`` (``--opt=val``) or in the
        next argument (``--opt val``)."""
        arg = super(NamedParameter, self).get_value(ba, i)
        if arg.startswith('--'):
            name, glued, val = arg.partition('=')
        else:
            arg = arg.lstrip('-')
            if len(arg) > 1:
                glued = True
                val = arg[1:]
            else:
                glued = False
        if not glued:
            try:
                val = ba.in_args[i+1]
            except IndexError:
                raise errors.MissingValue
        ba.skip = not glued
        return val


class FlagParameter(NamedParameter, ParameterWithSourceEquivalent):
    """A named parameter that takes no argument.

    :param value: The value when the argument is present.
    :param false_value: The value when the argument is given one of the
        false value triggers using ``--param=xyz``.
    """

    false_triggers = '0', 'n', 'no', 'f', 'false'
    """Values for which ``--flag=X`` will consider the argument false and
    will pass `.false_value` to the function. In all other cases `.value`
    is passed."""

    def __init__(self, value, false_value, **kwargs):
        super(FlagParameter, self).__init__(**kwargs)
        self.value = value
        """The value passed to the function if the flag is activated,
        usually `True`."""
        self.false_value = false_value
        """The value passed to the function if the flag is not activated,
        usually `False`."""

    def read_argument(self, ba, i):
        """Overrides `NamedParameter`'s value-getting behavior to allow no
        argument to be passed after the flag is named."""
        arg = ba.in_args[i]
        if arg[1] == '-':
            ba.kwargs[self.argument_name] = (
                self.value if self.is_flag_activation(arg)
                else self.false_value
                )
        else:
            ba.kwargs[self.argument_name] = self.value
            self.redispatch_short_arg(arg[2:], ba, i)


    def is_flag_activation(self, arg):
        """Checks if an argument triggers the true or false value."""
        if arg[1] != '-':
            return True
        arg, sep, val = arg.partition('=')
        return (
            not sep or
            val and val.lower() not in self.false_triggers
            )


class OptionParameter(NamedParameter, ParameterWithValue,
                      ParameterWithSourceEquivalent):
    """A named parameter that takes an argument."""

    def read_argument(self, ba, i):
        """Stores the argument in `CliBoundArguments.kwargs` if it isn't
        already present."""
        if self.argument_name in ba.kwargs:
            raise errors.DuplicateNamedArgument()
        val = self.get_value(ba, i)
        ba.kwargs[self.argument_name] = self.coerce_value(val, ba)

    def format_type(self):
        """Returns a string designation of the value type."""
        return util.name_type2cli(self.conv)

    def get_all_names(self):
        """Appends the value type to all aliases."""
        names = super(OptionParameter, self).get_all_names()
        return names + (' ' if len(names) == 2 else '=') + self.format_type()

    def get_full_name(self):
        """Appends the value type to the shortest alias."""
        sn = super(OptionParameter, self).get_full_name()
        return (' ' if len(sn) == 2 else '=').join((sn, self.format_type()))

def split_int_rest(s):
    for i, c, in enumerate(s):
        if not c.isdigit():
            return s[:i], s[i:]
    return s, ''

class IntOptionParameter(OptionParameter):
    """A named parameter that takes an integer as argument. The short form
    of it can be chained with the short form of other named parameters."""

    def read_argument(self, ba, i):
        """Handles redispatching after a numerical value."""
        if self.argument_name in ba.kwargs:
            raise errors.DuplicateNamedArgument()
        arg = ba.in_args[i]
        if arg.startswith('--'):
            super(IntOptionParameter, self).read_argument(ba, i)
            return

        arg = arg.lstrip('-')[1:]
        if not arg:
            super(IntOptionParameter, self).read_argument(ba, i)
            return

        val, rest = split_int_rest(arg)
        ba.kwargs[self.argument_name] = self.coerce_value(val, ba)

        self.redispatch_short_arg(rest, ba, i)


class PositionalParameter(ParameterWithValue, ParameterWithSourceEquivalent):
    """Equivalent of a positional-only parameter in python."""

    def read_argument(self, ba, i):
        """Stores the argument in `CliBoundArguments.args`."""
        ba.args.append(self.coerce_value(self.get_value(ba, i), ba))

    def help_parens(self):
        """Puts the value type in parenthesis since it isn't shown in
        the parameter's signature."""
        if self.conv is not identity:
            yield 'type: ' + util.name_type2cli(self.conv)
        for s in super(PositionalParameter, self).help_parens():
            yield s


class MultiParameter(ParameterWithValue):
    """Parameter that can collect multiple values."""

    def __init__(self, min, max, **kwargs):
        super(MultiParameter, self).__init__(**kwargs)
        self.min = min
        """The minimum amount of values this parameter accepts."""
        self.max = max
        """The maximum amount of values this parameter accepts."""

    @property
    def required(self):
        """Returns if there is a minimum amount of values required."""
        return self.min

    def get_collection(self, ba):
        """Return an object that new values will be appended to."""
        raise NotImplementedError

    def read_argument(self, ba, i):
        """Adds passed argument to the collection returned
        by `get_collection`."""
        val = self.coerce_value(self.get_value(ba, i), ba)
        col = self.get_collection(ba)
        col.append(val)
        if self.min <= len(col):
            ba.unsatisfied.discard(self)
        if self.max is not None and self.max < len(col):
            raise errors.TooManyValues

    def apply_generic_flags(self, ba):
        """Doesn't automatically mark the parameter as satisfied."""
        if self.last_option:
            ba.posarg_only = True

    def unsatisfied(self, ba):
        """Lets `errors.MissingRequiredArguments` be raised or raises
        `errors.NotEnoughValues` if arguments were passed but not enough
        to meet `.min`."""
        if not ba.args or len(ba.unsatisfied) > 1:
            return True
        raise errors.NotEnoughValues

    def get_full_name(self):
        """Adds an elipsis to the parameter name."""
        return super(MultiParameter, self).get_full_name() + '...'


class ExtraPosArgsParameter(MultiParameter, PositionalParameter):
    """Parameter that forwards all remaining positional arguments to the
    callee.

    Used to convert ``*args``-like parameters.
    """

    def __init__(self, required=False, min=None, max=None, **kwargs):
        min = bool(required) if min is None else min
        super(ExtraPosArgsParameter, self).__init__(min=min, max=max, **kwargs)

    def get_collection(self, ba):
        """Uses `CliBoundArguments.args` to collect the remaining arguments."""
        return ba.args

    def apply_generic_flags(self, ba):
        """Sets itself as sticky parameter so that `errors.TooManyArguments`
        is not raised when processing further parameters."""
        super(ExtraPosArgsParameter, self).apply_generic_flags(ba)
        ba.sticky = self


class AppendArguments(HelperParameter, MultiParameter):
    """Helper parameter that collects multiple values to be passed as
    positional arguments to the callee.

    Similar to `ExtraPosArgsParameter` but does not correspond to a parameter
    in the source."""

    def __init__(self, **kwargs):
        super(AppendArguments, self).__init__(min=0, max=None, **kwargs)

    def get_collection(self, ba):
        """Uses `CliBoundArguments.args` to collect the remaining arguments."""
        return ba.args


class IgnoreAllArguments(HelperParameter, Parameter):
    """Helper parameter for `.FallbackCommandParameter` that ignores the
    remaining arguments."""

    def read_argument(self, ba, i):
        """Does nothing, ignoring all arguments processed."""
        pass


class FallbackCommandParameter(NamedParameter):
    """Parameter that sets an alternative function when triggered. When used
    as an argument other than the first all arguments are discarded."""

    def __init__(self, func, **kwargs):
        super(FallbackCommandParameter, self).__init__(**kwargs)
        self.func = func
        """The function that will be called if this parameter is mentionned."""

    @util.property_once
    def description(self):
        """Use `.func`'s docstring to provide the parameter
        description."""
        try:
            return self.func.helper.description
        except AttributeError:
            pass

    def read_argument(self, ba, i):
        """Clears all processed arguments, sets up `.func` to be called later,
        and lets all remaining arguments be collected as positional if this
        was the first argument."""
        ba.args[:] = [ba.name + ' ' + self.display_name]
        ba.kwargs.clear()
        ba.post_name.append(ba.in_args[i])
        ba.func = self.func
        ba.posarg_only = True
        ba.sticky = IgnoreAllArguments() if i else AppendArguments()


class AlternateCommandParameter(FallbackCommandParameter):
    """Parameter that sets an alternative function when triggered. Cannot
    be used as any argument but the first."""

    def read_argument(self, ba, i):
        """Raises an error when this parameter is used after other arguments
        have been given."""
        if i:
            raise errors.ArgsBeforeAlternateCommand(self)
        return super(AlternateCommandParameter, self).read_argument(ba, i)


def parameter_converter(obj):
    """Decorates a callable to be interpreted as a parameter converter
    when passed as an annotation.

    It will be called with an `inspect.Parameter` object and a sequence of
    objects passed as annotations, without the parameter converter itself.
    It is expected to return a `clize.parser.Parameter` instance or
    `Parameter.IGNORE`."""
    obj._clize__parameter_converter = True
    return obj


def is_parameter_converter(obj):
    return getattr(obj, '_clize__parameter_converter', False)


def unimplemented_parameter(argument_name, **kwargs):
    raise ValueError(
        "This converter cannot convert parameter {0!r},".format(argument_name)
        )


@modifiers.autokwoargs
def use_class(
        pos=unimplemented_parameter, varargs=unimplemented_parameter,
        named=unimplemented_parameter, varkwargs=unimplemented_parameter,
        kwargs={}):
    """Creates a parameter converter similar to the default converter that
    picks one of 4 factory functions depending on the type of parameter.

    :param pos: The parameter factory for positional parameters.
    :param varargs: The parameter factory for ``*args``-like parameters.
    :param named: The parameter factory for keyword parameters.
    :param varkwargs: The parameter factory for ``**kwargs``-like parameters.
    :type pos: callable that returns a `Parameter` instance
    :type varargs: callable that returns a `Parameter` instance
    :type named: callable that returns a `Parameter` instance
    :type varkwargs: callable that returns a `Parameter` instance
    :param collections.abc.Mapping kwargs: additional arguments to pass
        to the chosen factory.
    """
    return parameter_converter(
        partial(_use_class, pos, varargs, named, varkwargs, kwargs))


@modifiers.autokwoargs
def use_mixin(cls, kwargs={}):
    """Like ``use_class``, but creates classes inheriting from ``cls`` and
    one of ``PositionalParameter``, ``ExtraPosArgsParameter``, and
    ``OptionParameter``

    :param cls: The class to use as mixin.
    :param collections.abc.Mapping kwargs: additional arguments to pass
        to the chosen factory.
    """
    class _PosWithMixin(cls, PositionalParameter): pass
    class _VarargsWithMixin(cls, ExtraPosArgsParameter): pass
    class _NamedWithMixin(cls, OptionParameter): pass
    return use_class(pos=_PosWithMixin, varargs=_VarargsWithMixin,
                     named=_NamedWithMixin,
                     kwargs=kwargs)


def _use_class(pos_cls, varargs_cls, named_cls, varkwargs_cls, kwargs,
               param, annotations):
    named = param.kind in (param.KEYWORD_ONLY, param.VAR_KEYWORD)
    aliases = [param.name]
    default = util.UNSET
    conv = identity

    kwargs = dict(
        kwargs,
        argument_name=param.name,
        undocumented=Parameter.UNDOCUMENTED in annotations,
        )

    if param.default is not param.empty:
        default = param.default

    if Parameter.REQUIRED in annotations:
        kwargs['required'] = True

    if Parameter.LAST_OPTION in annotations:
        kwargs['last_option'] = True

    set_coerce = False
    for thing in annotations:
        if isinstance(thing, Parameter):
            return thing
        if callable(thing):
            if is_parameter_converter(thing):
                raise ValueError(
                    "A custom parameter converter must be the first element "
                    "of a parameter's annotation")
            try:
                conv = get_value_converter(thing)
            except ValueError:
                pass
            else:
                if set_coerce:
                    raise ValueError(
                        "Coercion function specified twice in annotation: "
                        "{0.__name__} {1.__name__}".format(conv, thing))
                conv = conv
                set_coerce = True
                continue
        if isinstance(thing, six.string_types):
            if not named:
                raise ValueError("Cannot give aliases for a positional "
                                 "parameter.")
            if len(thing.split()) > 1:
                raise ValueError("Cannot have whitespace in aliases.")
            if thing in aliases:
                raise ValueError("Duplicate alias " + repr(thing))
            aliases.append(thing)
            continue
        if isinstance(thing, ParameterFlag):
            continue
        raise ValueError(thing)

    kwargs['default'] = default if not kwargs.get('required') else util.UNSET
    kwargs['conv'] = conv
    if not set_coerce and default is not util.UNSET and default is not None:
        kwargs['conv'] = get_value_converter(type(default))

    if named:
        kwargs['aliases'] = [
            util.name_py2cli(alias, named)
            for alias in aliases]
        if param.kind == param.VAR_KEYWORD:
            return varkwargs_cls(**kwargs)
        return named_cls(**kwargs)
    else:
        kwargs['display_name'] = util.name_py2cli(param.name)
        if param.kind == param.VAR_POSITIONAL:
            return varargs_cls(**kwargs)
        return pos_cls(**kwargs)

def pos_parameter(required=False, **kwargs):
    return PositionalParameter(**kwargs)

def named_parameter(**kwargs):
    if kwargs['default'] is False and kwargs['conv'] is bool:
        del kwargs['default'], kwargs['conv']
        return FlagParameter(value=True, false_value=False, **kwargs)
    elif kwargs['conv'] is _implicit_converters[int]:
        return IntOptionParameter(**kwargs)
    else:
        return OptionParameter(**kwargs)

default_converter = use_class(
    pos=pos_parameter, varargs=ExtraPosArgsParameter,
    named=named_parameter,
    )
"""The default parameter converter. It is described in detail in :ref:`default-converter`."""


def _develop_extras(params):
    for param in params:
        yield param
        for subparam in _develop_extras(param.extras):
            yield subparam


class CliSignature(object):
    """A collection of parameters that can be used to translate CLI arguments
    to function arguments.

    :param iterable parameters: The parameters to use.

    .. attribute:: converter
       :annotation: = clize.parser.default_converter

       The converter used by default in case none is present in the
       annotations.

    .. attribute:: parameters

        An ordered dict of all parameters of this cli signature.

    .. attribute:: positional

        List of positional parameters.

    .. attribute:: alternate

        List of parameters that initiate an alternate action.

    .. attribute:: named

        List of named parameters that aren't in `.alternate`.

    .. attribute:: aliases
        :annotation: = {}

        Maps parameter names to `NamedParameter` instances.

    .. attribute:: required
        :annotation: = set()

        A set of all required parameters.
    """

    converter = default_converter

    def __init__(self, parameters):
        params = self.parameters = util.OrderedDict()
        pos = self.positional = []
        named = self.named = []
        alt = self.alternate = []
        aliases = self.aliases = {}
        required = self.required = set()
        for param in _develop_extras(parameters):
            required_ = getattr(param, 'required', False)
            func = getattr(param, 'func', None)
            aliases_ = getattr(param, 'aliases', None)

            if required_:
                required.add(param)

            if aliases_ is not None:
                for alias in aliases_:
                    existing = aliases.get(alias)
                    if existing is not None:
                        raise ValueError(
                            "Parameters {0.display_name} and {1.display_name} "
                            "use a duplicate alias {2!r}."
                            .format(existing, param, alias)
                            )
                    aliases[alias] = param

            if func:
                alt.append(param)
            elif aliases_ is not None:
                named.append(param)
            else:
                pos.append(param)
            params[getattr(param, 'argument_name', param.display_name)] = param

    @classmethod
    def from_signature(cls, sig, extra=(), **kwargs):
        """Takes a signature object and returns an instance of this class
        deduced from it.

        :param inspect.Signature sig: The signature object to use.
        :param iterable extra: Extra parameter instances to include.
        """
        return cls(
            parameters=itertools.chain(
                filter(lambda x: x is not Parameter.IGNORE,
                    (cls.convert_parameter(param)
                    for param in sig.parameters.values())
                ), extra), **kwargs)

    @classmethod
    def convert_parameter(cls, param):
        """Convert a python parameter to a CLI parameter."""
        if param.annotation != param.empty:
            annotations = util.maybe_iter(param.annotation)
        else:
            annotations = []

        if Parameter.IGNORE in annotations:
            return Parameter.IGNORE

        for i, annotation in enumerate(annotations):
            if getattr(annotation, '_clize__parameter_converter', False):
                conv = annotation
                annotations = annotations[:i] + annotations[i+1:]
                break
        else:
            conv = cls.converter

        return conv(param, annotations)



    def read_arguments(self, args, name):
        """Returns a `.CliBoundArguments` instance for this CLI signature
        bound to the given arguments.

        :param sequence args: The CLI arguments, minus the script name.
        :param str name: The script name.
        """
        return CliBoundArguments(self, args, name)

    def __str__(self):
        return ' '.join(
            str(p)
            for p in itertools.chain(self.named, self.positional)
            if not p.undocumented
            )


class _SeekFallbackCommand(object):
    """Context manager that tries to seek a fallback command if an error was
    raised."""
    def __enter__(self):
        pass

    def __exit__(self, typ, exc, tb):
        if exc is None:
            return
        try:
            pos = exc.pos
            ba = exc.ba
        except AttributeError:
            return

        for i, arg in enumerate(ba.in_args[pos + 1:], pos +1):
            param = ba.sig.aliases.get(arg, None)
            if param in ba.sig.alternate:
                try:
                    param.read_argument(ba, i)
                except errors.ArgumentError:
                    continue
                ba.unsatisfied.clear()
                return True


class CliBoundArguments(object):
    """Command line arguments bound to a `.CliSignature` instance.

    :param CliSignature sig: The signature to bind against.
    :param sequence args: The CLI arguments, minus the script name.
    :param str name: The script name.

    .. attribute:: sig

        The signature being bound to.

    .. attribute:: in_args

        The CLI arguments, minus the script name.

    .. attribute:: name

        The script name.

    .. attribute:: args
        :annotation: = []

        List of arguments to pass to the target function.

    .. attribute:: kwargs
        :annotation: = {}

        Mapping of named arguments to pass to the target function.

    .. attribute:: meta
        :annotation: = {}

        A dict for parameters to store data for the duration of the
        argument processing.

    .. attribute:: func
        :annotation: = None

        If not `None`, replaces the target function.

    .. attribute:: post_name
        :annotation: = []

        List of words to append to the script name when passed to the target
        function.

    The following attributes only exist while arguments are being processed:

    .. attribute:: posparam
       :annotation: = iter(sig.positional)

       The iterator over the positional parameters used to process positional
       arguments.

    .. attribute:: sticky
       :annotation: = None

       If not `None`, a parameter that will keep receiving positional
       arguments.

    .. attribute:: posarg_only
       :annotation: = False

       Arguments will always be processed as positional when this is set to
       `True`.

    .. attribute:: skip
       :annotation: = 0

       Amount of arguments to skip.

    .. attribute:: unsatisfied
       :annotation: = set(<required parameters>)

       Required parameters that haven't yet been satisfied.

    """


    def __init__(self, sig, args, name):
        self.sig = sig
        self.name = name
        self.in_args = tuple(args)
        self.func = None
        self.post_name = []
        self.args = []
        self.kwargs = {}
        self.meta = {}

        self.posparam = iter(self.sig.positional)
        self.sticky = None
        self.posarg_only = False
        self.skip = 0
        self.unsatisfied = set(self.sig.required)

        with _SeekFallbackCommand():
            for i, arg in enumerate(self.in_args):
                if self.skip > 0:
                    self.skip -= 1
                    continue
                with errors.SetArgumentErrorContext(pos=i, val=arg, ba=self):
                    if self.posarg_only or arg[0] != '-' or len(arg) < 2:
                        if self.sticky is not None:
                            param = self.sticky
                        else:
                            try:
                                param = next(self.posparam)
                            except StopIteration:
                                exc = errors.TooManyArguments(
                                    self.in_args[i:])
                                exc.__cause__ = None
                                raise exc
                    elif arg == '--':
                        self.posarg_only = True
                        continue
                    else:
                        if arg.startswith('--'):
                            name = arg.partition('=')[0]
                        else:
                            name = arg[:2]
                        try:
                            param = self.sig.aliases[name]
                        except KeyError:
                            raise errors.UnknownOption(name)
                    with errors.SetArgumentErrorContext(param=param):
                        param.read_argument(self, i)
                        param.apply_generic_flags(self)

        if not self.func:
            if self.unsatisfied:
                unsatisfied = []
                for p in self.unsatisfied:
                    with errors.SetArgumentErrorContext(param=p):
                        if p.unsatisfied(self):
                            unsatisfied.append(p)
                if unsatisfied:
                    raise errors.MissingRequiredArguments(unsatisfied)

            for p in self.sig.parameters.values():
                p.post_parse(self)

        del self.sticky, self.posarg_only, self.skip, self.unsatisfied

    def __iter__(self):
        yield self.func
        yield self.post_name
        yield self.args
        yield self.kwargs
