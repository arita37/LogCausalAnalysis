#!/usr/bin/env python
# coding: utf-8


def table(data, label = None, spl = "\t", fill = " "):
    # data : [row = [str, str, ...], row1, ...]

    l_row = data
    if label is not None:
        l_row = [label] + data
    l_length = [max([len(elem) for elem in column]) for column in zip(*data)]

    l_buf = []
    if label is not None:
        l_buf.append(spl.join([elem.rjust(length)
                for elem, length in zip(label, l_length)]))
    for row in data:
        temp_buf = []
        for elem, length in zip(row, l_length):
            temp_buf.append(elem.rjust(length))
        l_buf.append(spl.join(temp_buf))

    return "\n".join(l_buf)
