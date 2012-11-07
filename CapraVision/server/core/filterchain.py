#! /usr/bin/env python

#    Copyright (C) 2012  Club Capra - capra.etsmtl.ca
#
#    This file is part of CapraVision.
#    
#    CapraVision is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Contains the FilterChain class and helper functions to work with the filter chain."""

import CapraVision.server.filters

import ConfigParser
import inspect

def params_list(chain):
    flist = []
    for filter in chain.filters:
        fname = filter.__class__.__name__
        params = []
        for name, value in filter.__dict__.items():
            if name[0] == '_':
                continue
            params.append((name, value))
        flist.append((fname, params))
    return flist

def isnumeric(string):
    try:
        float(string)
        return True
    except ValueError:
        return False
    
def read(file_name):
    """Open a filter chain file and load its content in a new filter chain."""
    new_chain = FilterChain()
    cfg = ConfigParser.ConfigParser()
    cfg.read(file_name)
    for section in cfg.sections():
        filter = CapraVision.filters.create_filter(section) 
        for member in filter.__dict__:
            if member[0] == '_':
                continue
            val = cfg.get(section, member)
            if val == "True" or val == "False":
                filter.__dict__[member] = cfg.getboolean(section, member)
            elif isnumeric(val):
                filter.__dict__[member] = cfg.getfloat(section, member)
            else:
                if isinstance(val, str):
                    val = '\n'.join([line[1:-1] for line in str.splitlines(val)])
                filter.__dict__[member] = val
        if hasattr(filter, 'configure'):
            filter.configure()
        new_chain.add_filter(filter)
    return new_chain

def write(file_name, chain):
    """Save the content of the filter chain in a file."""
    cfg = ConfigParser.ConfigParser()
    for fname, params in params_list(chain):
        cfg.add_section(fname)
        for name, value in params:
            if isinstance(value, str):
                value = '\n'.join(['"%s"' % line for line in str.splitlines(value)])
            cfg.set(fname, name, value)
    cfg.write(open(file_name, 'w'))
    
class FilterChain:
    """ Observable.  Contains the chain of filters to execute on an image.
    
    The observer must be a method that receive a filter and an image as parameter.
    The observer method is called after each execution of a filter in the filter chain.
    """
    def __init__(self):
        self.filters = []
        self.image_observers = [] 
        self.filter_observers = []
    
    def add_filter(self, filter):
        self.filters.append(filter)
        self.notify_filter_observers()
        
    def remove_filter(self, filter):
        self.filters.remove(filter)
        self.notify_filter_observers()
        
    def move_filter_up(self, filter):
        i = self.filters.index(filter)
        if i > 0:
            self.filters[i], self.filters[i-1] = self.filters[i-1], filter
            self.notify_filter_observers()
        
    def move_filter_down(self, filter):
        i = self.filters.index(filter)
        if i < len(self.filters) - 1:
            self.filters[i], self.filters[i+1] = self.filters[i+1], filter
            self.notify_filter_observers()
    
    def add_image_observer(self, observer):
        self.image_observers.append(observer)
        
    def remove_image_observer(self, observer):
        self.image_observers.remove(observer)
        
    def add_filter_observer(self, observer):
        self.filter_observers.append(observer)
        
    def remove_filter_observer(self, observer):
        self.filter_observers.remove(observer)
        
    def notify_filter_observers(self):
        for observer in self.filter_observers:
            observer()
            
    def add_filter_output_observer(self, output):
        for f in self.filters:
            f.add_output_observer(output)
            
    def remove_filter_output_observer(self, output):
        for f in self.filters:
            f.remove_output_observer(output)
    
    def execute(self, image):
        for f in self.filters:
            image = f.execute(image.copy())
            for observer in self.image_observers:
                observer(f, image)
        return image