'''
Created on Oct 21, 2011

@author: caioviel
'''

import numpy
import threading
import time

from commum.Model import *
from InternalInterface import InternalInterface
from BriteParser import BriteParser


class TopologyManager(threading.Thread):
    '''
    classdocs
    '''

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.all_hosts = []
        self.links = []
        self.routers = []
        self.multicast_group = []
        self.active_hosts = []
        self.inactive_hosts = []
        self.multicast_source = -1
        self.eventListener = None
        self.is_running = False
        self.event_id = 0
        
    def getNextEventId(self):
        self.event_id += 1 
        return self.event_id
        
    def importTopologyFromBrite(self, britefile):
        parser = BriteParser(britefile)
        parser.doParse()
        self.all_hosts = parser.hosts
        self.links = parser.links
        self.routers = parser.routers
        
        self.__selectMulticastGroup__()
        
        self.multicast_source = self.selectRandomHost(self.multicast_group)
        
        self.__selectActiveHosts__()
        
        self.__calcLinksWeight__()
        
        
    def selectRandomHost(self, hosts):
        host_index = int(numpy.random.uniform(0.0, len(hosts)-1))
        return hosts[host_index]
    
    def __selectMulticastGroup__(self, min_number=20.0, max_number=40.0):
        multicast_hosts_number = int(numpy.random.uniform(min_number, max_number))
    
        self.multicast_group = []
        while len(self.multicast_group) < multicast_hosts_number:
            host = self.selectRandomHost(self.all_hosts)
            if host not in self.multicast_group:
                self.multicast_group.append(host)
    
    def __selectActiveHosts__(self):
        active_hosts_number = int(numpy.random.normal(len(self.multicast_group)/2, 3.0))
        
        self.active_hosts = []
        while len(self.active_hosts) < active_hosts_number:
            host = self.selectRandomHost(self.multicast_group)
            if host == self.multicast_source:
                continue
            elif host not in self.active_hosts:
                self.active_hosts.append(host)
        
        for host in self.multicast_group:
            if host == self.multicast_source:
                continue
            elif host not in self.active_hosts:
                self.inactive_hosts.append(host)
                
    def setEventsListener(self, eventListener):
        self.eventListener = eventListener
    
    def startEvents(self):
        if self.eventListener == None:
            raise Exception("Trying to start the event generation without setting the events listener.")
        else:
            self.is_running = True
            threading.Thread.start(self)
            
    def run(self):
        print 'Starting to generate events...'
        while self.is_running:
            #Dormir um tempo aleatorio seguindo uma distrubuicao normal de media 40 e variancia 15 (em segundos)
            sleepingTime = numpy.random.normal(40, 20)
            time.sleep(sleepingTime)
            
            #50% de chances de ser um evento de entrada / 50% de ser um evento de saida
            event = None
            value = numpy.random.random()
            if value >= 0.5: #Evento de entrada
                event = self.generateEntryEvent()
            else: #Evento de saida
                event = self.generateExitEvent()
            
            if len(event.hosts) > 0:
                print 'Event generated.'
                self.eventListener.notifyEvent(event)
            
    def generateEntryEvent(self):
        entering_hosts = []
        entering_hosts_number = numpy.random.poisson(2);
        while len(entering_hosts) < entering_hosts_number:
            host = self.selectRandomHost(self.inactive_hosts)
            if host not in entering_hosts:
                entering_hosts.append(host)
                
        for host in entering_hosts:
            self.active_hosts.append(host)
                
        event = Event(self.getNextEventId(), 'entry')
        event.hosts = entering_hosts
        return event
    
    def generateExitEvent(self):
        exiting_hosts = []
        exiting_hosts_number = numpy.random.poisson(1);
        while len(exiting_hosts) < exiting_hosts_number:
            host = self.selectRandomHost(self.active_hosts)
            if host not in exiting_hosts:
                exiting_hosts.append(host)
                
        for host in exiting_hosts:
            self.inactive_hosts.append(host)
                
        event = Event(self.getNextEventId(), 'exit')
        event.hosts = exiting_hosts
        return event
    
    def isHost(self, nodeid):
        if nodeid > 50:
            return True
        else:
            return False
        
    def getHostById(self, hostId):
        if self.isHost(hostId):
            return self.all_hosts[hostId-51]
        else:
            return None
        
    def getRouterById(self, routerId):
        if not self.isHost(routerId):
            return self.routers[routerId-1]
        else:
            print 'Will return None.'
            return None
        
    def getLinkById(self, linkid):
        return self.links[linkid-1]
    
    def updateHosts(self, hosts):
        for i in range(len(self.all_hosts)):
            self.all_hosts[i].ip = hosts[i].ip
            self.all_hosts[i].mac = hosts[i].mac
        
    
    def __calcLinksWeight__(self):
        visitedNodes = []
        nodesToVisit = []
        source = self.multicast_source
        link = self.getLinkById(source.link)
        source.distanceFromSource = 0
        link.weight = 1
        node = self.getRouterById(source.router)

        node.distanceFromSource = 1
        
        visitedNodes.append(source.id)
        nodesToVisit.append(node)
        
        while len(nodesToVisit) > 0:
            node = nodesToVisit.pop(0)
            if node.id in visitedNodes:
                #It's had already been calculed.
                continue
            
            visitedNodes.append(node.id)
            
            if self.isHost(node.id):
                #it's a host
                host = node
                link = self.getLinkById(host.link)
                if link.weight == -1: 
                    #The weight for this link hasn't been calculed
                    link.weight = node.distanceFromSource + 1
                elif link.weight > node.distanceFromSource + 1:
                    link.weight = node.distanceFromSource + 1
                
                router = self.getRouterById(host.router)
                if router.distanceFromSource == -1:
                    router.distanceFromSource = link.weight
                elif router.distanceFromSource > link.weight:
                    router.distanceFromSource = link.weight
                
                nodesToVisit.append(router)   
                
            else: 
                #It's a router
                thisrouter = node
                for i in range(len(thisrouter.allports)):
                    link = self.getLinkById( thisrouter.links[i] )
                    nodeid = thisrouter.allports[i]
                    
                    if link.weight == -1: 
                    #The weight for this link hasn't been calculed
                        link.weight = thisrouter.distanceFromSource + 1
                    elif link.weight > thisrouter.distanceFromSource + 1:
                        link.weight = thisrouter.distanceFromSource + 1
                    
                    _node = None
                    if self.isHost(nodeid):
                        _node = self.getHostById(nodeid)
                    else:
                        _node = self.getRouterById(nodeid)
                        
                    if _node.distanceFromSource == -1:
                        _node.distanceFromSource = link.weight
                    elif _node.distanceFromSource > link.weight:
                        _node.distanceFromSource = link.weight
                
                    nodesToVisit.append(_node)