from rdflib import Graph, term

from config_translator import ConfigTranslator
from dateutil import parser
import pytz
from common.tzinfos import whois_timezone_info
from datetime import timezone
from conversor.predicates import PredicateError, Predicates
from transformer import transformer, type_transformer, retype


class BNodeFoundException(TypeError):
    def __init__(self, error_msg):
        super(TypeError, self).__init__(error_msg)


class SubjectError(TypeError):
    def __init__(self, error_msg):
        super(TypeError, self).__init__(error_msg)


class Subject:
    """
    Class which takes a Subject from a Graph and builds the Entity structure
    """
    def __init__(self, graph: Graph, subject):
        """

        :param graph: Graph to be analyzed
        :param subject:  Subject in the graph
        """
        self.graph = graph
        self.predicates = {}
        self.bnode = None
        self.bnod_predicate = None
        self.is_bnode = False
        self.subject_object = subject
        self.subject = str(subject)
        self.short_name = transformer(self.subject)
        self.uri = str(subject)
        if isinstance(subject, term.URIRef):
            try:
                self.prefix, self.url, self.thing = graph.compute_qname(
                    subject)
                self.s_type = type_transformer(self.url)
            except ValueError:
                # This is likely to be an onthology
                self.url = str(subject)
                self.prefix = ""
                self.thing = ""
                self.s_type = self.url
        elif isinstance(subject, term.BNode):
            self.prefix = "_"
            self.url = "_"
            self.thing = str(subject)
            self.is_bnode = True
        else:
            raise SubjectError("Subject must be an URI")

    def stodate(self, value):
        """
            Converts a date in string format to UTC date using
        """
        dt = parser.parse(value, tzinfos=whois_timezone_info)
        dt = dt.astimezone(pytz.UTC)
        return dt.replace(tzinfo=timezone.utc).isoformat()

    def push_data(self, pred, obj):
        """
        Given a predicate and an object in a triple with this object as subject, it will add the information read from
        the predicate and the object of the RDF triple to this object.

        :param pred: Predicate found in analysis
        :param obj:  Object related to the predicate
        :return:
        """
        if not isinstance(pred, term.URIRef):
            raise PredicateError("Predicate must be URIRef")
        if isinstance(obj, term.URIRef):
            pass
        elif isinstance(obj, term.BNode):
            raise BNodeFoundException(str(obj))
        p_id = str(pred)
        if p_id not in self.predicates:
            pr = Predicates(self.graph, pred)
            if pr.thing == 'rdf:type' or pr.thing == 'a':
                try:
                    self.s_type = retype(str(obj), 'a', self.s_type)
                except:
                    pass
                return
            else:
                self.predicates[p_id] = pr
        self.predicates[p_id].add_value(obj)

    def push_bnode(self, pred, bnode):
        """
        When the bnode is completed (some kind of structure as the value of this Subject), this will be appended to
        as an attribute.

        :param pred:
        :param bnode:
        :return:
        """
        self.bnode = bnode
        self.bnod_predicate = Predicates(self.graph, pred)

    def __iter__(self):
        """
        Iterator yielding, for every predicate related to this Subject the data related to it as Entity or Relationship.
        It will be basically used by the SubjectAnalysis class

        :return:
        """
        for _, v in self.predicates.items():
            yield v.thing, v.value, v.isreference

        if self.bnode is not None:
            r = {}
            is_reference = None
            for k, v, is_reference in self.bnode:
                r[k] = v
            yield self.bnod_predicate.thing, r, is_reference

        # if self.bnode is not None:
        #    for k, v in self.bnode:
        #        print(k)
        #        print(v)

    def __str__(self):
        """
        String representation of the subject

        :return: a representation of the object as a string
        """
        return f"{self.prefix} | {self.thing} | {self.url}"
