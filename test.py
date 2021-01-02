import unittest
import unittest.mock
import react
from PyQt5 import QtWidgets

class MockComponent(react.Component):
    def __init__(self):
        super().__init__()
        class MockController(object):
            _request_rerender = unittest.mock.MagicMock()
        self._controller = MockController()

class MockBrokenComponent(react.Component):
    def __init__(self):
        super().__init__()
        class MockController(object):
            def _request_rerender(*args, **kwargs):
                raise ValueError("I am broken")
        self._controller = MockController()


class StorageManagerTestCase(unittest.TestCase):

    def test_record(self):
        class A(object):
            value = 0
        obj = A()
        with react._storage_manager() as storage_manager:
            storage_manager.set(obj, "value", 1)
            self.assertEqual(obj.value, 1)
        self.assertEqual(obj.value, 1)

    def test_record(self):
        class A(object):
            value = 0
        obj = A()
        try:
            with react._storage_manager() as storage_manager:
                storage_manager.set(obj, "value", 1)
                self.assertEqual(obj.value, 1)
                raise ValueError
        except ValueError:
            pass
        self.assertEqual(obj.value, 0)


class ComponentTestCase(unittest.TestCase):

    def test_render_changes(self):
        a = MockComponent()
        a.foo = 1
        a.bar = 2
        with a.render_changes():
            a.foo = 3
            self.assertEqual(a.foo, 3)
            a.bar = 0
        self.assertEqual(a.foo, 3)
        self.assertEqual(a.bar, 0)
        a._controller._request_rerender.assert_called_once_with(
            a, {}, dict(foo=3, bar=0))
        a._controller._request_rerender.reset_mock()
        try:
            with a.render_changes():
                a.bar = 1
                self.assertEqual(a.bar, 1)
                a.foo = 1 / 0
        except ZeroDivisionError:
            pass
        self.assertEqual(a.foo, 3)
        self.assertEqual(a.bar, 0)
        a._controller._request_rerender.assert_not_called()

    def test_state_change_unwind(self):
        a = MockBrokenComponent()
        a.foo = 1
        a.bar = 2

        exception_thrown = False
        try:
            with a.render_changes():
                a.foo = 3
                self.assertEqual(a.foo, 3)
                a.bar = 0
        except ValueError as e:
            if str(e) == "I am broken":
                exception_thrown = True

        self.assertTrue(exception_thrown)
        self.assertEqual(a.foo, 1)
        self.assertEqual(a.bar, 2)

        exception_thrown = False
        try:
            a.set_state(foo=3, bar=0)
        except ValueError as e:
            if str(e) == "I am broken":
                exception_thrown = True

        self.assertTrue(exception_thrown)
        self.assertEqual(a.foo, 1)
        self.assertEqual(a.bar, 2)

class QtTreeTestCase(unittest.TestCase):

    def test_button(self):
        app = QtWidgets.QApplication([])
        def on_click():
            pass
        button_str = "asdf"
        button = react.Button(title=button_str, on_click=on_click)
        button_tree = react.QtTree(button, [])
        qt_button = button.underlying
        commands = button_tree.gen_qt_commands()
        print(qt_button.clicked)
        print(qt_button.clicked.connect)
        print(qt_button.clicked.connect)
        self.assertCountEqual(commands, [(qt_button.setText, button_str), (qt_button.setStyleSheet, "QWidget{}"), (button.set_on_click, on_click)])

    def test_view_layout(self):
        app = QtWidgets.QApplication([])
        view_c = react.View(layout="column")
        self.assertEqual(view_c.underlying.__class__, QtWidgets.QVBoxLayout)
        view_r = react.View(layout="row")
        self.assertEqual(view_r.underlying.__class__, QtWidgets.QHBoxLayout)


    def test_view_change(self):
        app = QtWidgets.QApplication([])
        label1 = react.Label(text="A")
        label2 = react.Label(text="B")
        view = react.View(children=[label1])

        def label_tree(label):
            tree = react.QtTree(label, [])
            return tree, tree.gen_qt_commands()

        label1_tree, label1_commands = label_tree(label1)
        label2_tree, label2_commands = label_tree(label2)
        view_tree = react.QtTree(view, [label1_tree])
        commands = view_tree.gen_qt_commands()

        self.assertCountEqual(commands, label1_commands + [(view.underlying.insertWidget, 0, label1.underlying)])

        view_tree = react.QtTree(view, [label1_tree, label2_tree])
        commands = view_tree.gen_qt_commands()
        self.assertCountEqual(commands, label1_commands + label2_commands + [(view.underlying.insertWidget, 1, label2.underlying)])

        inner_view = react.View(children=[])

        view_tree = react.QtTree(view, [label2_tree, react.QtTree(inner_view, [])])
        commands = view_tree.gen_qt_commands()
        self.assertCountEqual(commands, label2_commands + [(view.delete_child, 0), (view.underlying.insertLayout, 1, inner_view.underlying)])

if __name__ == "__main__":
    unittest.main()
