def list_flattenner(nested_list):
    res = []
    for i in nested_list:
        if not isinstance(i, (list,)):
            res.append(i)
        else:
            res += list_flattenner(i)
    return res
