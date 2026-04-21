import networkx as nx
from networkx.drawing.nx_pydot import write_dot

# ---------------------------------------------------------------------------
# Topologie GEMMA standard (source : GEMMA-vide.pdf / norme ADEPA)
# ---------------------------------------------------------------------------
GEMMA_ALLOWED_TRANSITIONS = frozenset([
    # A
    ("A1", "F1"), ("A1", "F2"),("A1", "F4"), ("A1", "F5"),
    ("A2", "A1"),
    ("A3", "A4"), 
    ("A4", "F1"),
    ("A5", "A6"), ("A5", "A7"),
    ("A6", "A1"),
    ("A7", "A4"), ("A7", "A6"),
    # F
    ("F1", "A2"), ("F1", "A3"), 
    ("F1", "D1"), ("F1", "D2"), ("F1", "D3"),
    ("F1", "F3"), ("F1", "F4"), ("F1", "F5"), ("F1", "F6"),
    ("F2", "F1"),
    ("F3", "A1"), 
    ("F4", "A6"), 
    ("F5", "F1"), ("F5", "F4"),
    ("F6", "F1"), ("F6", "D1"),
    # D
    ("D1", "A5"), ("D1", "D2"),
    ("D2", "A5"), 
    ("D3", "D2"), ("D3", "A2"), ("D3", "A3")
])


class GemmaTransitionsTools:
    def __init__(self, transitions):
        """
        transitions: liste de tuples (origine, destination)
        """
        self.transitions = transitions
        self.graph = self._build_graph(transitions)

    def get_layout_positions(self, layout='spring', scale=500):
        """
        Retourne un dictionnaire {etat: (x, y)} pour placer les états sur le canvas.
        layout: 'spring', 'shell', 'circular', 'planar', 'kamada_kawai'
        scale: facteur d'échelle pour adapter à la taille du canvas
        """
        if layout == 'spring':
            pos = nx.spring_layout(self.graph, scale=scale)
        elif layout == 'shell':
            pos = nx.shell_layout(self.graph, scale=scale)
        elif layout == 'circular':
            pos = nx.circular_layout(self.graph, scale=scale)
        elif layout == 'planar':
            pos = nx.planar_layout(self.graph, scale=scale)
        elif layout == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(self.graph, scale=scale)
        else:
            pos = nx.spring_layout(self.graph, scale=scale)
        # Conversion en tuples (float -> int)
        return {k: (int(v[0]), int(v[1])) for k, v in pos.items()}

    def _build_graph(self, transitions):
        G = nx.DiGraph()
        for origin, dest in transitions:
            G.add_edge(origin, dest)
        return G

    def validate(self, emergency_state=None):
        """
        Validation du graphe :
        - états inaccessibles
        - cycles
        - états bloquants
        - accès à l'arrêt d'urgence (optionnel)
        """
        inaccessible = []
        cycles = list(nx.simple_cycles(self.graph))
        blocking = [n for n in self.graph.nodes if self.graph.out_degree(n) == 0]
        if emergency_state:
            dangerous = [n for n in self.graph.nodes if not nx.has_path(self.graph, n, emergency_state)]
        else:
            dangerous = []
        return {
            "inaccessible": inaccessible,
            "cycles": cycles,
            "blocking": blocking,
            "dangerous": dangerous
        }

    def simulate(self, initial_state, events):
        """
        Simule une séquence d'états à partir d'un état initial et d'une liste d'événements.
        """
        state = initial_state
        path = [state]
        for event in events:
            found = False
            for _, dest in self.graph.out_edges(state):
                # Ici, on suppose que l'événement n'est pas stocké, à adapter si besoin
                state = dest
                path.append(state)
                found = True
                break
            if not found:
                break
        return path

    def export_diagram(self, filename):
        """
        Exporte le graphe au format DOT (Graphviz)
        """
        write_dot(self.graph, filename)
