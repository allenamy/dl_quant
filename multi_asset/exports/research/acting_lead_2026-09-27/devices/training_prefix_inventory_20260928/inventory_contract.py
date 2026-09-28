import math

def exact_axis(left,right):
    if len(left)!=len(right) or any(a!=b for a,b in zip(left,right)):
        raise ValueError('ordered axis differs; no intersection permitted')

def window_contract(axis,first,last,label_limit,origin):
    if first<0 or last>=len(axis) or first>last:raise ValueError('window bounds')
    a=list(axis)
    if any(not math.isfinite(float(x)) or float(x)!=int(x) or int(x)%14400 for x in a):raise ValueError('integer 4h axis required')
    if any(int(y)-int(x)!=14400 for x,y in zip(a,a[1:])):raise ValueError('continuous axis required')
    end=int(a[last])+14400
    if end>label_limit:raise ValueError('label end exceeds frozen training limit')
    return {'first_anchor':int(a[first]),'last_anchor':int(a[last]),'label_end':end,
            'prefix_status':'UNSUPPORTED_COMMON_ORIGIN' if a[first]<origin else 'NOT_BUILT',
            'has_measured_inventory':False,'origin':origin}
