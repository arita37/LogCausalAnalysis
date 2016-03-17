#!/usr/bin/env python
# coding: utf-8

import sys
import time
import datetime
import threading
import cPickle as pickle
import logging

import config
import fslib
import log_db
import log2event
import pc_input 
import evfilter
import pcresult

_logger = logging.getLogger(__name__.rpartition(".")[-1])


def pc_log(conf, top_dt, end_dt, dur, area):
    
    _logger.info("job start ({0} - {1} in {2})".format(top_dt, end_dt, area))

    tempfn = thread_name(conf, top_dt, end_dt, dur, area) + ".temp"
    edict, evmap = log2event.log2event(conf, top_dt, end_dt, area)

    usefilter = conf.getboolean("dag", "usefilter")
    if usefilter:
        act = conf.get("filter", "action")
        if act == "remove":
            edict, evmap = log2event.filter_edict(conf, edict, evmap)
        elif act == "replace":
            edict, evmap = log2event.replace_edict(conf, edict, evmap,
                    top_dt, end_dt)
        else:
            raise NotImplementedError

    _logger.info("{0} events found in given term of log data".format(
            len(edict)))
    with open(tempfn, 'w') as f:
        pickle.dump((edict, evmap), f)

    if len(edict) > 2:
        threshold = conf.getfloat("dag", "threshold")
        data = log2event.event2stat(edict, top_dt, end_dt, dur)
        graph = pc_input.pc(data, threshold)
    else:
        _logger.info("insufficient events({0}), return empty dag".format(\
                len(edict)))
        graph = pc_input.empty_dag()

    output = pcresult.PCOutput(conf)
    output.make(graph, evmap, top_dt, end_dt, dur, area)
    output.dump()

    fslib.rm(tempfn)
    _logger.info("job done, output {0}".format(output.filename))
    return output


def thread_name(conf, top_dt, end_dt, dur, area):
    dirname = conf.get("dag", "output_dir")
    l_header = []
    l_header.append(dirname)
    l_header.append("/")
    l_header.append(area)
    l_header.append("_")
    if conf.getdur("dag", "unit_diff") == datetime.timedelta(days = 1):
        l_header.append(top_dt.strftime("%Y%m%d"))
    else:
        l_header.append(top_dt.strftime("%Y%m%d_%H%M%S"))
    return "".join(l_header)


def pc_all_args(conf):
    ld = log_db.LogData(conf)
    
    w_term = conf.getterm("dag", "whole_term")
    if w_term is None:
        w_top_dt, w_end_dt = ld.whole_term()
    else:
        w_top_dt, w_end_dt = w_term
    evfilter.init_evfilter(conf)
    term = conf.getdur("dag", "unit_term")
    diff = conf.getdur("dag", "unit_diff")
    dur = conf.getdur("dag", "stat_bin")

    l_args = []
    top_dt = w_top_dt
    while top_dt < w_end_dt:
        end_dt = top_dt + term
        l_area = conf.getlist("dag", "area")
        if "each" in l_area:
            l_area.pop(l_area.index("each"))
            l_area += ["host_" + host for host
                    in ld.whole_host(top_dt, end_dt)]
        for area in l_area:
            l_args.append((conf, top_dt, end_dt, dur, area))
        top_dt = top_dt + diff
    return l_args

    #l_args = []
    #l_area = conf.getlist("dag", "area")
    #if "each" in l_area:
    #    l_area.pop(l_area.index("each"))
    #    l_area += ["host_" + host for host
    #            in ld.whole_host(top_dt, end_dt)]
    #for area in l_area:
    #    top_dt = w_top_dt
    #    while top_dt < w_end_dt:
    #        end_dt = top_dt + term
    #    l_args.append((conf, top_dt, end_dt, dur, area))
    #    top_dt = top_dt + diff
    #return l_args

def pc_sthread(l_args):

    start_dt = datetime.datetime.now()
    _logger.info("pc_log task start ({0} jobs)".format(len(l_args)))

    for args in l_args:
        pc_log(*args)

    end_dt = datetime.datetime.now()
    _logger.info("pc_log task done ({0})".format(end_dt - start_dt))


def pc_mthread(l_args, pal=1):

    start_dt = datetime.datetime.now()
    _logger.info("pc_log task start ({0} jobs)".format(len(l_args)))

    l_thread = [threading.Thread(name = thread_name(*args),
        target = pc_log, args = args) for args in l_args]

    l_job = []
    while len(l_thread) > 0:
        if len(l_job) < pal:
            job = l_thread.pop(0)
            job.start()
            l_job.append(job)
        else:
            time.sleep(1)
            l_job = [j for j in l_job if j.is_alive()]
    else:
        for job in l_job:
            job.join()

    end_dt = datetime.datetime.now()
    _logger.info("pc_log task done ({0})".format(end_dt - start_dt))


def test_pc(l_args):
    pc_log(*(l_args[0]))


if __name__ == "__main__":
    
    usage = "usage: {0} [options]".format(sys.argv[0])
    import optparse
    op = optparse.OptionParser(usage)
    op.add_option("-c", "--config", action="store",
            dest="conf", type="string", default=config.DEFAULT_CONFIG_NAME,
            help="configuration file path")
    op.add_option("-p", "--parallel", action="store", dest="pal", type="int",
            default=1, help="multithreading")
    op.add_option("-r", action="store_true", dest="rflag",
            default=False, help="using pcalg library in R")
    op.add_option("--test", action="store_true", dest="test",
            default=False, help="test pc_log; do with first term")
    (options, args) = op.parse_args()

    conf = config.open_config(options.conf)
    config.set_common_logging(conf, _logger, ["evfilter"])

    fslib.mkdir(conf.get("dag", "output_dir"))
    l_args = pc_all_args(conf)
    if options.test:
        test_pc(l_args); sys.exit()

    if options.pal == 1:
        pc_sthread(l_args)
    else:
        pc_mthread(l_args, options.pal)


