import graphviz
import copy
import os, errno

def silentremove(filename):
    """ Function to surpress errors when handling files """
    try:
        os.remove(filename)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occurred
    
def sort_leq(sorts, s1, s2):
    """ Checks if s1 <= s2 in the sort hierarchy, that is if s2 is more specific than s1. """
    s1, s2 = s1.replace("_1_", "").replace("_2_", ""), s2.replace("_1_", "").replace("_2_", "")

    if s1 not in sorts.keys() or s2 not in sorts.keys():
        return False

    while s1 != s2 and s2 != "_":
        # Generalise sort of s2
        s2 = sorts[s2]

    if s1 == s2:
        return True
    else:
        return False

def find_most_common_sort(sorts, s1, s2):
    """ Find most specific common sort of s1 and s2, returns bottom if no sort in common """
    if sort_leq(sorts, s1, s2):
        return s1
    elif sort_leq(sorts, s2, s1):
        return s2
    else:
        while s1 != s2:
            s1 = sorts[s1]
            s2 = sorts[s2]
        return s1

def powerset(s):
    """ Simple powerset helper function """
    x = len(s)
    masks = [1 << i for i in range(x)]
    for i in range(1 << x):
        yield [ss for mask, ss in zip(masks, s) if i & mask]


class FeatureStructure:
    def __init__(self, sorts, feat, nodes, root, typing_func, trans_func):
        """
        sorts:          {String: String}:           A dictionary of all possible sorts, including the most general sort, 
                                                    defining the sort hierarchy with key being more specific than value. 
                                                    If sort is already most general its value is "_"
        feat:           [String]:                   A list of possible features.
        nodes:          [String]:                   A list of node names, containing the root node. They are only for indexing, generated nodes will be of the form _Q_i, avoid these names.
        root:           String:                     Name of the root node.
        typing_func     {String: String}:           A dictionary of nodes as keys and sorts as values. 
        trans_func      {(String, String): String}: Transition function with keys as (f, q) where f is feature defined in feat, and q is a node. The values are nodes themselves.
        """
        self.sorts = sorts
        self.feat = feat
        self.nodes = nodes
        self.root = root
        self.typing_func = typing_func
        self.trans_func = trans_func

        # Check invalid structures
        # Test root
        if not root in nodes:
            raise Exception("Root not in nodes, please specify a valid feature structure.")
        
        for q in nodes:
            # Test node types
            if q not in typing_func.keys():
                raise Exception("A node does not have a sort defined, please specify a vlaid feature structure.")
            # Test types
            if not typing_func[q] in sorts.keys():
                raise Exception("A node has invalid sort, please specify a valid feature structure.")
        
        for (f, q) in trans_func.keys():
            # Test features
            if not f in feat:
                raise Exception("A feature is not in Feat, please specify a valid feature structure.")
            # Test domain of transition
            if not q in nodes:
                raise Exception("A transition starts from a nonexisting node, please specify a valid feature structure.")
            # Test range of transition
            if not trans_func[(f, q)] in nodes:
                raise Exception("A transition leads to a nonexisting node, please specify a valid feature structure.")       

    def __str__(self):
        """ Define how to print feature structures to console """
        feat = f"Feat:\n {' '.join(self.feat)}\n\n"

        sorts = "Sort hierarchy: \n"
        for (k, v) in self.sorts.items():
            if k != "_":
                sorts += f"{k} > {v} \n"
        sorts += "\n"

        root = f"Root: {self.root}\n\n"

        types = "Types: \n"
        for (k, v) in self.typing_func.items():
            types += f"{k} : {v} \n"
        types += "\n"

        trans = "Transitions: \n"
        for (k, v) in self.trans_func.items():
            trans += f"{k[1]} --- {k[0]} ---> {v} \n"

        return feat + sorts + root + types + trans

    def __repr__(self):
        """ Called from interactive prompt """
        return self.__str__()

    def __eq__(self, fs):
        """ Overrides the default implementation of equality, used for testing only """
        if not isinstance(fs, FeatureStructure):
            return False
        
        return set(self.nodes) == set(fs.nodes) and self.root == fs.root and self.typing_func == fs.typing_func and self.trans_func == fs.trans_func

    def plot(self, name="Feature Structure", folder = "Feature Structures/plots/", filename="fs.gv", view=False):
        """ Plot a feature structure as a graph, using graphviz """
        g = graphviz.Digraph(name)
        g.attr(rankdir='LR', size='8,5')
        g.attr('node', shape='circle')

        for q in self.nodes:
            g.node(f"{q} - {self.typing_func[q]}")

        for k in self.trans_func.keys():
            g.edge(f"{k[1]} - {self.typing_func[k[1]]}",  f"{self.trans_func[k]} - {self.typing_func[self.trans_func[k]]}", label = k[0])

        if view:
            g.view()

        g.render(folder + filename)
        silentremove(folder + filename)

    def subsumes(self, fs, f):
        """ Checks feature structure subsumption in a BFS manner """
        if not isinstance(fs, FeatureStructure):
            raise Exception("Object not a feature structure.")

        morph_f, morph_t = f

        queue1 = [self.root]
        visited1 = []
        queue2 = [fs.root]
        visited2 = []

        while len(queue1):
            q1, *queue1 = queue1
            q2, *queue2 = queue2      

            if self.typing_func[q1] not in morph_t.keys() or not sort_leq(fs.sorts, morph_t[self.typing_func[q1]], fs.typing_func[q2]):
                return False

            gen1 = [(f, q) for (f, q) in self.trans_func.keys() if q == q1]
            gen2 = [(f, q) for (f, q) in fs.trans_func.keys() if q == q2]

            flag = False
            for (f1, q1) in gen1:
                for (f2, q2) in gen2:
                    if(
                        f1 in morph_f.keys() and
                        morph_f[f1] == f2 and 
                        self.typing_func[self.trans_func[(f1, q1)]] in morph_t.keys() and
                        sort_leq(fs.sorts, morph_t[self.typing_func[self.trans_func[(f1, q1)]]], fs.typing_func[fs.trans_func[(f2, q2)]]) and
                        not (self.trans_func[(f1, q1)] == q1 and fs.trans_func[(f2, q2)] != q2)                  
                    ):
                        flag = True
                        if self.trans_func[(f1, q1)] not in visited1 and fs.trans_func[(f2, q2)] not in visited2:
                            queue1.append(self.trans_func[(f1, q1)])
                            visited1.append(q1)
                            queue2.append(fs.trans_func[(f2, q2)])
                            visited2.append(q2)
                        break
                if flag and not (len(set(queue1)) != len(queue1) and len(set(queue2)) == len(queue2)):
                    flag = False
                else:
                    return False
        return True

    def subsumes_monic(self, fs, f):
        """ Checks if the subsumption map is injective """
        if not isinstance(fs, FeatureStructure):
            raise Exception("Object not a feature structure.")

        morph_f, morph_t = f
        morph_h = {}

        queue1 = [self.root]
        visited1 = []
        queue2 = [fs.root]
        visited2 = []

        while len(queue1):
            q1, *queue1 = queue1
            q2, *queue2 = queue2      

            if self.typing_func[q1] not in morph_t.keys() or not sort_leq(fs.sorts, morph_t[self.typing_func[q1]], fs.typing_func[q2]):
                return False

            gen1 = [(f, q) for (f, q) in self.trans_func.keys() if q == q1]
            gen2 = [(f, q) for (f, q) in fs.trans_func.keys() if q == q2]

            if len(gen1) == 0 and len(gen2) == 0:
                morph_h[q1] = q2

            flag = False
            for (f1, q1) in gen1:
                for (f2, q2) in gen2:
                    if(
                        f1 in morph_f.keys() and
                        morph_f[f1] == f2 and 
                        sort_leq(fs.sorts, morph_t[self.typing_func[self.trans_func[(f1, q1)]]], fs.typing_func[fs.trans_func[(f2, q2)]]) and
                        not (self.trans_func[(f1, q1)] == q1 and fs.trans_func[(f2, q2)] != q2)                  
                    ):
                        flag = True
                        morph_h[q1] = q2
                        if self.trans_func[(f1, q1)] not in visited1 and fs.trans_func[(f2, q2)] not in visited2:
                            queue1.append(self.trans_func[(f1, q1)])
                            visited1.append(q1)
                            queue2.append(fs.trans_func[(f2, q2)])
                            visited2.append(q2)
                        break
                if flag and not (len(set(queue1)) != len(queue1) and len(set(queue2)) == len(queue2)):
                    flag = False
                else:
                    return False
        return len(set(morph_h.values())) == len(list(morph_h.values()))

    def subsumes_epic(self, fs, f):
        """ Checks if the subsumption map is surjective """
        if not isinstance(fs, FeatureStructure):
            raise Exception("Object not a feature structure.")

        morph_f, morph_t = f

        queue1 = [self.root]
        visited1 = []
        queue2 = [fs.root]
        visited2 = []

        while len(queue1):
            q1, *queue1 = queue1
            q2, *queue2 = queue2      

            if self.typing_func[q1] not in morph_t.keys() or not sort_leq(fs.sorts, morph_t[self.typing_func[q1]], fs.typing_func[q2]):
                return False

            gen1 = [(f, q) for (f, q) in self.trans_func.keys() if q == q1]
            gen2 = [(f, q) for (f, q) in fs.trans_func.keys() if q == q2]

            if len(gen1) == 0:
                visited1.append(q1)
            if len(gen2) == 0:
                visited2.append(q2)

            flag = False
            for (f1, q1) in gen1:
                for (f2, q2) in gen2:
                    if(
                        f1 in morph_f.keys() and
                        morph_f[f1] == f2 and 
                        sort_leq(fs.sorts, morph_t[self.typing_func[self.trans_func[(f1, q1)]]], fs.typing_func[fs.trans_func[(f2, q2)]]) and
                        not (self.trans_func[(f1, q1)] == q1 and fs.trans_func[(f2, q2)] != q2)                  
                    ):
                        flag = True
                        if self.trans_func[(f1, q1)] not in visited1 and fs.trans_func[(f2, q2)] not in visited2:
                            queue1.append(self.trans_func[(f1, q1)])
                            visited1.append(q1)
                            queue2.append(fs.trans_func[(f2, q2)])
                            visited2.append(q2)
                        break
                if flag and not (len(set(queue1)) != len(queue1) and len(set(queue2)) == len(queue2)):
                    flag = False
                else:
                    return False

        return set(visited2) == set(fs.nodes)

    def antiunify(self, fs, f):
        """ Computes the antiunifier as the pair of common nodes """
        if not isinstance(fs, FeatureStructure):
            raise Exception("Object not a feature structure.")
        morph_f, morph_t  = f

        root = (self.root, fs.root)
        nodes = [root]
        typing_func, trans_func = {}, {}
        typing_func[root] = find_most_common_sort(self.sorts, morph_t[self.typing_func[self.root]], fs.typing_func[fs.root])

        flag = False
        for q0 in nodes:
            gen1 = [(f, q) for (f, q) in self.trans_func.keys() if q == q0[0]]
            gen2 = [(f, q) for (f, q) in fs.trans_func.keys() if q == q0[1]]

            for (f1, q1) in gen1:
                for (f2, q2) in gen2:
                    if morph_f[f1] == f2:
                        node = (self.trans_func[(f1, q1)], fs.trans_func[(f2, q2)])
                        if node not in nodes:
                            nodes.append(node)
                        else: 
                            flag = True
                        typing_func[node] = find_most_common_sort(self.sorts, morph_t[self.typing_func[self.trans_func[(f1, q1)]]], fs.typing_func[fs.trans_func[(f2, q2)]])
                        trans_func[(f1, q0)] = node
                        break
                if flag:
                    break

        return FeatureStructure(self.sorts, self.feat, nodes, root, typing_func, trans_func)

    def disjoint_unify(self, fs1, fs2, f1, f2):
        """ Computes the disjoint union of fs1 and fs2 with objects identified by self """
        if (not isinstance(fs1, FeatureStructure)) or (not isinstance(fs2, FeatureStructure)):
            raise Exception("Object not a feature structure.")

        morph_f1, morph_t1 = f1
        morph_f2, morph_t2 = f2

        out_morph_f1, out_morph_t1, out_morph_h1 = {}, {}, {}
        out_morph_f2, out_morph_t2, out_morph_h2 = {}, {}, {}

        root = (self.root, fs1.root, fs2.root)
        nodes = [root]
        typing_func, trans_func = {}, {}
        typing_func[root] = self.typing_func[self.root]
        feat = []
        sorts = copy.copy(self.sorts)

        flag = False
        for q00 in nodes:
            gen1 = [(f, q) for (f, q) in fs1.trans_func.keys() if q == q00[1]]
            gen2 = [(f, q) for (f, q) in fs2.trans_func.keys() if q == q00[2]]

            if q00[0] is not None:
                gen0 = [(f, q) for (f, q) in self.trans_func.keys() if q == q00[0]]

                for (f0, q0) in gen0:
                    for (f1, q1) in gen1:
                        for (f2, q2) in gen2:
                            node = (self.trans_func[(f0, q0)], fs1.trans_func[(f1, q1)], fs2.trans_func[(f2, q2)])
                            if (morph_f1[f0] == f1 and morph_f2[f0] == f2) and (morph_t1[self.typing_func[node[0]]] == fs1.typing_func[node[1]] and morph_t2[self.typing_func[node[0]]] == fs2.typing_func[node[2]]):
                                if node not in nodes:
                                    nodes.append(node)
                                else: 
                                    flag = True
                                typing_func[node] = self.typing_func[node[0]]
                                trans_func[(f0, q00)] = node
                                feat.append(f0)

                                out_morph_h1[q1] = node
                                out_morph_f1[f1] = f0
                                out_morph_t1[fs1.typing_func[q1]] = typing_func[node]
                                out_morph_h2[q2] = node
                                out_morph_f2[f2] = f0
                                out_morph_t2[fs2.typing_func[q2]] = typing_func[node]

                                break
                        if flag:
                            break

            for (f1, q1) in gen1:  
                if not any([fs1.trans_func[(f1, q1)] == q[1] == q[2] for q in nodes]):
                    node = (None, fs1.trans_func[(f1, q1)], None)
                    typing_func[node] = f"_1_{fs1.typing_func[node[1]]}"
                    sorts[f"_1_{fs1.typing_func[node[1]]}"] = sorts[fs1.typing_func[node[1]]]
                    trans_func[(f"_1_{f1}", q00)] = node
                    feat.append(f"_1_{f1}")
                    nodes.append(node)

                    out_morph_h1[q1] = node
                    out_morph_f1[f1] = f"_1_{f1}"
                    out_morph_t1[fs1.typing_func[q1]] = f"_1_{fs1.typing_func[node[1]]}"
            for (f2, q2) in gen2:  
                if not any([fs2.trans_func[(f2, q2)] == q[1] == q[2] for q in nodes]):
                    node = (None, None, fs2.trans_func[(f2, q2)])
                    typing_func[node] = f"_2_{fs2.typing_func[node[2]]}"
                    sorts[f"_2_{fs2.typing_func[node[2]]}"] = sorts[fs2.typing_func[node[2]]]
                    trans_func[(f"_2_{f2}", q00)] = node
                    feat.append(f"_2_{f2}")
                    nodes.append(node)

                    out_morph_h2[q2] = node
                    out_morph_f2[f2] = f"_2_{f2}"
                    out_morph_t2[fs2.typing_func[q2]] = f"_2_{fs2.typing_func[node[2]]}"
        
        f1 = (out_morph_f1, out_morph_t1, out_morph_h1)
        f2 = (out_morph_f2, out_morph_t2, out_morph_h2)
        return (f1, FeatureStructure(sorts, feat, nodes, root, typing_func, trans_func), f2)

    def sort_generalisation_operator(self):
        """ Generates all possible type generalised feature structures from self """
        res = []
        for q in self.nodes:
            if self.typing_func[q] in self.sorts and self.typing_func[q] != "_":
                fs = copy.deepcopy(self)
                fs.typing_func[q] = self.sorts[self.typing_func[q]]
                res.append(fs)

        return res
    
    def node_elimination_operator(self):
        """ Generates alll possible generalisations via variable elimination from self """

        res = []
        for q in self.nodes:
            if self.typing_func[q] == "_" and q not in [t[1] for t in self.trans_func.keys()]:
                fs = copy.deepcopy(self)
                fs.nodes.remove(q)

                del fs.typing_func[q]

                for k in list(fs.trans_func.keys()):
                    if fs.trans_func[k] == q:
                        del fs.trans_func[k]

                res.append(fs)

        return res

    def node_equality_elimination_operator(self, looping = True):
        """
        Generates alll possible generalisations by breaking variable equality, the looping argument can 
        control if returning arrows should be kept or not, which can b ealmost thought of as a separate operator.
        """
        res = []
        qt = [q for q in self.nodes if list(self.trans_func.values()).count(q) > 1]
        if list(self.trans_func.values()).count(self.root):
            qt.append(self.root)

        for q in qt:
            gt = [k for k in self.trans_func.keys() if self.trans_func[k] == q]
            for gti in powerset(gt):
                if not gti or (gti == gt and len(gti) > 1):
                    continue

                fs = copy.deepcopy(self)
                node = (" ".join([i[1] for i in gti]), q)
                fs.nodes.append(node)
                fs.typing_func[node] = self.typing_func[q]

                for k in gti:
                    fs.trans_func[k] = node
                
                if looping:
                    for k in [k for k in self.trans_func.keys() if k[1] == q]:
                        fs.trans_func[(k[0], node)] = self.trans_func[k]

                res.append(fs)
        return res
