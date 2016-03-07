#!/usr/bin/env python
# coding: utf-8

import copy

import config
import dtutil
import log_db
import evfilter


#class EventDefinition(object):
#
#
#class VirtualEventDefinition(EventDefinition):
#
#
#
#class EventDefinitionMap():
#
#    def __init__(self, evdef_style):
#        """
#        Args:
#            evdef (str): one of [ltgid-host, ltid-host].
#
#        """
#        self.evdef_style = evdef_style
#        self.emap = {} # key : eid, val : eventdef
#
#
##TODO
#
class LogEventIDMap():

    def __init__(self):
        #self.eidlen = 0
        self.emap = {} # key : eid, val : info
        self.ermap = {} # key : info, val : eid

    def __len__(self):
        #return self.eidlen
        return len(self.emap)

    def _info(self, line):
        return (line.lt.ltgid, line.host)

    def _next_eid(self):
        eid = len(self.emap)
        while self.emap.has_key(eid):
            eid += 1
        else:
            return eid

    def eid(self, line):
        info = self._info(line)
        if self.ermap.has_key(info):
            return self.ermap[info]
        else:
            eid = self._next_eid()
            #eid = self.eidlen
            #self.eidlen += 1
            self.emap[eid] = info
            self.ermap[info] = eid
            return eid

    def has_eid(self, eid):
        return self.emap.has_key(eid)

    def info(self, eid):
        return self.emap[eid]

    def get_eid(self, info):
        return self.ermap[info]

    def pop(self, eid):
        info = self.emap.pop(eid)
        self.ermap.pop(info)
        #self.eidlen -= 1
        return info

    def move_eid(self, old_eid, new_eid):
        info = self.pop(old_eid)
        self.emap[new_eid] = info
        self.ermap[info] = new_eid

    def rearrange(self, l_eid):
        #assert len(l_eid) == self.eidlen
        emap = copy.deepcopy(self.emap)
        ermap = copy.deepcopy(self.ermap)
        self.emap = {}
        self.ermap = {}
        for new_eid, old_eid in enumerate(l_eid):
            old_info = emap[old_eid]
            self.emap[new_eid] = old_info 
            self.ermap[old_info] = new_eid


def _copy_evmap(evmap):
    new_evmap = LogEventIDMap()
    new_evmap.emap = copy.deepcopy(evmap.emap)
    new_evmap.ermap = copy.deepcopy(evmap.ermap)
    return new_evmap


def log2event(conf, top_dt, end_dt, area):
    ld = log_db.LogData(conf)
    evmap = LogEventIDMap()
    edict = {} # key : eid, val : list(datetime.datetime)

    if area == "all":
        iterobj = ld.iter_lines(top_dt = top_dt, end_dt = end_dt)
    elif area[:5] == "host_":
        host = area[5:]
        iterobj = ld.iter_lines(top_dt = top_dt, end_dt = end_dt, host = host)
    else:
        iterobj = ld.iter_lines(top_dt = top_dt, end_dt = end_dt, area = area)

    for line in iterobj:
        eid = evmap.eid(line)
        edict.setdefault(eid, []).append(line.dt)

    return edict, evmap


def filter_edict(conf, edict, evmap):
    l_result = evfilter.periodic_events(conf, edict, evmap)

    temp_edict = edict.copy()
    temp_evmap = _copy_evmap(evmap)
    for eid, interval in l_result:
        temp_edict.pop(eid)
        temp_evmap.pop(eid)
    return _remap_eid(temp_edict, temp_evmap)


#def replace_edict(conf, edict, evmap):
#    l_filter = conf.gettuple("dag", "use_filter")
#    if len(l_filter) == 0:
#        return edict, evmap
#    l_result = evfilter.periodic_events(conf, edict, evmap, l_filter)
#
#    err = conf.get("filter", "seq_error")
#    dup = conf.get("filter", "seq_duplication") 
#
#    temp_edict = edict.copy()
#    temp_evmap = _copy_evmap(evmap)
#    for eid, interval in l_result:
#        l_dt = edict[eid]
#        if dup:
#            l_pe, npe = separate_periodic_dup(l_dt, interval, err)
#        else:
#            l_pe, npe = separate_periodic(l_dt, interval, err)
#        
#
#    #TODO

def _remap_eid(edict, evmap):
    new_eid = 0
    for old_eid in edict.keys():
        if old_eid == new_eid:
            new_eid += 1
        else:
            temp = edict[old_eid]
            edict.pop(old_eid)
            edict[new_eid] = temp
            evmap.move_eid(old_eid, new_eid)
            new_eid += 1

    return edict, evmap


def event2stat(edict, top_dt, end_dt, dur):
    d_stat = {}
    l_label = dtutil.label(top_dt, end_dt, dur)

    for eid, l_ev in edict.iteritems():
        d_stat[eid] = dtutil.discretize(l_ev, l_label, binarize = True)
    return d_stat


