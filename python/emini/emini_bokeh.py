import numpy as np
import pandas as pd

from os.path import basename
#from deprecated import deprecated
import bokeh.io
from bokeh.layouts import (
    column, row, gridplot, layout
)

from bokeh.models import (
    Band,
    BoxAnnotation,
    ColumnDataSource,
    Range1d,
    LinearAxis,
    CrosshairTool,
    HoverTool,
    CustomJS,
)

from bokeh.models.widgets.markups import (
    Div
)

from bokeh.plotting import (
    Figure,
    show,
)

from bokeh.core.properties import value

# for color_palette, see https://docs.bokeh.org/en/latest/docs/reference/palettes.html
from bokeh.palettes import Category20
import itertools
# this will cycle through
# colour = itertools.cycle(Category20[20])


def add_legend_mute(figures):
    """Click on a legend entry to mute the sries.
    :parameter figures
        a list of figures
    :parameter dimensions: default 'height'
        specify 'both for both, height for a vertical line, and 'width for a horizontal line
    """

    # copy list (see 
    for fig in figures:
        fig.legend.location = "top_left"
        fig.legend.click_policy = "mute"


def add_linked_crosshair(figures, dimensions='height'):
    """Add a bokeh.models.tools.CrossHairTool to each figure and linked to track in all.
    :parameter figures
        a list of figures
    :parameter dimensions: default 'height'
        specify 'both for both, height for a vertical line, and 'width for a horizontal line
    """
    # ToDo: I think 'both' needs to be changed to look at x and y separately as the y's aren't necessarily
    #       relevant across different graphs.
    if dimensions == 'both':
        js_move = """
if (cb_obj.x>=fig.x_range.start && cb_obj.x<=fig.x_range.end &&
    cb_obj.y>=fig.y_range.start && cb_obj.y<=fig.y_range.end) {
    cross.spans.height.computed_location=cb_obj.sx;
    cross.spans.width.computed_location=cb_obj.sy;
}
else {
    cross.spans.height.computed_location=null;
    cross.spans.width.computed_location=null;
}
"""
    elif dimensions == 'height':
        js_move = """
if (cb_obj.x>=fig.x_range.start && cb_obj.x<=fig.x_range.end &&
    cb_obj.y>=fig.y_range.start && cb_obj.y<=fig.y_range.end) {
    cross.spans.height.computed_location=cb_obj.sx;
}
else {
    cross.spans.height.computed_location=null;
}
        """
    elif dimensions == 'width':
        js_move = """
if (cb_obj.x>=fig.x_range.start && cb_obj.x<=fig.x_range.end &&
    cb_obj.y>=fig.y_range.start && cb_obj.y<=fig.y_range.end) {
    cross.spans.width.computed_location=cb_obj.sy;
}
else {
    cross.spans.width.computed_location=null;
}
        """

    js_leave = "cross.spans.height.computed_location=null; cross.spans.width.computed_location=null"

    # copy list (see 
    for fig in figures:
        crosshair = CrosshairTool(dimensions=dimensions)
        fig.add_tools(crosshair)
        for fig2 in figures:
            if fig2 != fig:
                args = {'cross': crosshair, 'fig': fig2}
                fig2.js_on_event('mousemove', CustomJS(args=args, code=js_move))
                fig2.js_on_event('mouseleave', CustomJS(args=args, code=js_leave))


line_marker_map = {
    'o': Figure.circle,
    'a': Figure.asterisk,
    'c': Figure.cross,
    's': Figure.square,
    'x': Figure.x,
}


def add_circle_line(fig, cds, col, color):
    fig.circle(source=cds, x='index', y=col, color=color, legend=value(col), size=5,
               muted_color=color, muted_alpha=0.2)
    fig.line(source=cds, x='index', y=col, color=color, legend=value(col), line_width=2)


def add_marker_line(fig, cds, col, color, marker='o'):
    size = 10 if marker.isupper() else 5
    marker = marker.lower()
    line_marker_map[marker](fig, source=cds, x='index', y=col, color=color,
                            legend=value(col), size=size, muted_color=color, muted_alpha=0.2)
    fig.line(source=cds, x='index', y=col, color=color, legend=value(col), line_width=2)


def add_bands(fig, cds, lo, hi, color):
    band = Band(source=cds, base='index', lower=lo, upper=hi, fill_alpha=0.1, fill_color=color)
    fig.add_layout(band)


def add_candle(fig, cds, oprc, hprc, lprc, cprc):
    # copy of index and open.close
    idx = cds.data['index']
    o = cds.data[oprc]
    c = cds.data[cprc]

    # up/down in different colour
    up = c > o
    dn = c < o

    # fig.x_range.range_padding = 0.05
    fig.segment('index', hprc, 'index', lprc, source=cds, color="black")
    fig.vbar(idx[up], 0.5, o[up], c[up], fill_color="#035afc", line_color="black")
    fig.vbar(idx[dn], 0.5, o[dn], c[dn], fill_color="#fc0303", line_color="black")


def add_trades(figs, idx, trd):
    # we create a BoxAnnotation for each position, first find the left and right ends
    # entry trades
    long_beg = trd.index[((trd['trd'] > 0) & (trd['dpos'] > 0)) |
                         ((trd.index == trd.index[0]) & (trd['pos'] > 0))]
    long_end = trd.index[((trd['trd'] < 0) & (trd['pos'] > 0)) |
                         ((trd.index == trd.index[-1]) & (trd['dpos'] > 0))]

    for i in range(len(long_beg)):
        left = idx.get_loc(long_beg[i], 'bfill')
        right = idx.get_loc(long_end[i], 'bfill')
        for f in figs:
            box = BoxAnnotation(left=left, right=right, fill_alpha=0.1, fill_color='blue')
            f.renderers.append(box)

    shrt_beg = trd.index[((trd['trd'] < 0) & (trd['dpos'] < 0)) |
                         ((trd.index == trd.index[0]) & (trd['pos'] < 0))]
    shrt_end = trd.index[((trd['trd'] > 0) & (trd['pos'] < 0)) |
                         ((trd.index == trd.index[-1]) & (trd['dpos'] < 0))]

    for i in range(len(shrt_beg)):
        left = idx.get_loc(shrt_beg[i], 'bfill')
        right = idx.get_loc(shrt_end[i], 'bfill')
        for f in figs:
            box = BoxAnnotation(left=left, right=right, fill_alpha=0.1, fill_color='red')
            f.renderers.append(box)


def make_figure(plot_options, tick_labels, title):
    f = Figure(**plot_options)
    f.xaxis.major_label_overrides = tick_labels
    f.title.text = title
    f.title.align='center'
    f.title.text_font_style='bold'
    f.title.text_font_size='2em'
    return f


def plot_pnl(plot_options, log_returns, title):

    pnl = pd.DataFrame(index=log_returns.index, dtype=np.float64)
    for c in log_returns.columns:
        pnl[c] = np.expm1(log_returns[c].cumsum()) 

    # datetime labels for rows
    cds = ColumnDataSource({'index': np.arange(pnl.index.shape[0])})
    cds_labels = {
        i: date.strftime('%Y-%m-%d') for i, date in enumerate(pd.to_datetime(pnl.index))
    }
    # this is for the HoverTool
    cds.add([v for k, v in cds_labels.items()], 'tdate')

    # colours generator
    colors = itertools.cycle(Category20[20])

    # plot
    f = make_figure(plot_options, cds_labels, title)
    color = next(colors)  
    for c in pnl.columns:
        cds.add(pnl[c].values, c)
        add_circle_line(f, cds=cds, col=c, color=next(colors))

    return f


col_format = {
    'Return' : '.2%',
    'Volatility' : '.2%',
    'Sharpe' : '.2',
    'Sortino': '.2',
    'Sharpe 2%': '.2',
    'Sortino 2%' : '.2',
    'Trades' : '0'
}


def table_html(df, col_format=None, hide_nan=False, caption=None):

        # overwrite with supplied formatters, '' is default formatter
        if col_format is None:
            col_format = {}

        table_styles = {
            #'width': '100%',
            'font-size': '1em',
            'border': '1px solid #98bf21',
            'border-collapse': 'collapse',
            #'text-align': 'right'
        }

        # tag for table
        tid = 't' + str(id(df))

        # style block with global entries
        html = '<style> ' + '#' + tid + ' {'
        html += ''.join([x + ':' + y + ';' for x, y in table_styles.items()])
        html += '}'

        # align cells right
        html += ' #' + tid + ' th, #' + tid +' td {text-align:right;border:1px solid #98bf21;padding:3px 7px 2px 7px;}'

        # emphasised header row
        html += ' #' + tid + ' th {text-align:center;color:#ffffff;background-color:#A7C942;}'
        #html += ' #' + tid + ' th {font-size:1.1em;color:#ffffff;background-color:#A7C942;}'
        #text-align:left;
        #padding-top:5px;
        #padding-bottom:4px;

        # alternate row highlights
        html += ' #' + tid + ' tr:nth-child(odd) {color:#000000;background-color:#EAF2D3;}'

        # bold first column (labels)
        html += ' #' + tid + ' td:nth-child(1) {font-weight:bold;text-align:center;}'
        html += '</style>'

        # table
        html += ' <table id="' + tid + '">'

        # caption
        if caption is not None:
            html += '<caption style="caption-side:bottom;font-size:0.75em;text-align:left;">' + caption + '</caption>'
#        html += '<caption style="caption-side:top;text-align:left;">This is the Caption</caption>'

        # output header
        html += '<tr><th></th>' + ''.join([f'<th>{x}</th>' for x in df.columns]) + '</tr>'

        # loop over dataframe index
        for row in df.index:
            html += '<tr><td>' + str(row) + '</td>'
            for col in df.columns:
                cell = df.loc[row,col]

                # The following check is performed as a string comparison
                # so that ipy_table does not need to require (import) numpy.
                if str(type(cell)) in ["<class 'float'>", "<class 'numpy.float64'>"]:
                    if np.isnan(cell) and hide_nan:
                        html += '<td></td>'
                    else:
                        fmt = col_format.get(col,'')
                        if cell < 0:
                            html += f'<td style="color:red">{cell:{fmt}}</td>'
                        else:
                            html += f'<td>{cell:{fmt}}</td>'
                else:
                    html += f'<td>{cell}</td>'
            html += '</tr>'

        # close table
        html += '</table>'
        return html


def plot_stats(stats, title):
    return [
        Div(text=f'<b>{title}</b>'),
        Div(text=table_html(stats, col_format))
    ]
    

def do_plot(scenario_pnl, scenario_stats, strategy_pnl, strategy_stats, fn=None):

    # global plot options
    plot_options = dict(plot_width=1800, plot_height=950,  # responsive=True,
                        x_axis_type='linear',
                        tools='save,reset,box_zoom')

    figure_list = []
    figure_list.append(plot_pnl(plot_options, scenario_pnl, 'Scenarios'))

    figure_list[-1].add_tools(HoverTool(
        tooltips=[
            ('tdate', '@tdate'),
            # ('vwap' , '@vprc{0,0.0000}'),
            # ('volume', '@tqty{0,0}'),
        ],
        #mode='vline'
        mode='mouse'
    ))

    plot_options['x_range'] = figure_list[-1].x_range
    
    for nm, lr in strategy_pnl.items():
        figure_list.append(plot_pnl(plot_options, lr, f'Strategy {nm}'))
        
    add_linked_crosshair(figure_list)
    add_legend_mute(figure_list)    

    figs =  gridplot(figure_list, ncols=1, sizing_mode='scale_both')

    w = []
    w.extend(plot_stats(
        scenario_stats,
        f"Scenario Statistics, Date Range {scenario_pnl.index[0].date()} to {scenario_pnl.index[-1].date()}"))

    for k, v in strategy_stats.items():
        w.extend(plot_stats(v, f'Strategy {k}'))

    stats = column(w, sizing_mode='stretch_both')#, height=500)
    
    bokeh.io.reset_output()
    if fn is not None:
        bokeh.io.output_file(fn, mode="inline", title=basename(fn)[:-5])
    # show(column(plt, sizing_mode="stretch_both"))
    show(column(stats, figs))

