from abc import abstractmethod


class HierarchicalFilter:
    @classmethod
    def _query_string(cls, require, exclude) -> str:
        """Generates string in proper syntax for Elasticsearch query_string attribute, given API parameters"""
        positive_codes, negative_codes = cls._order_raw_codes(require, exclude, require + exclude)

        positive_nodes = [
            cls.node(code, True, positive_codes["sub"], negative_codes["sub"]) for code in positive_codes["top"]
        ]
        negative_nodes = [
            cls.node(code, False, positive_codes["sub"], negative_codes["sub"]) for code in negative_codes["top"]
        ]

        positive_query = " OR ".join([node.get_query() for node in positive_nodes])
        negative_query = " AND ".join([node.get_query() for node in negative_nodes])

        if positive_query and negative_query:
            return f"{positive_query} AND {negative_query}"
        else:
            return positive_query + negative_query  # We know that exactly one is blank thanks to TinyShield

    @staticmethod
    def _order_raw_codes(requires, exclude, all_codes):
        """Seperates codes into 'top' codes (those with no higher node in either array), and 'sub' codes (those that do)."""
        postive_codes = {
            "top": [code for code in requires if len([root for root in all_codes if code[:-1].startswith(root)]) == 0]
            # func to know if parent
        }
        negative_codes = {
            "top": [code for code in exclude if len([root for root in all_codes if code[:-1].startswith(root)]) == 0]
            # func to know if parent
        }
        postive_codes["sub"] = [code for code in requires if code not in postive_codes["top"] + negative_codes["top"]]
        negative_codes["sub"] = [code for code in exclude if code not in postive_codes["top"] + negative_codes["top"]]

        return postive_codes, negative_codes

    @staticmethod
    @abstractmethod
    def node(code, positive, positive_codes, negative_codes):
        pass


class Node:
    """Represents one part of the final query, either requiring or excluding one code, with any exceptions"""

    code: str
    positive: bool
    children: list

    def __init__(self, code, positive, positive_codes, negative_codes):
        self.code = code
        self.positive = positive
        self.populate_children(positive_codes, negative_codes)

    def populate_children(self, positive_codes, negative_codes):
        self.children = []
        self._pop_children_helper(positive_codes, True, positive_codes, negative_codes)
        self._pop_children_helper(negative_codes, False, positive_codes, negative_codes)

    def _pop_children_helper(self, codes, is_positive, positive_codes, negative_codes):
        for other_code in codes:
            if (
                len(other_code) == len(self.code) + 2 and other_code[: len(self.code)] == self.code
            ):  # func to know if parent
                self.children.append(self._self_replicate(other_code, is_positive, positive_codes, negative_codes))

    def get_query(self):
        retval = self._basic_search_unit()
        if not self.positive:
            retval = f"NOT {retval}"
        retval = f"({retval})"

        positive_child_query = " OR ".join([child.get_query() for child in self.children if child.positive])
        negative_child_query = " AND ".join([child.get_query() for child in self.children if not child.positive])
        joined_child_query = " AND ".join(query for query in [positive_child_query, negative_child_query] if query)

        if self.children:
            if self.positive:
                retval += f" AND ({joined_child_query})"
            else:
                retval += f" OR ({joined_child_query})"

        print(retval)
        return f"({retval})"

    @abstractmethod
    def _basic_search_unit(self):
        pass

    @abstractmethod
    def _self_replicate(self, code, positive, positive_codes, negative_codes):
        pass
