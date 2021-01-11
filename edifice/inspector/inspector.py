import inspect
import edifice as ed

class TreeView(ed.Component):

    @ed.register_props
    def __init__(self, title, on_click, initial_collapsed=False):
        super().__init__()
        self.collapsed = initial_collapsed

    def toggle(self, e):
        self.set_state(collapsed=not self.collapsed)

    def render(self):
        child_style = {"align": "left"}
        if self.collapsed:
            child_style["height"] = 0
        return ed.View(layout="column", style={"align": "top"})(
            ed.View(layout="row", style={"align": "left"})(
                ed.Icon("caret-right",
                        rotation=0 if self.collapsed else 90,
                        on_click=self.toggle,
                ).set_key("caret"),
                ed.Label(self.props.title, style={"margin-left": 5}, on_click=self.props.on_click).set_key("title"),
            ).set_key("root"),
            ed.View(layout="row", style=child_style)(
                ed.View(layout="column", style={"width": 20, }).set_key("indent"),
                ed.View(layout="column", style={"align": "top"})(
                    *[comp.set_key(str(i)) for i, comp in enumerate(self.props.children)]
                ).set_key("children")
            ).set_key("children")
        )

class StateView(ed.Component):

    @ed.register_props
    def __init__(self, component):
        super().__init__()

    def render(self):
        state = dict((k, v) for (k, v) in vars(self.props.component).items() if k[0] != "_")
        return ed.ScrollView(layout="column", style={"align": "top", "margin-left": 15})(
            *[ed.View(layout="row", style={"align": "left"})(
                  ed.Label(key + ":", style={"font-weight": 600, "width": 140}).set_key("key"),
                  ed.Label(state[key], style={}).set_key("value"),
              ).set_key(key) for key in state]
        )

class PropsView(ed.Component):

    @ed.register_props
    def __init__(self, props):
        super().__init__()

    def render(self):
        props = self.props.props
        return ed.ScrollView(layout="column", style={"align": "top", "margin-left": 15})(
            *[ed.View(layout="row", style={"align": "left"})(
                  ed.Label(key + ":", style={"font-weight": 600, "width": 140}).set_key("key"),
                  ed.Label(props[key], style={}).set_key("value"),
              ).set_key(key) for key in props._keys]
        )


class ComponentView(ed.Component):

    @ed.register_props
    def __init__(self, component):
        super().__init__()

    def render(self):
        component = self.props.component
        module = inspect.getmodule(component.__class__)
        lineno = None
        try:
            lineno = inspect.getsourcelines(component.__class__)[1]
        except:
            pass
        heading_style = {"font-size": "16px", "margin": 10, "margin-bottom": 0}

        return ed.View(layout="column", style={"align": "top", "min-width": 450, "min-height": 450})(
            ed.Label(component.__class__.__name__, style={"font-size": "20px", "margin": 10}).set_key("class_name"),
            ed.Label("Class defined in " + module.__file__ + ":" + str(lineno), style={"margin-left": 10}).set_key("file"),
            ed.Label("Props", style=heading_style).set_key("props_header"),
            PropsView(component.props).set_key("_props_view"),
            ed.Label("State", style=heading_style).set_key("state_header"),
            StateView(component).set_key("_state_view"),
        )


class Inspector(ed.Component):

    @ed.register_props
    def __init__(self, component_tree, root_component, refresh):
        super().__init__()
        self.selected = None
        self.component_tree = component_tree
        self.root_component = root_component

    def _refresh(self):
        with self.render_changes():
            self.component_tree, self.root_component = self.props.refresh()

    def _build_tree(self, root):
        children = self.component_tree[root]
        if isinstance(children, ed.Component):
            children = [children]

        if len(children) > 0:
            return TreeView(title=root.__class__.__name__, on_click=lambda e: self.set_state(selected=root),
                            initial_collapsed=len(children) > 1)(
                 *[self._build_tree(child) for child in children]
            )
        return ed.Label(root.__class__.__name__,
                       on_click=lambda e: self.set_state(selected=root))

    def render(self):
        return ed.View(layout="row")(
            ed.View(layout="column", style={"align": "top", "width": 251, "border-right": "1px solid gray"})(
                ed.View(layout="row", style={"align": "left", "height": 30})(
                    ed.Label("Edifice Inspector", style={"font-size": 18, "margin-left": 10, "width": 160}).set_key("title"),
                    ed.Icon("sync-alt", size=20, on_click=lambda e: self._refresh).set_key("refresh")
                ).set_key("heading"),
                ed.ScrollView(layout="column", style={"width": 250, "min-height": 450, "margin-top": 10})(
                    self._build_tree(self.root_component)
                ).set_key("tree"),
            ).set_key("left_pane"),
            ed.View(layout="column", style={"min-width": 450, "min-height": 450})(
                self.selected and ComponentView(self.selected).set_key("component_view")
            ).set_key("right_pane")
        )