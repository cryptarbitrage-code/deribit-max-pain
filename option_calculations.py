def option_value_expiry(strike, size, underlying_price, option_type):
    # calculates the intrinsic value in dollars at expiry of a linear options

    if option_type == "C":
        option_value = max(0, underlying_price - strike) * size
    elif option_type == "P":
        option_value = max(0, strike - underlying_price) * size
    else:
        print("incorrect option type")

    return option_value
