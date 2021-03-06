"""
A collection of utilities for analyzing and plotting financial data.

"""

import numpy as np
import matplotlib.dates as mdates
import datetime

from matplotlib import colors as mcolors
from matplotlib.patches import Ellipse
from matplotlib.collections import LineCollection, PolyCollection, PatchCollection
from mplfinance._arg_validators import _process_kwargs, _validate_vkwargs_dict

from six.moves import zip

from mplfinance._styles import _get_mpfstyle

def _check_input(opens, closes, highs, lows, miss=-1):
    """Checks that *opens*, *highs*, *lows* and *closes* have the same length.
    NOTE: this code assumes if any value open, high, low, close is
    missing (*-1*) they all are missing

    Parameters
    ----------
    ax : `Axes`
        an Axes instance to plot to
    opens : sequence
        sequence of opening values
    highs : sequence
        sequence of high values
    lows : sequence
        sequence of low values
    closes : sequence
        sequence of closing values
    miss : int
        identifier of the missing data

    Raises
    ------
    ValueError
        if the input sequences don't have the same length
    """

    def _missing(sequence, miss=-1):
        """Returns the index in *sequence* of the missing data, identified by
        *miss*

        Parameters
        ----------
        sequence :
            sequence to evaluate
        miss :
            identifier of the missing data

        Returns
        -------
        where_miss: numpy.ndarray
            indices of the missing data
        """
        return np.where(np.array(sequence) == miss)[0]

    same_length = len(opens) == len(highs) == len(lows) == len(closes)
    _missopens = _missing(opens)
    same_missing = ((_missopens == _missing(highs)).all() and
                    (_missopens == _missing(lows)).all() and
                    (_missopens == _missing(closes)).all())

    if not (same_length and same_missing):
        msg = ("*opens*, *highs*, *lows* and *closes* must have the same"
               " length. NOTE: this code assumes if any value open, high,"
               " low, close is missing (*-1*) they all must be missing.")
        raise ValueError(msg)

def roundTime(dt=None, roundTo=60):
   """Round a datetime object to any time lapse in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
   if dt is None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

def _calculate_atr(atr_length, highs, lows, closes):
    """Calculate the average true range
    atr_length : time period to calculate over
    all_highs : list of highs
    all_lows : list of lows
    all_closes : list of closes
    """
    if atr_length < 1:
        raise ValueError("Specified atr_length may not be less than 1")
    elif atr_length >= len(closes):
        raise ValueError("Specified atr_length is larger than the length of the dataset: " + str(len(closes)))
    atr = 0
    for i in range(len(highs)-atr_length, len(highs)):
        high = highs[i]
        low = lows[i]
        close_prev = closes[i-1]
        tr = max(abs(high-low), abs(high-close_prev), abs(low-close_prev))
        atr += tr
    return atr/atr_length

def combine_adjacent(arr):
    """Sum like signed adjacent elements
    arr : starting array

    Returns
    -------
    output: new summed array
    indexes: indexes indicating the first 
             element summed for each group in arr
    """
    output, indexes = [], []
    curr_i = 0
    while len(arr) > 0:
        curr_sign = arr[0]/abs(arr[0])
        index = 0
        while index < len(arr) and arr[index]/abs(arr[index]) == curr_sign:
            index += 1
        output.append(sum(arr[:index]))
        indexes.append(curr_i)
        curr_i += index
        
        for _ in range(index):
            arr.pop(0)
    return output, indexes

def coalesce_volume_dates(in_volumes, in_dates, indexes):
    """Sums volumes between the indexes and ouputs
    dates at the indexes
    in_volumes : original volume list
    in_dates : original dates list
    indexes : list of indexes

    Returns
    -------
    volumes: new volume array
    dates: new dates array
    """
    volumes, dates = [], []
    for i in range(len(indexes)):
        dates.append(in_dates[indexes[i]])
        to_sum_to = indexes[i+1] if i+1 < len(indexes) else len(in_volumes)
        volumes.append(sum(in_volumes[indexes[i]:to_sum_to]))
    return volumes, dates


def _updown_colors(upcolor,downcolor,opens,closes,use_prev_close=False):
    if upcolor == downcolor:
        return upcolor
    cmap = {True : upcolor, False : downcolor}
    if not use_prev_close:
        return [ cmap[opn < cls] for opn,cls in zip(opens,closes) ]
    else:
        first = cmap[opens[0] < closes[0]] 
        _list = [ cmap[pre < cls] for cls,pre in zip(closes[1:], closes) ]
        return [first] + _list

def _valid_renko_kwargs():
    '''
    Construct and return the "valid renko kwargs table" for the mplfinance.plot(type='renko') 
    function. A valid kwargs table is a `dict` of `dict`s. The keys of the outer dict are 
    the valid key-words for the function.  The value for each key is a dict containing 2 
    specific keys: "Default", and "Validator" with the following values:
        "Default"      - The default value for the kwarg if none is specified.
        "Validator"    - A function that takes the caller specified value for the kwarg,
                         and validates that it is the correct type, and (for kwargs with 
                         a limited set of allowed values) may also validate that the
                         kwarg value is one of the allowed values.
    '''
    vkwargs = {
        'brick_size'  : { 'Default'     : 'atr',
                          'Validator'   : lambda value: isinstance(value,(float,int)) or value == 'atr' },
        'atr_length'  : { 'Default'     : 14,
                          'Validator'   : lambda value: isinstance(value,int) or value == 'total' },               
    }

    _validate_vkwargs_dict(vkwargs)

    return vkwargs

def _valid_pointnfig_kwargs():
    '''
    Construct and return the "valid pointnfig kwargs table" for the mplfinance.plot(type='pnf') 
    function. A valid kwargs table is a `dict` of `dict`s. The keys of the outer dict are 
    the valid key-words for the function.  The value for each key is a dict containing 2 
    specific keys: "Default", and "Validator" with the following values:
        "Default"      - The default value for the kwarg if none is specified.
        "Validator"    - A function that takes the caller specified value for the kwarg,
                         and validates that it is the correct type, and (for kwargs with 
                         a limited set of allowed values) may also validate that the
                         kwarg value is one of the allowed values.
    '''
    vkwargs = {
        'box_size'    : { 'Default'     : 'atr',
                          'Validator'   : lambda value: isinstance(value,(float,int)) or value == 'atr' },
        'atr_length'  : { 'Default'     : 14,
                          'Validator'   : lambda value: isinstance(value,int) or value == 'total' },               
    }

    _validate_vkwargs_dict(vkwargs)

    return vkwargs

def _construct_ohlc_collections(dates, opens, highs, lows, closes, marketcolors=None):
    """Represent the time, open, high, low, close as a vertical line
    ranging from low to high.  The left tick is the open and the right
    tick is the close.
    *opens*, *highs*, *lows* and *closes* must have the same length.
    NOTE: this code assumes if any value open, high, low, close is
    missing (*-1*) they all are missing

    Parameters
    ----------
    opens : sequence
        sequence of opening values
    highs : sequence
        sequence of high values
    lows : sequence
        sequence of low values
    closes : sequence
        sequence of closing values
    marketcolors : dict of colors: 'up', 'down'

    Returns
    -------
    ret : list 
        a list or tuple of matplotlib collections to be added to the axes
    """

    _check_input(opens, highs, lows, closes)

    if marketcolors is None:
        mktcolors = _get_mpfstyle('classic')['marketcolors']['ohlc']
        print('default mktcolors=',mktcolors)
    else:
        mktcolors = marketcolors['ohlc']

    rangeSegments = [((dt, low), (dt, high)) for dt, low, high in
                     zip(dates, lows, highs) if low != -1]

    avg_dist_between_points = (dates[-1] - dates[0]) / float(len(dates))

    ticksize = avg_dist_between_points / 2.5

    # the ticks will be from ticksize to 0 in points at the origin and
    # we'll translate these to the date, open location
    openSegments = [((dt-ticksize, op), (dt, op)) for dt, op in zip(dates, opens) if op != -1]
    

    # the ticks will be from 0 to ticksize in points at the origin and
    # we'll translate these to the date, close location
    closeSegments = [((dt, close), (dt+ticksize, close)) for dt, close in zip(dates, closes) if close != -1]

    if mktcolors['up'] == mktcolors['down']:
        colors = mktcolors['up']
    else:
        colorup = mcolors.to_rgba(mktcolors['up'])
        colordown = mcolors.to_rgba(mktcolors['down'])
        colord = {True: colorup, False: colordown}
        colors = [colord[open < close] for open, close in
                  zip(opens, closes) if open != -1 and close != -1]

    useAA = 0,    # use tuple here
    lw    = 0.5,  # use tuple here
    lw = None
    rangeCollection = LineCollection(rangeSegments,
                                     colors=colors,
                                     linewidths=lw,
                                     antialiaseds=useAA
                                     )

    openCollection = LineCollection(openSegments,
                                    colors=colors,
                                    linewidths=lw,
                                    antialiaseds=useAA
                                    )

    closeCollection = LineCollection(closeSegments,
                                     colors=colors,
                                     antialiaseds=useAA,
                                     linewidths=lw
                                     )

    return rangeCollection, openCollection, closeCollection


def _construct_candlestick_collections(dates, opens, highs, lows, closes, marketcolors=None):
    """Represent the open, close as a bar line and high low range as a
    vertical line.

    NOTE: this code assumes if any value open, low, high, close is
    missing they all are missing


    Parameters
    ----------
    opens : sequence
        sequence of opening values
    highs : sequence
        sequence of high values
    lows : sequence
        sequence of low values
    closes : sequence
        sequence of closing values
    marketcolors : dict of colors: up, down, edge, wick, alpha
    alpha : float
        bar transparency

    Returns
    -------
    ret : tuple
        (lineCollection, barCollection)
    """
    
    _check_input(opens, highs, lows, closes)

    if marketcolors is None:
        marketcolors = _get_mpfstyle('classic')['marketcolors']
        print('default market colors:',marketcolors)

    avg_dist_between_points = (dates[-1] - dates[0]) / float(len(dates))

    delta = avg_dist_between_points / 4.0

    barVerts = [((date - delta, open),
                 (date - delta, close),
                 (date + delta, close),
                 (date + delta, open))
                for date, open, close in zip(dates, opens, closes)
                if open != -1 and close != -1]

    rangeSegLow   = [((date, low), (date, min(open,close)))
                     for date, low, open, close in zip(dates, lows, opens, closes)
                     if low != -1]
    
    rangeSegHigh  = [((date, high), (date, max(open,close)))
                     for date, high, open, close in zip(dates, highs, opens, closes)
                     if high != -1]
                      
    rangeSegments = rangeSegLow + rangeSegHigh

    alpha  = marketcolors['alpha']

    uc     = mcolors.to_rgba(marketcolors['candle'][ 'up' ], alpha)
    dc     = mcolors.to_rgba(marketcolors['candle']['down'], alpha)
    colors = _updown_colors(uc, dc, opens, closes)

    uc     = mcolors.to_rgba(marketcolors['edge'][ 'up' ], 1.0)
    dc     = mcolors.to_rgba(marketcolors['edge']['down'], 1.0)
    edgecolor = _updown_colors(uc, dc, opens, closes)
    
    uc     = mcolors.to_rgba(marketcolors['wick'][ 'up' ], 1.0)
    dc     = mcolors.to_rgba(marketcolors['wick']['down'], 1.0)
    wickcolor = _updown_colors(uc, dc, opens, closes)

    useAA = 0,    # use tuple here
    lw    = 0.5,  # use tuple here
    lw = None
    rangeCollection = LineCollection(rangeSegments,
                                     colors=wickcolor,
                                     linewidths=lw,
                                     antialiaseds=useAA
                                     )

    barCollection = PolyCollection(barVerts,
                                   facecolors=colors,
                                   edgecolors=edgecolor,
                                   antialiaseds=useAA,
                                   linewidths=lw
                                   )

    return rangeCollection, barCollection

def _construct_renko_collections(dates, highs, lows, volumes, config_renko_params, closes, marketcolors=None):
    """Represent the price change with bricks

    NOTE: this code assumes if any value open, low, high, close is
    missing they all are missing

    Algorithm Explanation
    ---------------------
    In the first part of the algorithm, we populate the cdiff array
    along with adjusting the dates and volumes arrays into the new_dates and
    new_volumes arrays. A single date includes a range from no bricks to many 
    bricks, if a date has no bricks it shall not be included in new_dates, 
    and if it has n bricks then it will be included n times. Volumes use a 
    volume cache to save volume amounts for dates that do not have any bricks
    before adding the cache to the next date that has at least one brick.
    We populate the cdiff array with each close values difference from the 
    previously created brick divided by the brick size.

    In the second part of the algorithm, we iterate through the values in cdiff
    and add 1s or -1s to the bricks array depending on whether the value is 
    positive or negative. Every time there is a trend change (ex. previous brick is
    an upbrick, current brick is a down brick) we draw one less brick to account
    for the price having to move the previous bricks amount before creating a 
    brick in the opposite direction.

    In the final part of the algorithm, we enumerate through the bricks array and
    assign up-colors or down-colors to the associated index in the color array and
    populate the verts list with each bricks vertice to be used to create the matplotlib
    PolyCollection.

    Useful sources:
    https://avilpage.com/2018/01/how-to-plot-renko-charts-with-python.html
    https://school.stockcharts.com/doku.php?id=chart_analysis:renko
    
    Parameters
    ----------
    dates : sequence
        sequence of dates
    highs : sequence
        sequence of high values
    lows : sequence
        sequence of low values
    config_renko_params : kwargs table (dictionary)
        brick_size : size of each brick
        atr_length : length of time used for calculating atr
    closes : sequence
        sequence of closing values
    marketcolors : dict of colors: up, down, edge, wick, alpha

    Returns
    -------
    ret : tuple
        rectCollection
    """
    renko_params = _process_kwargs(config_renko_params, _valid_renko_kwargs())
    if marketcolors is None:
        marketcolors = _get_mpfstyle('classic')['marketcolors']
        print('default market colors:',marketcolors)
    
    brick_size = renko_params['brick_size']
    atr_length = renko_params['atr_length']
    

    if brick_size == 'atr':
        if atr_length == 'total':
            brick_size = _calculate_atr(len(closes)-1, highs, lows, closes)
        else:
            brick_size = _calculate_atr(atr_length, highs, lows, closes)
    else: # is an integer or float
        upper_limit = (max(closes) - min(closes)) / 2
        lower_limit = 0.01 * _calculate_atr(len(closes)-1, highs, lows, closes)
        if brick_size > upper_limit:
            raise ValueError("Specified brick_size may not be larger than (50% of the close price range of the dataset) which has value: "+ str(upper_limit))
        elif brick_size < lower_limit:
            raise ValueError("Specified brick_size may not be smaller than (0.01* the Average True Value of the dataset) which has value: "+ str(lower_limit))

    alpha  = marketcolors['alpha']

    uc     = mcolors.to_rgba(marketcolors['candle'][ 'up' ], alpha)
    dc     = mcolors.to_rgba(marketcolors['candle']['down'], alpha)
    euc    = mcolors.to_rgba(marketcolors['edge'][ 'up' ], 1.0)
    edc    = mcolors.to_rgba(marketcolors['edge']['down'], 1.0)
    
    cdiff = [] # holds the differences between each close and the previously created brick / the brick size
    prev_close_brick = closes[0]
    volume_cache = 0 # holds the volumes for the dates that were skipped
    new_dates = [] # holds the dates corresponding with the index
    new_volumes = [] # holds the volumes corresponding with the index.  If more than one index for the same day then they all have the same volume.

    for i in range(len(closes)-1):
        brick_diff = int((closes[i+1] - prev_close_brick) / brick_size)
        if brick_diff == 0:
            if volumes is not None:
                volume_cache += volumes[i]
            continue

        cdiff.extend([int(brick_diff/abs(brick_diff))] * abs(brick_diff))
        if volumes is not None:
            new_volumes.extend([volumes[i] + volume_cache] * abs(brick_diff))
            volume_cache = 0
        new_dates.extend([dates[i]] * abs(brick_diff))
        prev_close_brick += brick_diff *brick_size

    bricks = [] # holds bricks, -1 for down bricks, 1 for up bricks
    curr_price = closes[0]

    last_diff_sign = 0 # direction the bricks were last going in -1 -> down, 1 -> up
    dates_volumes_index = 0 # keeps track of the index of the current date/volume
    for diff in cdiff:
        
        curr_diff_sign = diff/abs(diff)
        if last_diff_sign != 0 and curr_diff_sign != last_diff_sign:
            last_diff_sign = curr_diff_sign
            new_dates.pop(dates_volumes_index)
            if volumes is not None:
                if dates_volumes_index == len(new_volumes)-1:
                    new_volumes[dates_volumes_index-1] += new_volumes[dates_volumes_index]
                else:
                    new_volumes[dates_volumes_index+1] += new_volumes[dates_volumes_index]
                new_volumes.pop(dates_volumes_index)
            continue
        last_diff_sign = curr_diff_sign
    
        if diff > 0:
            bricks.extend([1]*abs(diff))
        else:
            bricks.extend([-1]*abs(diff))
        dates_volumes_index += 1


    verts = [] # holds the brick vertices
    colors = [] # holds the facecolors for each brick
    edge_colors = [] # holds the edgecolors for each brick
    brick_values = [] # holds the brick values for each brick
    for index, number in enumerate(bricks):
        if number == 1: # up brick
            colors.append(uc)
            edge_colors.append(euc)
        else: # down brick
            colors.append(dc)
            edge_colors.append(edc)

        curr_price += (brick_size * number)
        brick_values.append(curr_price)
        
        x, y = index, curr_price

        verts.append((
            (x, y),
            (x, y+brick_size),
            (x+1, y+brick_size),
            (x+1, y)))

    useAA = 0,    # use tuple here
    lw = None
    rectCollection = PolyCollection(verts,
                                    facecolors=colors,
                                    antialiaseds=useAA,
                                    edgecolors=edge_colors,
                                    linewidths=lw
                                    )
    
    return (rectCollection, ), new_dates, new_volumes, brick_values, brick_size

def _construct_pointnfig_collections(dates, highs, lows, volumes, config_pointnfig_params, closes, marketcolors=None):
    """Represent the price change with Xs and Os

    NOTE: this code assumes if any value open, low, high, close is
    missing they all are missing

    Algorithm Explanation
    ---------------------
    In the first part of the algorithm, we populate the boxes array
    along with adjusting the dates and volumes arrays into the new_dates and
    new_volumes arrays. A single date includes a range from no boxes to many 
    boxes, if a date has no boxes it shall not be included in new_dates, 
    and if it has n boxes then it will be included n times. Volumes use a 
    volume cache to save volume amounts for dates that do not have any boxes
    before adding the cache to the next date that has at least one box.
    We populate the boxes array with each close values difference from the 
    previously created brick divided by the box size.

    The second part of the algorithm has a series of step. First we combine the
    adjacent like signed values in the boxes array (ex. [-1, -2, 3, -4] -> [-3, 3, -4]).
    Next we subtract 1 from the absolute value of each element in boxes except the 
    first to ensure every time there is a trend change (ex. previous box is
    an X, current brick is a O) we draw one less box to account for the price 
    having to move the previous box's amount before creating a box in the 
    opposite direction. Next we adjust volume and dates to combine volume into 
    non 0 box indexes and to only use dates from non 0 box indexes. We then
    remove all 0s from the boxes array and once again combine adjacent similarly
    signed differences in boxes.

    Lastly, we enumerate through the boxes to populate the line_seg and circle_patches
    arrays. line_seg holds the / and \ line segments that make up an X and 
    circle_patches holds matplotlib.patches Ellipse objects for each O. We start
    by filling an x and y array each iteration which contain the x and y 
    coordinates for each box in the column. Then for each coordinate pair in
    x, y we add to either the line_seg array or the circle_patches array 
    depending on the value of sign for the current column (1 indicates 
    line_seg, -1 indicates circle_patches). The height of the boxes take 
    into account padding which separates each box by a small margin in 
    order to increase readability.

    Useful sources:
    https://stackoverflow.com/questions/8750648/point-and-figure-chart-with-matplotlib
    https://www.investopedia.com/articles/technical/03/081303.asp
    
    Parameters
    ----------
    dates : sequence
        sequence of dates
    highs : sequence
        sequence of high values
    lows : sequence
        sequence of low values
    config_pointnfig_params : kwargs table (dictionary)
        box_size : size of each box
        atr_length : length of time used for calculating atr
    closes : sequence
        sequence of closing values
    marketcolors : dict of colors: up, down, edge, wick, alpha

    Returns
    -------
    ret : tuple
        rectCollection
    """
    pointnfig_params = _process_kwargs(config_pointnfig_params, _valid_pointnfig_kwargs())
    if marketcolors is None:
        marketcolors = _get_mpfstyle('classic')['marketcolors']
        print('default market colors:',marketcolors)
    
    box_size = pointnfig_params['box_size']
    atr_length = pointnfig_params['atr_length']
    

    if box_size == 'atr':
        if atr_length == 'total':
            box_size = _calculate_atr(len(closes)-1, highs, lows, closes)
        else:
            box_size = _calculate_atr(atr_length, highs, lows, closes)
    else: # is an integer or float
        upper_limit = (max(closes) - min(closes)) / 2
        lower_limit = 0.01 * _calculate_atr(len(closes)-1, highs, lows, closes)
        if box_size > upper_limit:
            raise ValueError("Specified box_size may not be larger than (50% of the close price range of the dataset) which has value: "+ str(upper_limit))
        elif box_size < lower_limit:
            raise ValueError("Specified box_size may not be smaller than (0.01* the Average True Value of the dataset) which has value: "+ str(lower_limit))

    alpha  = marketcolors['alpha']

    uc     = mcolors.to_rgba(marketcolors['candle'][ 'up' ], alpha)
    dc     = mcolors.to_rgba(marketcolors['candle']['down'], alpha)
    tfc    = mcolors.to_rgba(marketcolors['edge']['down'], 0) # transparent face color

    boxes = [] # each element in an integer representing the number of boxes to be drawn on that indexes column (negative numbers -> Os, positive numbers -> Xs)
    prev_close_box = closes[0] # represents the value of the last box in the previous column
    volume_cache = 0 # holds the volumes for the dates that were skipped
    temp_volumes, temp_dates = [], [] # holds the temp adjusted volumes and dates respectively
    
    for i in range(len(closes)-1):
        box_diff = int((closes[i+1] - prev_close_box) / box_size)
        if box_diff == 0:
            if volumes is not None:
                volume_cache += volumes[i]
            continue

        boxes.append(box_diff)
        if volumes is not None:
            temp_volumes.append(volumes[i] + volume_cache)
            volume_cache = 0
        temp_dates.append(dates[i])
        prev_close_box += box_diff *box_size

    # combine adjacent similarly signed differences
    boxes, indexes = combine_adjacent(boxes)
    new_volumes, new_dates = coalesce_volume_dates(temp_volumes, temp_dates, indexes)
    
    #subtract 1 from the abs of each diff except the first to account for the first box using the last box in the opposite direction
    first_elem = boxes[0]
    boxes = [boxes[i]- int((boxes[i]/abs(boxes[i]))) for i in range(1, len(boxes))]
    boxes.insert(0, first_elem)

    # adjust volume and dates to make sure volume is combined into non 0 box indexes and only use dates from non 0 box indexes
    temp_volumes, temp_dates = [], []
    for i in range(len(boxes)):
        if boxes[i] == 0:
            volume_cache += new_volumes[i]
        else:
            temp_volumes.append(new_volumes[i] + volume_cache)
            volume_cache = 0
            temp_dates.append(new_dates[i])
    
    #remove 0s from boxes
    boxes = list(filter(lambda diff: diff != 0, boxes))

    # combine adjacent similarly signed differences again after 0s removed
    boxes, indexes = combine_adjacent(boxes)
    new_volumes, new_dates = coalesce_volume_dates(temp_volumes, temp_dates, indexes)

    curr_price = closes[0]
    box_values = [] # y values for the boxes
    circle_patches = [] # list of circle patches to be used to create the cirCollection
    line_seg = [] # line segments that make up the Xs
    
    for index, difference in enumerate(boxes):
        diff = abs(difference)

        sign = (difference / abs(difference)) # -1 or 1
        start_iteration = 0 if sign > 0 else 1
        
        x = [index] * (diff)
        y = [curr_price + (i * box_size * sign) for i in range(start_iteration, diff+start_iteration)]
        
        curr_price += (box_size * sign * (diff))
        box_values.append(sum(y) / len(y))
        
        for i in range(len(x)): # x and y have the same length
            height = box_size * 0.85
            width = 0.6
            if height < 0.5:
                width = height
            
            padding = (box_size * 0.075)
            if sign == 1: # X
                line_seg.append([(x[i]-width/2, y[i] + padding), (x[i]+width/2, y[i]+height + padding)]) # create / part of the X
                line_seg.append([(x[i]-width/2, y[i]+height+padding), (x[i]+width/2, y[i]+padding)]) # create \ part of the X
            else: # O
                circle_patches.append(Ellipse((x[i], y[i]-(height/2) - padding), width, height))
    
    useAA = 0,    # use tuple here
    lw = 0.5        

    cirCollection = PatchCollection(circle_patches)
    cirCollection.set_facecolor([tfc] * len(circle_patches))
    cirCollection.set_edgecolor([dc] * len(circle_patches))
    
    xCollection = LineCollection(line_seg,
                                 colors=[uc] * len(line_seg),
                                 linewidths=lw,
                                 antialiaseds=useAA
                                 )
    
    return (cirCollection, xCollection), new_dates, new_volumes, box_values, box_size



from matplotlib.ticker import Formatter
class IntegerIndexDateTimeFormatter(Formatter):
    """
    Formatter for axis that is indexed by integer, where the integers
    represent the index location of the datetime object that should be
    formatted at that lcoation.  This formatter is used typically when
    plotting datetime on an axis but the user does NOT want to see gaps
    where days (or times) are missing.  To use: plot the data against
    a range of integers equal in length to the array of datetimes that
    you would otherwise plot on that axis.  Construct this formatter
    by providing the arrange of datetimes (as matplotlib floats). When
    the formatter receives an integer in the range, it will look up the
    datetime and format it.  

    """
    def __init__(self, dates, fmt='%b %d, %H:%M'):
        self.dates = dates
        self.len   = len(dates)
        self.fmt   = fmt

    def __call__(self, x, pos=0):
        #import pdb; pdb.set_trace()
        'Return label for time x at position pos'
        # not sure what 'pos' is for: see
        # https://matplotlib.org/gallery/ticks_and_spines/date_index_formatter.html
        ix = int(np.round(x))
         
        if ix >= self.len or ix < 0:
            date = None
            dateformat = ''
        else:
            date = self.dates[ix]
            dateformat = mdates.num2date(date).strftime(self.fmt)
        #print('x=',x,'pos=',pos,'dates[',ix,']=',date,'dateformat=',dateformat)
        return dateformat

