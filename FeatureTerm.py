from amalgam import Category
import feature_term_gens as ftgens


class FeatureTerm(Category): 
    def __init__(self, sorts):
        self.sorts = sorts
        super().__init__()

    def generalization_step(self, fs):
        return ftgens.gen_step(fs, self.sorts)
      
    def pullback(self, fs, fs_gen):
        return self._antiunification(fs, fs_gen)
    
    def get_csp_gen(self, fs1, fs2):
        return self._antiunification(fs1, fs2)

    def amalgamate(self, fs1, fs2):
        return super().amalgamate(fs1, fs2)
    
    def _subsumes(self, fs1, fs2):
        to_gen = [fs1]
        while bool(to_gen):
            g, *to_gen = to_gen 
            sort_gens = ftgens.get_all_sort_generalizations(g, self.sorts)
            for g in sort_gens:
                if g.subsumes(fs2):
                    return True
                to_gen.append(g)
        return False

    def _antiunification(self, fs1, fs2):
        # There should be a simpler way for this
        # Get all value paths (+ some extra)
        fs1_paths = ftgens.find_all_leaves(fs1) + ftgens.find_all_structs(fs1)
        fs2_paths = ftgens.find_all_leaves(fs2) + ftgens.find_all_structs(fs2)

        # Get common paths
        fs_paths = []
        for p1 in fs1_paths:
            for p2 in fs2_paths:
                if (p1 == p2) and (len(p1) > 1):
                    fs_paths.append(p1)
        fs_paths = set(fs_paths)

        # Create the antiunificated feature structure from common paths
        fs = ftgens.FeatStruct()
        for p in fs_paths:
            fs[p[:-1]] = p[-1]
        return fs

if __name__ == "__main__":
    icon1 = ftgens.init_FeatStruct(root = "icon", leftside = ftgens.init_FeatStruct( root = "Silhouette", right = "Rightarrow"), rightside="Silhouette")
    icon2 = ftgens.init_FeatStruct(root = "icon", rightside = ftgens.init_FeatStruct( root = "Silhouette", left = "Leftarrow"), leftside="Silhouette")

    sorts = {
        "Rightarrow": "Arrow",
        "Leftarrow": "Arrow",
        "Arrow": "Symbol",
        "Silhouette": "asd",
        "asd": "Symbol"
    }

    fs1 =  ftgens.init_FeatStruct(root = "icon", rightside="Silhouette")
    fs2 =  ftgens.init_FeatStruct(root = "asd", rightside="Symbol", leftside="asdf")
    print(fs1.subsumes(fs2))

    
    ft = FeatureTerm(sorts)
    print(ft._subsumes(fs1, fs2))