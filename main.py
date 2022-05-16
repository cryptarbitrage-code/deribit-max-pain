from datetime import datetime
from tkinter import *
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from api_functions import get_book_summary_by_currency
from option_calculations import option_value_expiry

# Some chart parameters
chart_size = (12, 6)
# other settings
pd.set_option('display.max_columns', None)  # useful for testing to display full dataframe

# tkinter set up
root = Tk()
root.title("Historical Volatility Calculations - Cryptarbitrage")
root.iconbitmap('cryptarbitrage_icon_96px.ico')
root.minsize(400, 200)

# details frame
details_frame = LabelFrame(root, text="Details", padx=2, pady=2)
details_frame.grid(row=0, column=0, padx=2, pady=2, sticky=NW)
selected_expiry = StringVar()
selected_currency = StringVar()
selected_currency.set('BTC')

# Chart frames
chart1_frame = LabelFrame(root, text="Max Pain Chart", padx=2, pady=2)
chart1_frame.grid(row=0, column=1, rowspan=2, padx=2, pady=2)


def fetch_data(currency):
    # fetch book summary and place into dataframe
    all_option_book_summary = get_book_summary_by_currency(currency, 'option')
    df = pd.DataFrame(all_option_book_summary)

    # split the instrument name into separate columns
    expiry_date = []
    strike_price = []
    option_type = []
    for index in range(len(df)):
        instrument_text = df.loc[index, 'instrument_name'].split('-')
        expiry_date.append(instrument_text[1])
        strike_price.append(float(instrument_text[2]))
        option_type.append(instrument_text[3])
    df = df.assign(expiry_date=expiry_date)
    df = df.assign(strike_price=strike_price)
    df = df.assign(option_type=option_type)

    unique_expiry_dates = df['expiry_date'].unique()
    unique_expiry_dates = sorted(unique_expiry_dates, key=lambda date: datetime.strptime(date, "%d%b%y"))

    return df, unique_expiry_dates


def details_state_1():
    currency = selected_currency.get()
    # set variables to global so plot_charts gets the updated values
    # without having to fetch data from the API for every plot
    global df, unique_expiry_dates
    df, unique_expiry_dates = fetch_data(currency)
    # details frame: State 1
    for widgets in details_frame.winfo_children():
        widgets.destroy()

    current_currency = 'Current currency: ' + currency
    current_currency_label = Label(details_frame, text=current_currency)
    current_currency_label.grid(row=0, column=0, columnspan=2)
    selected_expiry.set(unique_expiry_dates[0])
    # button that allows changing the currency
    change_currency_button = Button(master=details_frame,
                                    command=details_state_2,
                                    height=1,
                                    width=18,
                                    text="Change currency",
                                    bg="#ccccff")
    change_currency_button.grid(row=1, column=0, columnspan=2)
    expiry_dropdown = OptionMenu(details_frame, selected_expiry, *unique_expiry_dates)
    expiry_dropdown.grid(row=2, column=0)
    expiry_dropdown.config(width=10)
    # button that displays the plot
    plot_button = Button(master=details_frame,
                         command=plot_charts,
                         height=1,
                         width=18,
                         text="Plot Chart",
                         bg="#88bb88")
    plot_button.grid(row=3, column=0, columnspan=2)


def details_state_2():
    # details frame: State 2
    for widgets in details_frame.winfo_children():
        widgets.destroy()

    currency_dropdown = OptionMenu(details_frame, selected_currency, 'BTC', 'ETH', 'SOL')
    currency_dropdown.grid(row=0, column=0)
    currency_dropdown.config(width=10)
    # button that sets the new currency
    select_currency_button = Button(master=details_frame,
                                    command=details_state_1,
                                    height=1,
                                    width=18,
                                    text="Select currency",
                                    bg="#ccccff")
    select_currency_button.grid(row=1, column=0, columnspan=2)


def calculate_max_pain():
    # create dataframe of selected expiry
    df_selected = df[df['expiry_date'] == selected_expiry.get()]
    df_selected = df_selected.sort_values('strike_price')
    df_selected = df_selected.reset_index(drop=True)

    # create list of all expiry dates
    unique_strikes_selected = df_selected['strike_price'].unique()
    unique_strikes_selected.sort()

    # do max pain calculations for all options in the selected expiry
    max_pain_calcs = []
    for index in range(len(df_selected)):
        option_calc = {}
        for strike in unique_strikes_selected:
            option_calc[str(strike)] = option_value_expiry(df_selected.loc[index, 'strike_price'],
                                                           df_selected.loc[index, 'open_interest'],
                                                           strike,
                                                           df_selected.loc[index, 'option_type'])
        max_pain_calcs.append(option_calc)
    # create a dataframe out of the max pain calculations, merge it with the selected expiry dataframe
    df_max_pain_calcs = pd.DataFrame(max_pain_calcs)
    df_selected = pd.merge(df_selected, df_max_pain_calcs, left_index=True, right_index=True)
    # print('df_selected: ', df_selected)
    # print('unique_strikes_selected: ', unique_strikes_selected)
    return df_selected, unique_strikes_selected


def plot_charts():
    # Clears any current charts, then plots all charts using selected parameters
    # Destroy old charts if any
    for widgets in chart1_frame.winfo_children():
        widgets.destroy()

    df_selected, unique_strikes_selected = calculate_max_pain()
    df_calls = df_selected[df_selected['option_type'] == 'C']
    df_puts = df_selected[df_selected['option_type'] == 'P']

    # CHART 1: max pain
    # the figure that will contain the plot
    fig1 = Figure(figsize=chart_size, dpi=100)
    # adding the subplot
    plot1 = fig1.add_subplot(111)
    # calculate appropriate bar width based on strike range
    bar_width = (df_selected['strike_price'].max() - df_selected['strike_price'].min()) / 200
    # plotting the graph
    plot1.bar(df_calls['strike_price'] + bar_width * 0.8, df_calls['open_interest'], label='Call OI', width=bar_width)
    plot1.bar(df_puts['strike_price'] - bar_width * 0.8, df_puts['open_interest'], label='Put OI', width=bar_width)

    # sum each intrinsic value column and use to plot intrinsic value
    # sums puts and calls intrinsic value, then stores in the calls df for plotting
    total_intrinsic = []
    for strike in unique_strikes_selected:
        total_intrinsic.append(df_selected[str(strike)].sum())
    df_calls = df_calls.assign(total_intrinsic=total_intrinsic)
    # print('df_calls: ', df_calls)

    # Intrinsic value plot
    plot1_b = plot1.twinx()
    plot1_b.scatter(df_calls['strike_price'], df_calls['total_intrinsic'] / 1000000,
                    label='Intrinsic Value', color='#17becf', linewidth=1.5, marker='x')
    plot1_b.tick_params(axis='y', labelcolor='#17becf')
    plot1_b.set_ylabel('Intrinsic Value ($millions)')
    plot1_b.ticklabel_format(useOffset=False, style='plain')

    # calculate max pain strike and plot vertical line
    max_pain_list = df_calls.loc[df_calls.total_intrinsic == df_calls['total_intrinsic'].min(), 'strike_price'].tolist()
    max_pain = max_pain_list[0]  # in case there are >1 strikes with the same intrinsic, select the first
    max_pain_label = 'Max Pain (' + str(max_pain) + ')'
    plot1.axvline(x=max_pain, label=max_pain_label, color='#17becf', linestyle='--', ymax=0.75)

    plot1.set_xlabel('Price')
    plot1.set_ylabel('Open Interest')
    plot1.set_title('Open Interest and Max Pain (' + selected_currency.get() + ' ' + selected_expiry.get() + ')')
    plot1.legend()
    plot1.grid(True, alpha=0.25)

    fig1.tight_layout()
    # creating the Tkinter canvas containing the Matplotlib figure
    canvas1 = FigureCanvasTkAgg(fig1, master=chart1_frame)
    canvas1.draw()
    # placing the canvas on the Tkinter window
    canvas1.get_tk_widget().pack()
    # creating the Matplotlib toolbar
    toolbar = NavigationToolbar2Tk(canvas1, chart1_frame)
    toolbar.update()
    # placing the toolbar on the Tkinter window
    canvas1.get_tk_widget().pack()

    plt.show()


details_state_1()
plot_charts()

root.mainloop()
