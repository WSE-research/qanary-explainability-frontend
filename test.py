from rdflib import Graph

string = """@prefix explanations: <urn:qanary:explanations#> .@prefix rdfs:         <http://www.w3.org/2000/01/rdf-schema#> .<urn:qanary:QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia>        explanations:hasExplanationForCreatedData                "The component urn:qanary:QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia has added 0 annotation(s) to the graph: "@en , "Die Komponente urn:qanary:QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia hat 0 Annotation(en) zum Graph hinzugefügt: "@de ."""

g = Graph()
g.parse(data=string)
