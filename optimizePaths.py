#!/usr/bin/env python
'''
Copyright (C) 2017 Romain Testuz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St Fifth Floor, Boston, MA 02139
'''
import inkex, simplepath, simplestyle
import sys
import math
import random
import colorsys
import os
#Trick to allow placing symbolic links in the inkscape extension folder
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#import networkx as nx

class Graph:
    def __init__(self):
        self.__adj = {}
        self.__data = {}

    def __str__(self):
        return str(self.__adj)

    def nodes(self):
        nodes = []
        for n in self.__adj:
            nodes.append(n)
        return nodes

    def edges(self):
        edges = []
        for n1 in self.__adj:
            for n2 in self.neighbours(n1):
                edges.append((n1, n2))
        return edges

    def node(self, n):
        if n in self.__adj:
            return self.__data[n]
        else:
            raise ValueError('Inexistant node')

    def neighbours(self, n):
        if n in self.__adj:
            return self.__adj[n]
        else:
            raise ValueError('Inexistant node')

    def degree(self, n):
        if n in self.__adj:
            return len(self.__adj[n])
        else:
            raise ValueError('Inexistant node')

    def addNode(self, n, data):
        if n not in self.__adj:
            self.__adj[n] = []
            self.__data[n] = data
        else:
            raise ValueError('Node already exists')

    def removeNode(self, n):
        if n in self.__adj:
            #Remove all edges pointing to node
            for n2 in self.__adj:
                neighbours = self.__adj[n2]
                if n in neighbours:
                    neighbours.remove(n)
            del self.__adj[n]
            del self.__data[n]
        else:
            raise ValueError('Removing inexistant node')

    def addEdge(self, n1, n2):
        if(n1 in self.__adj and n2 in self.__adj):
            self.__adj[n1].append(n2)
            self.__adj[n2].append(n1)
        else:
            raise ValueError('Adding edge to inexistant node')

    def removeEdge(self, n1, n2):
        if(n1 in self.__adj and n2 in self.__adj and
        n2 in self.__adj[n1] and n1 in self.__adj[n2]):
            self.__adj[n1].remove(n2)
            self.__adj[n2].remove(n1)
        else:
            raise ValueError('Removing inexistant edge')



class OptimizePaths(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("-t", "--tolerance",
            action="store", type="float",
            dest="tolerance", default=0.1,
            help="the distance below which 2 nodes will be merged")
        self.OptionParser.add_option("-l", "--enableLog",
                        action="store", type="inkbool",
                        dest="enableLog", default=False,
                        help="Enable logging")
        self.OptionParser.add_option("-s", "--splitSubPaths",
                        action="store", type="inkbool",
                        dest="splitSubPaths", default=False,
                        help="Split sub-paths")

    def parseSVG(self):
        vertices = []
        edges = []

        for id, node in self.selected.iteritems():
            if node.tag == inkex.addNS('path','svg'):
                d = node.get('d')
                path = simplepath.parsePath(d)
                #start = prev = None
                startVertex = previousVertex = None

                for command, coords in path:
                    tcoords = tuple(coords)
                    #self.log(command + " " + str(tcoords))
                    if command == 'M':
                        #start = prev = tcoords
                        vertices.append(tcoords)
                        startVertex = previousVertex = len(vertices)-1
                    elif command == 'L':
                        vertices.append(tcoords)
                        currentVertex = len(vertices)-1
                        edges.append((previousVertex, currentVertex))
                        previousVertex = currentVertex
                    elif command == 'Z':
                        edges.append((previousVertex, startVertex))
                        previousVertex = startVertex
                    elif (command == 'C' or command == 'S' or command == 'Q' or
                    command == 'T' or command == 'A'):
                        endCoords = (tcoords[-2], tcoords[-1])
                        vertices.append(endCoords)
                        currentVertex = len(vertices)-1
                        edges.append((previousVertex, currentVertex))
                        previousVertex = currentVertex

            #elif node.tag == inkex.addNS('polygon','svg'):

        #for v in vertices:
            #self.log("Vertex: " + str(v))
        #for e in edges:
            #self.log("Edge: " + str(e))

        return (vertices, edges)

    def buildGraph(self, vertices, edges):
        G = Graph()
        for i, v in enumerate(vertices):
            self.log("N "+ str(i) + " (" + str(v[0]) + "," + str(v[1]) + ")")
            G.addNode(i, (v[0], v[1]))
        self.log(G)
        for e in edges:
            self.log("E "+str(e[0]) + " " + str(e[1]))
            G.addEdge(e[0], e[1])
        return G

    @staticmethod
    def dist(a, b):
        return math.sqrt( (a[0] - b[0])**2 + (a[1] - b[1])**2 )

    def log(self, message):
        if(self.options.enableLog):
            inkex.debug(message)

    def mergeWithTolerance(self, G, tolerance):
        mergeTo = {}
        for ni in G.nodes():
            node_i_data = G.node(ni)
            for nj in G.nodes():
                if nj <= ni :
                    continue
                #self.log("Test " + str(ni) + " with " + str(nj))
                node_j_data = G.node(nj)
                dist_ij = self.dist(node_i_data, node_j_data)
                if (dist_ij < tolerance) and (nj not in mergeTo) and (ni not in mergeTo):
                    self.log("Merge " + str(nj) + " with " + str(ni) + " (dist="+str(dist_ij)+")")
                    mergeTo[nj] = ni

        for n in mergeTo:
            newEdges = []
            for neigh_n in G.neighbours(n):
                newEdge = None
                if neigh_n in mergeTo:
                    newEdge = (mergeTo[n], mergeTo[neigh_n])
                else:
                    newEdge = (mergeTo[n], neigh_n)

                if newEdge[0] is not newEdge[1]:
                    newEdges.append(newEdge)

            for e in newEdges:
                G.addEdge(e[0], e[1])
                self.log("Added edge: "+str(e[0]) + " " + str(e[1]))
            G.removeNode(n)
            self.log("Removed node: " + str(n))

    @staticmethod
    def rgbToHex(rgb):
        return '#%02x%02x%02x' % rgb

    #Color should be in hex format ("#RRGGBB"), if not specified a random color will be generated
    def addPathToInkscape(self, path, parent, color=None):
        if(color is None):
            color = colorsys.hsv_to_rgb(random.uniform(0.0, 1.0), 1.0, 1.0)
            color = tuple(x * 255 for x in color)
            color = self.rgbToHex( color )

        style = "stroke:"+color+";stroke-width:2;fill:none;"
        attribs = {'style': style, 'd': simplepath.formatPath(path) }
        inkex.etree.SubElement(parent, inkex.addNS('path','svg'), attribs )

    def graphToSVG(self, G):
        parent = self.current_layer
        path = []
        dfsEdges = G.edges()


        if self.options.splitSubPaths:
            group = inkex.etree.SubElement(parent, inkex.addNS('g','svg'))
            for i,e in enumerate(dfsEdges):
                node_i_data = G.node(e[0])
                node_j_data = G.node(e[1])

                #Path ends either at the last edge or when the next edge starts somewhere else
                endPath = (i == len(dfsEdges)-1 or e[1] != dfsEdges[i+1][0])

                if(not path):
                    path.append(['M', (node_i_data[0], node_i_data[1])])
                    path.append(['L', (node_j_data[0], node_j_data[1])])

                else:
                    path.append(['L', (node_j_data[0], node_j_data[1])])

                if endPath:
                    self.addPathToInkscape(path, group)
                    path = []

        else:
            prevEdge = None

            for e in nx.edge_dfs(G):
                node_i_data = G.node[e[0]]
                node_j_data = G.node[e[1]]

                if (prevEdge == None or prevEdge[1] != e[0]):
                    path.append(['M', (node_i_data[0], node_i_data[1])])
                    path.append(['L', (node_j_data[0], node_j_data[1])])
                else:
                    path.append(['L', (node_j_data[0], node_j_data[1])])

                prevEdge = e

            self.addPathToInkscape(path, parent, "#FF0000")


    def effect(self):
        (vertices, edges) = self.parseSVG()
        G = self.buildGraph(vertices, edges)
        self.log("Number of edges: "+str(len(edges)))

        self.mergeWithTolerance(G, self.options.tolerance)
        #self.log("Number of edges after cleaning: "+str(G.number_of_edges()))

        for e in G.edges():
            self.log("E "+str(e[0]) + " " + str(e[1]))
        for n in G.nodes():
            self.log("Degree of "+str(n) + ": " + str(G.degree(n)))

        self.graphToSVG(G)

e = OptimizePaths()
e.affect()