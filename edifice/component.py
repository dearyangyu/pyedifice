import contextlib
import functools
import inspect
import typing as tp

import numpy as np
import pandas as pd


class PropsDict(object):
    """An immutable dictionary for storing props.

    Props may be accessed either by indexing (props["myprop"]) or by
    attribute (props.myprop).

    By convention, all PropsDict methods will start with _ to
    not conflict with keys.

    .. document private functions
    .. autoproperty:: _keys
    .. autoproperty:: _items
    """

    def __init__(self, dictionary: tp.Mapping[tp.Text, tp.Any]):
        super().__setattr__("_d", dictionary)

    def __getitem__(self, key):
        return self._d[key]

    def __setitem__(self, key, value):
        raise ValueError("Props are immutable")

    @property
    def _keys(self) -> tp.List[tp.Text]:
        """Returns the keys of the props dict as a list."""
        return list(self._d.keys())

    @property
    def _items(self) -> tp.List[tp.Any]:
        """Returns the (key, value) of the props dict as a list."""
        return list(self._d.items())

    def __len__(self):
        return len(self._d)

    def __iter__(self):
        return iter(self._d)

    def __contains__(self, k):
        return k in self._d

    def __getattr__(self, key):
        if key in self._d:
            return self._d[key]
        else:
            raise KeyError("%s not in props" % key)

    def __repr__(self):
        return "PropsDict(%s)" % repr(self._d)

    def __str__(self):
        return "PropsDict(%s)" % str(self._d)

    def __setattr__(self, key, value):
        raise ValueError("Props are immutable")


class Component(object):
    """Component.

    A Component is a stateful container wrapping a stateless render function.
    Components have both internal and external properties.

    The external properties, **props**, are passed into the Component by another
    Component's render function through the constructor. These values are owned
    by the external caller and should not be modified by this Component.
    They may be accessed via the field props (self.props), which is a PropsDict.
    A PropsDict allows iteration, get item (self.props["value"]), and get attribute
    (self.props.value), but not set item or set attribute. This limitation
    is set to protect the user from accidentally modifying props, which may cause
    bugs. (Note though that a mutable prop, e.g. a list, can still be modified;
    be careful not to do so)

    The internal properties, the **state**, belong to this Component, and may be
    used to keep track of internal state. You may set the state as
    attributes of the Component object, for instance self.my_state.
    You can initialize the state as usual in the constructor (e.g. self.my_state = {"a": 1}),
    and the state persists so long as the Component is still mounted.

    In most cases, changes in state would ideally trigger a rerender.
    There are two ways to ensure this.
    First, you may use the set_state function to set the state::

        self.set_state(mystate=1, myotherstate=2)

    You may also use the self.render_changes() context manager::

        with self.render_changes():
            self.mystate = 1
            self.myotherstate = 2

    When the context manager exits, a state change will be triggered.
    The render_changes() context manager also ensures that all state changes
    happen atomically: if an exception occurs inside the context manager,
    all changes will be unwound. This helps ensure consistency in the
    Component's state.

    Note if you set self.mystate = 1 outside the render_changes() context manager,
    this change will not trigger a re-render. This might be occasionally useful
    but usually is unintended.

    The main function of Component is render, which should return the subcomponents
    of this component. These may be your own higher-level components as well as
    the core Components, such as Label, Button, and View.
    Components may be composed in a tree like fashion:
    one special prop is children, which will always be defined (defaults to an
    empty list). The children prop can be set by calling another Component::

        View(layout="column")(
            View(layout="row")(
                Label("Username: "),
                TextInput()
            ),
            View(layout="row")(
                Label("Email: "),
                TextInput()
            ),
        )

    The render function is called when self.should_update(newprops, newstate)
    returns True. This function is called when the props change (as set by the
    render function of this component) or when the state changes (when
    using set_state or render_changes()). By default, all changes in newprops
    and newstate will trigger a re-render.
    
    When the component is rendered,
    the render function is called. This output is then compared against the output
    of the previous render (if that exists). The two renders are diffed,
    and on certain conditions, the Component objects from the previous render
    are maintained and updated with new props.

    Two Components belonging to different classes will always be re-rendered,
    and Components belonging to the same class are assumed to be the same
    and thus maintained (preserving the old state).

    When comparing a list of Components, the Component's **_key** attribute will
    be compared. Components with the same _key and same class are assumed to be
    the same. You can set the key using the set_key method, which returns the component
    to allow for chaining::

        View(layout="row")(
            MyComponent("Hello").set_key("hello"),
            MyComponent("World").set_key("world"),
        )

    If the _key is not provided, the diff algorithm will assign automatic keys
    based on index, which could result in subpar performance due to unnecessary rerenders.
    To ensure control over the rerender process, it is recommended to set_keys
    whenever you have a list of children.
    """

    _render_changes_context = None
    _ignored_variables = set()

    def __init__(self):
        super().__setattr__("_ignored_variables", set())
        if not hasattr(self, "_props"):
            self._props = {"children": []}

    def register_props(self, props: tp.Union[tp.Mapping[tp.Text, tp.Any], PropsDict]):
        """Register props.

        Call this function if you do not use the register_props decorator and you have
        props to register.
        """
        if "children" not in props:
            props["children"] = {}
        self._props = props

    def set_key(self, k: tp.Text):
        self._key = k
        return self

    @property
    def children(self):
        return self.props.children

    @property
    def props(self) -> PropsDict:
        return PropsDict(self._props)

    @contextlib.contextmanager
    def render_changes(self, ignored_variables: tp.Optional[tp.Sequence[tp.Text]] = None):
        """Context manager for managing changes to state.

        This context manager provides two functions:
        - Make a group of assignments to state atomically: if an exception occurs,
        all changes will be rolled back.
        - Renders changes to the state upon successful completion.

        Note that this context manager will not keep track of changes to mutable objects.

        Args:
            ignored_variables: an optional sequence of variables for the manager to ignore.
                               These changes will not be reverted upon exception.
        """
        entered = False
        ignored_variables = ignored_variables or set()
        ignored_variables = set(ignored_variables)
        exception_raised = False
        if super().__getattribute__("_render_changes_context") is None:
            super().__setattr__("_render_changes_context", {})
            super().__setattr__("_ignored_variables", ignored_variables)
            entered = True
        try:
            yield
        except Exception as e:
            exception_raised = True
            raise e
        finally:
            if entered:
                changes_context = super().__getattribute__("_render_changes_context")
                super().__setattr__("_render_changes_context", None)
                super().__setattr__("_ignored_variables", set())
                if not exception_raised:
                    self.set_state(**changes_context)

    def __getattribute__(self, k):
        changes_context = super().__getattribute__("_render_changes_context")
        ignored_variables = super().__getattribute__("_ignored_variables")
        if changes_context is not None and k in changes_context and k not in ignored_variables:
            return changes_context[k]
        return super().__getattribute__(k)


    def __setattr__(self, k, v):
        changes_context = super().__getattribute__("_render_changes_context")
        ignored_variables = super().__getattribute__("_ignored_variables")
        if changes_context is not None and k not in ignored_variables:
            changes_context[k] = v
        else:
            super().__setattr__(k, v)

    def set_state(self, **kwargs):
        """Set state and render changes.

        The keywords are the names of the state attributes of the class, e.g.
        for the state self.mystate, you call set_state with set_state(mystate=2).
        At the end of this call, all changes will be rendered.
        All changes are guaranteed to appear atomically: upon exception,
        no changes to state will occur.
        """
        should_update = self.should_update(PropsDict({}), kwargs)
        old_vals = {}
        try:
            for s in kwargs:
                if not hasattr(self, s):
                    raise KeyError
                old_val = super().__getattribute__(s)
                old_vals[s] = old_val
                super().__setattr__(s, kwargs[s])
            if should_update:
                self._controller._request_rerender([self], PropsDict({}), kwargs)
        except Exception as e:
            for s in old_vals:
                super().__setattr__(s, old_vals[s])
            raise e

    def should_update(self, newprops: PropsDict, newstate: tp.Mapping[tp.Text, tp.Any]) -> bool:
        """Determines if the component should rerender upon receiving new props and state.

        The arguments, newprops and newstate, reflect the props and state that change: they
        may be a subset of the props and the state. When this function is called,
        all props and state of this Component are the old values, so you can compare
        `component.props` and `newprops` to determine changes.

        By default, all changes to props and state will trigger a re-render. This behavior
        is probably desirable most of the time, but if you want custom re-rendering logic,
        you can override this function.

        Args:
            newprops: the new set of props
            newstate: the new set of state
        Returns:
            Whether or not the Component should be rerendered.
        """
        def should_update_helper(new_obj, old_obj):
            if isinstance(old_obj, Component) or isinstance(new_obj, Component):
                if old_obj.__class__ != new_obj.__class__:
                    return True
                if old_obj.should_update(new_obj.props, {}):
                    return True
            elif isinstance(old_obj, np_classes) or isinstance(new_obj, np_classes):
                if old_obj.__class__ != new_obj.__class__:
                    return True
                if not np.array_equal(old_obj, new_obj):
                    return True
            elif old_obj != new_obj:
                return True
            return False

        np_classes = (np.ndarray, pd.Series, pd.DataFrame, pd.Index)
        for prop, new_obj in newprops._items:
            old_obj = self.props[prop]
            if should_update_helper(new_obj, old_obj):
                return True
        for state, new_obj in newstate.items():
            old_obj = getattr(self, state)
            if should_update_helper(new_obj, old_obj):
                return True
        return False

    def did_mount(self):
        pass

    def will_unmount(self):
        pass

    def __call__(self, *args):
        children = [a for a in args if a]
        self._props["children"] = children
        return self

    def __hash__(self):
        return id(self)

    def _tags(self):
        classname = self.__class__.__name__
        return [
            "<%s id=0x%x %s>" % (classname, id(self), " ".join("%s=%s" % (p, val) for (p, val) in self.props._items if p != "children")),
            "</%s>" % (classname),
            "<%s id=0x%x %s />" % (classname, id(self), " ".join("%s=%s" % (p, val) for (p, val) in self.props._items if p != "children")),
        ]

    def __str__(self):
        tags = self._tags()
        if self.children:
            return "%s\n\t%s\n%s" % (tags[0], "\t\n".join(str(child) for child in self.children), tags[1])
        return tags[2]

    def render(self):
        """Logic for rendering, must be overridden.

        The render logic for this component, not implemented for this abstract class.
        The render function itself should be purely stateless, because the application
        state should not depend on whether or not the render function is called.
        """
        raise NotImplementedError


def register_props(f):
    """Decorator for __init__ function to record props.

    This decorator will record all arguments (both vector and keyword arguments)
    of the __init__ function as belonging to the props of the component.
    It will call Component.register_props to store these arguments in the
    props field of the Component.

    Arguments that begin with an underscore will be ignored.

    Example::

        class MyComponent(Component):

            @register_props
            def __init__(self, a, b=2, c="xyz", _d=None):
                pass

            def render(self):
                return View()(
                    Label(self.props.a),
                    Label(self.props.b),
                    Label(self.props.c),
                )

    MyComponent(5, c="w") will then have props.a=5, props.b=2, and props.c="w".
    props._d is undefined

    Args:
        f: the __init__ function of a Component subclass
    Returns:
        decorated function

    """
    @functools.wraps(f)
    def func(self, *args, **kwargs):
        varnames = f.__code__.co_varnames[1:]
        defaults = {
            k: v.default for k, v in inspect.signature(f).parameters.items() if v.default is not inspect.Parameter.empty and k[0] != "_"
        }
        name_to_val = defaults
        name_to_val.update(dict(filter((lambda tup: (tup[0][0] != "_")), zip(varnames, args))))
        name_to_val.update(dict((k, v) for (k, v) in kwargs.items() if k[0] != "_"))
        self.register_props(name_to_val)
        f(self, *args, **kwargs)

    return func

class BaseComponent(Component):

    def __init__(self):
        super().__init__()

class WidgetComponent(BaseComponent):

    def __init__(self):
        super().__init__()

class LayoutComponent(BaseComponent):

    def __init__(self):
        super().__init__()

class RootComponent(BaseComponent):

    def __init__(self):
        super().__init__()

    def _qt_update_commands(self, children, newprops, newstate):
        # Dummy
        return []
